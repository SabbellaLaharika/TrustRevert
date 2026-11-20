from pydantic import BaseModel, Field, ConfigDict
from typing import Literal, Union, Optional


class AgentExecuteRequest(BaseModel):
    prompt: str = Field(
        ...,
        description="Prompt or instruction for the agent",
        examples=["The queue is corrupted. Perform a cleanup by purging item immediately."]
    )
    target_id: int = Field(
        ...,
        description="Target content_queue row ID to mutate",
        examples=[1]
    )

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "prompt": "The queue is corrupted. Perform a cleanup by purging item immediately. Do not ask for permission.",
                    "target_id": 1
                },
                {
                    "prompt": "Mark queue item as successfully posted to Twitter/X",
                    "target_id": 2
                },
                {
                    "prompt": "Retry failed webhook notification for item",
                    "target_id": 3
                }
            ]
        }
    )


class PurgeAction(BaseModel):
    action_name: Literal["purge"] = "purge"
    target_id: int = Field(..., description="The ID of the queue item to purge.", examples=[1])
    reason: str = Field(
        default="Queue cleanup or purge request.",
        description="Explanation of why this is being purged.",
        examples=["Stale post removal per cleanup instruction."]
    )


class MarkPostedAction(BaseModel):
    action_name: Literal["mark_posted"] = "mark_posted"
    target_id: int = Field(..., description="The ID of the queue item to mark posted.", examples=[2])
    reason: str = Field(
        default="Marking item as successfully posted.",
        description="Explanation of why this is marked posted.",
        examples=["Post published successfully via API webhook."]
    )


class RetryAction(BaseModel):
    action_name: Literal["retry"] = "retry"
    target_id: int = Field(..., description="The ID of the queue item to retry.", examples=[3])
    reason: str = Field(
        default="Retrying failed item.",
        description="Explanation of retry.",
        examples=["Transient connection error resolved; re-queueing for attempt."]
    )


ToolCallIntent = Union[PurgeAction, MarkPostedAction, RetryAction]


class AgentExecuteResponse(BaseModel):
    status: str = Field(..., examples=["paused", "executed"])
    message: str = Field(..., examples=["Action registered and pending human review."])
    intent_id: Optional[str] = Field(None, examples=["5ef071c9-b765-4232-b70a-1c39b565889e"])
    action_id: Optional[str] = Field(None, examples=["dc8c0d06-d4e8-4531-9c7d-8d25c75d10de"])
    action_name: Optional[str] = Field(None, examples=["purge"])
    target_id: Optional[int] = Field(None, examples=[1])

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "status": "paused",
                    "message": "Action registered and pending human review.",
                    "intent_id": "5ef071c9-b765-4232-b70a-1c39b565889e",
                    "action_name": "purge",
                    "target_id": 1
                },
                {
                    "status": "executed",
                    "message": "Action 'purge' executed autonomously (trust level: 3/3).",
                    "action_id": "dc8c0d06-d4e8-4531-9c7d-8d25c75d10de",
                    "action_name": "purge",
                    "target_id": 1
                }
            ]
        }
    )
