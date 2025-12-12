"""
FastAPI + ручки:
POST /kql/generate
POST /kql/execute
POST /research/deep
"""
from fastapi import FastAPI
from app.models import (
    KqlRequest, KqlResponse,
    ElkQueryRequest, ElkQueryResponse,
    DeepResearchRequest, DeepResearchResponse,
)
from app.kql_generator import description_to_kql
from app.elk_tools import execute_kql
from app.deep_research import deep_research_graph

app = FastAPI(title="ELK AI Agent", version="0.2.0")

@app.post("/kql/generate", response_model=KqlResponse)
def generate_kql(req: KqlRequest):
    kql = description_to_kql(req.description)
    return KqlResponse(kql=kql)

@app.post("/kql/execute", response_model=ElkQueryResponse)
def execute_kql_endpoint(req: ElkQueryRequest):
    res = execute_kql(req.kql, req.size)
    return ElkQueryResponse(total=res["total"], hits=res["hits"])

@app.post("/research/deep", response_model=DeepResearchResponse)
def deep_research_endpoint(req: DeepResearchRequest):
    state = {
        "description": req.description,
        "iterations": 0,
        "current_kql": "",
        "total_hits": 0,
        "sample_hits": [],
        "summary": "",
    }
    final_state = deep_research_graph.invoke(state)
    return DeepResearchResponse(
        summary=final_state["summary"],
        kql_used=final_state["current_kql"],
        total_hits=final_state["total_hits"],
        sample_hits=final_state["sample_hits"][:5],
    )