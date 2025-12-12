# agents/models.py
from pydantic import BaseModel, Field
from typing import Optional, Any, List, Dict

class KqlRequest(BaseModel):
    description: str = Field(..., description="Human description of what logs to find")

class KqlResponse(BaseModel):
    kql: str

class ElkQueryRequest(BaseModel):
    kql: str
    size: int = Field(100, le=10_000, description="How many docs to return")

class ElkQueryResponse(BaseModel):
    total: int
    hits: List[Dict[str, Any]]

class DeepResearchRequest(BaseModel):
    description: str
    max_iterations: int = Field(3, le=10, description="How many refinement steps")

class DeepResearchResponse(BaseModel):
    summary: str
    kql_used: str
    total_hits: int
    sample_hits: List[Dict[str, Any]]