from __future__ import annotations

from pydantic import BaseModel
from typing import Optional, Literal


Classification = Literal["public", "internal", "confidential", "restricted"]


class UserClaims(BaseModel):
    """
    POC RBAC user model.
    In production: populate from Entra ID claims (department/team/clearance).
    """
    user_id: str
    department: Optional[str] = None
    team: Optional[str] = None
    clearance: Classification = "confidential"