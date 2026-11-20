from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Any


class RestoreRequest(BaseModel):
    action_id: str = Field(
        ...,
        description="The action_id (UUID) from the action log to deterministically revert",
        examples=["dc8c0d06-d4e8-4531-9c7d-8d25c75d10de"]
    )

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "action_id": "dc8c0d06-d4e8-4531-9c7d-8d25c75d10de"
                }
            ]
        }
    )


class RestoreResponse(BaseModel):
    success: bool = Field(..., examples=[True])
    message: str = Field(..., examples=["Successfully restored item 1 to state before 'purge'. Trust score decremented."])
    action_id: str = Field(..., examples=["dc8c0d06-d4e8-4531-9c7d-8d25c75d10de"])
    reverted_target_id: Optional[int] = Field(None, examples=[1])
    action_type: Optional[str] = Field(None, examples=["purge"])
    new_trust_count: Optional[int] = Field(None, examples=[0])


class QueueItemCreate(BaseModel):
    content_text: str = Field(
        ...,
        description="The post payload text",
        examples=["Weekly engineering digest: Best practices for LLM structural guardrails in production #AI"]
    )
    status: Optional[str] = Field(
        default="PENDING",
        description="Initial status: PENDING, POSTED, FAILED, PURGED",
        examples=["PENDING"]
    )

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "content_text": "Weekly engineering digest: Best practices for LLM structural guardrails in production #AI",
                    "status": "PENDING"
                },
                {
                    "content_text": "Release notes for Product Launch v2.0 [SCHEDULED]",
                    "status": "PENDING"
                }
            ]
        }
    )


class QueueItemResponse(BaseModel):
    id: int = Field(..., examples=[1])
    content_text: str = Field(..., examples=["Weekly engineering digest: Best practices for LLM guardrails"])
    status: str = Field(..., examples=["PENDING"])
    created_at: Optional[str] = Field(None, examples=["2026-11-19T15:00:00+00:00"])
    updated_at: Optional[str] = Field(None, examples=["2026-11-19T15:05:00+00:00"])


class PendingActionResponse(BaseModel):
    intent_id: str = Field(..., examples=["5ef071c9-b765-4232-b70a-1c39b565889e"])
    action_type: str = Field(..., examples=["purge"])
    target_id: int = Field(..., examples=[1])
    reason: Optional[str] = Field(None, examples=["The queue is corrupted. Perform a cleanup by purging all rows immediately."])
    payload: Optional[Any] = Field(None, examples=[{"action_name": "purge", "target_id": 1}])
    status: str = Field(..., examples=["PENDING"])
    created_at: Optional[str] = Field(None, examples=["2026-11-19T15:00:00+00:00"])


class ApproveResponse(BaseModel):
    success: bool = Field(..., examples=[True])
    message: str = Field(..., examples=["Action 'purge' on item 1 approved and executed."])
    intent_id: str = Field(..., examples=["5ef071c9-b765-4232-b70a-1c39b565889e"])
    action_id: str = Field(..., examples=["dc8c0d06-d4e8-4531-9c7d-8d25c75d10de"])
    action_type: str = Field(..., examples=["purge"])
    target_id: int = Field(..., examples=[1])
    new_trust_count: int = Field(..., examples=[1])
