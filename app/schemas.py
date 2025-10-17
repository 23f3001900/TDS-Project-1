from pydantic import BaseModel
from typing import List, Optional


class BuildRequest(BaseModel):
    email: str
    secret: str
    task: str
    round: int
    nonce: str
    brief: str
    evaluation_url: str
    attachments: List[str] = []
    repo_url: Optional[str] = None   # ✅ add this line for round 2
