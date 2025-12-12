# agents/deep_research.py
"""
LangGraph-граф, который:
1. Генерирует стартовый KQL
2. Смотрит на выдачу
3. Уточняет фильтры (например, добавляет event.id, process.name, etc.)
4. Повторяет N раз
5. Возвращает сводку
"""
from typing import TypedDict, List, Annotated
from langgraph.graph import StateGraph, END
from langchain_core.messages import AnyMessage
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from app.kql_generator import description_to_kql
from app.elk_tools import execute_kql
from app.tracer import get_langfuse_handler
from app.config import settings
import json

langfuse_handler = get_langfuse_handler()

#  State 
class DeepResearchState(TypedDict):
    description: str
    iterations: int
    current_kql: str
    total_hits: int
    sample_hits: List[dict]
    summary: str

# 1. ПРОМПТ ДЛЯ УТОЧНЕНИЯ KQL
SYSTEM_PROMPT_REFINE = """\
You are a threat-hunting analyst.  
You receive:  
A) previous KQL string  
B) first 3 raw events returned by it  

Your task: output ONE improved KQL that is either narrower (exclude noise) or broader (catch variants) based on what you see in the samples.  

Rules:  
- Return ONLY the new KQL string.  
- Keep ECS field names.  
- Add or remove filters, but preserve time scope.  
- If samples contain obvious garbage (e.g. svchost.exe), exclude with NOT.  
- If you see a suspicious parent process you didn't filter for, add it.  

Think step by step, then write the single final KQL.
"""

# 2. ПРОМПТ ДЛЯ ИТОГОВОЙ СВОДКИ
SYSTEM_PROMPT_SUMMARY = """\
You are a SOC lead writing a 3-sentence executive summary for other analysts.  
Input: JSON array of up to 5 representative Windows events.  

Output rules:  
1. Sentence 1 – what activity was found (volume, time frame).  
2. Sentence 2 – most interesting / suspicious artefact (process, IP, user).  
3. Sentence 3 – recommended next action or hunt pivot.  

Keep terminology concise, no boilerplate.
"""

# 3. Локальные цепочки
llm = ChatOpenAI(
    model=settings.openai_model,
    openai_api_key=settings.openai_api_key,
    base_url=settings.openai_base_url or None,
    temperature=0,
)

refine_prompt = ChatPromptTemplate.from_messages(
    [("system", SYSTEM_PROMPT_REFINE),
     ("human", "Previous KQL:\n{kql}\n\nFirst 3 events:\n{logs}")]
)
refine_chain = refine_prompt | llm | StrOutputParser()

summary_prompt = ChatPromptTemplate.from_messages(
    [("system", SYSTEM_PROMPT_SUMMARY),
     ("human", "{logs}")]
)
summary_chain = summary_prompt | llm | StrOutputParser()

# 4. УЗЛЫ ГРАФА
def generate_initial_kql(state: DeepResearchState) -> DeepResearchState:
    desc = state["description"]
    kql = description_to_kql(desc)
    return {**state, "current_kql": kql}

def run_elk(state: DeepResearchState) -> DeepResearchState:
    res = execute_kql(state["current_kql"], size=100)
    return {**state, "total_hits": res["total"], "sample_hits": res["hits"]}

def refine_or_stop(state: DeepResearchState) -> DeepResearchState:
    iterations = state["iterations"]
    if iterations >= 3:
        # финальный summary
        text = json.dumps(state["sample_hits"][:3], indent=2, ensure_ascii=False)
        summary = summary_chain.invoke(
            {"logs": text},
            config={"callbacks": [langfuse_handler]}
            )
        return {**state, "summary": summary}
    else:
        # уточняем KQL
        text = json.dumps(state["sample_hits"][:3], indent=2, ensure_ascii=False)
        new_kql = refine_chain.invoke(
            {"kql": state["current_kql"], "logs": text},
            config={"callbacks": [langfuse_handler]}
            ).strip()
        return {
            **state,
            "current_kql": new_kql,
            "iterations": iterations + 1,
        }

# 5. СБОРКА ГРАФА
workflow = StateGraph(DeepResearchState)

workflow.add_node("generate_initial_kql", generate_initial_kql)
workflow.add_node("run_elk", run_elk)
workflow.add_node("refine_or_stop", refine_or_stop)

workflow.set_entry_point("generate_initial_kql")
workflow.add_edge("generate_initial_kql", "run_elk")
workflow.add_edge("run_elk", "refine_or_stop")

def _should_continue(st: DeepResearchState):
    return "refine_or_stop" if not st.get("summary") else END

workflow.add_conditional_edges("refine_or_stop", _should_continue)

deep_research_graph = workflow.compile()