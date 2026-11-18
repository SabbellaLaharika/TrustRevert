from pydantic import BaseModel, Field
from typing import Literal, Union, Optional


class AgentExecuteRequest(BaseModel):
    prompt: str = Field(..., description="Prompt or instruction for the agent")
    target_id: int = Field(..., description="Target content_queue ID")


class PurgeAction(BaseModel):
    action_name: Literal["purge"] = "purge"
    target_id: int = Field(..., description="The ID of the queue item to purge.")
    reason: str = Field(default="Queue cleanup or purge request.", description="Explanation of why this is being purged.")


class MarkPostedAction(BaseModel):
    action_name: Literal["mark_posted"] = "mark_posted"
    target_id: int = Field(..., description="The ID of the queue item to mark posted.")
    reason: str = Field(default="Marking item as successfully posted.", description="Explanation of why this is marked posted.")


class RetryAction(BaseModel):
    action_name: Literal["retry"] = "retry"
    target_id: int = Field(..., description="The ID of the queue item to retry.")
    reason: str = Field(default="Retrying failed item.", description="Explanation of retry.")


ToolCallIntent = Union[PurgeAction, MarkPostedAction, RetryAction]


class AgentExecuteResponse(BaseModel):
    status: str
    message: str
    intent_id: Optional[str] = None
    action_id: Optional[str] = None
    action_name: Optional[str] = None
    target_id: Optional[int] = None
