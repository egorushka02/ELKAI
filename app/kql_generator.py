"""
LLM-агент, превращающий описание на русском/английском в KQL-запрос.
"""
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from app.tracer import get_langfuse_handler
from app.config import settings

SYSTEM_PROMPT = """\
    You are a Windows-security analyst assistant.
    Your ONLY task is to translate the user sentence into a SINGLE valid Kibana Query Language string.
    Rules:
    1. Output NOTHING except the raw KQL string.
    2. Use only Winlogbeat field names listed below.
    3. Wrap multi-word literals in double quotes. Escape inner quotes with backslash ".
    4. Wildcards: * (any chars), ? (single char). Do NOT use regex.
    5. Time filters: add @timestamp > now-1d / now-7d and etc when the user mentions time.
    6. Combine clauses with AND/OR/NOT and parentheses when needed.

    Allowed fields (pick exact name):
    - timestamp
    - winlog.provider_name, winlog.event_id, winlog.computer_name, winlog.user.name, winlog.user.sid
    - process.name, process.pid, process.command_line, process.parent.name
    - user.name, user.domain, user.id
    - source.ip, source.port, destination.ip, destination.port
    - event.action, event.code, event.outcome
    - file.name, file.path, file.hash.sha256
    - registry.path, registry.value
    - network.protocol, network.direction, etc
    
    Examples:
    Failed logins last 3 days → @timestamp > now-3d AND winlog.provider_name:"Microsoft-Windows-Security-Auditing" AND winlog.event_id:4625
    Powershell at night → process.name:powershell.exe AND @timestamp > now-1d AND (hour >= 23 OR hour < 6)
    USB sticks → winlog.provider_name:"Microsoft-Windows-DriverFrameworks-UserMode" AND winlog.event_id:2003
    
    Now convert the user sentence.
"""

langfuse_handler = get_langfuse_handler()

prompt = ChatPromptTemplate.from_messages(
    [("system", SYSTEM_PROMPT), ("human", "{description}")]
)

llm = ChatOpenAI(
    model=settings.openai_model,
    openai_api_key=settings.openai_api_key,
    base_url=settings.openai_base_url or None,
    temperature=0,
)

kql_chain = prompt | llm | StrOutputParser()

def description_to_kql(description: str) -> str:
    try:
        return kql_chain.invoke(
            {"description": description},
            config={"callbacks": [langfuse_handler]}
            ).strip()
    except Exception as e:
        if "404" in str(e) and "data policy" in str(e):
            raise ValueError(
                f"Model '{settings.openai_model}' is not available. "
                "Please check your OpenRouter privacy settings"
                "or use a different model."
            ) from e
        raise