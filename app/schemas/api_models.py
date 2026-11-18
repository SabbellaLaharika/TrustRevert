from pydantic import BaseModel, Field
from typing import Optional, List, Any


class RestoreRequest(BaseModel):
    action_id: str = Field(..., description="The action_id (UUID) to revert")


class RestoreResponse(BaseModel):
    success: bool
    message: str
    action_id: str
    reverted_target_id: Optional[int] = None
    action_type: Optional[str] = None
    new_trust_count: Optional[int] = None


class QueueItemCreate(BaseModel):
    content_text: str
    status: Optional[str] = "PENDING"


class QueueItemResponse(BaseModel):
    id: int
    content_text: str
    status: str
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class PendingActionResponse(BaseModel):
    intent_id: str
    action_type: str
    target_id: int
    reason: Optional[str] = None
    payload: Optional[Any] = None
    status: str
    created_at: Optional[str] = None


class ApproveResponse(BaseModel):
    success: bool
    message: str
    intent_id: str
    action_id: str
    action_type: str
    target_id: int
    new_trust_count: int
