from app.schemas.tools import PurgeAction, MarkPostedAction, RetryAction, ToolCallIntent


def orchestrate_agent_call(prompt: str, target_id: int) -> ToolCallIntent:
    """Simulates/orchestrates the LLM turning an instruction into a validated Pydantic tool call intent.

    Never gives the LLM direct DB access; the LLM merely emits the typed intent schema.
    """
    prompt_lower = prompt.lower()

    if any(k in prompt_lower for k in ["post", "posted", "mark_posted", "publish"]):
        return MarkPostedAction(
            target_id=target_id,
            reason=f"Action formulated from prompt: '{prompt}'"
        )
    elif any(k in prompt_lower for k in ["retry", "re-queue", "re-try"]):
        return RetryAction(
            target_id=target_id,
            reason=f"Action formulated from prompt: '{prompt}'"
        )
    else:
        # Default or destructive intents ('purge', 'delete', 'clean', 'cleanup', 'remove')
        return PurgeAction(
            target_id=target_id,
            reason=f"Action formulated from prompt: '{prompt}'"
        )
