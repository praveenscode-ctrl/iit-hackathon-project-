from pydantic import BaseModel
from typing import Optional, List, Dict, Any

class AiQueryRequest(BaseModel):
    class_id: Optional[str] = None
    query_text: str

class AiQueryResponse(BaseModel):
    intent: str
    query_text: str
    result: Dict[str, Any]
    action_links: List[Dict[str, str]]
    needs_clarification: bool = False
