import json
import os
import uuid
from datetime import datetime, timezone
from typing import Dict, Any
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.queue import ContentQueue
from app.models.trust import TrustStore
from app.models.pending import PendingAction
from app.schemas.tools import ToolCallIntent
from app.services.reversible import execute_with_reversible_log
from app.services.mutations import get_mutation_func

def append_trace(trace_data: Dict[str, Any]) -> None:
    """Appends execution trace to traces.jsonl for replayability and auditability."""
    try:
        with open(settings.TRACES_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(trace_data, default=str) + "\n")
    except Exception:
        pass


def get_or_create_trust_record(db_session: Session, action_type: str) -> TrustStore:
    record = db_session.query(TrustStore).filter(TrustStore.action_type == action_type).first()
    if not record:
        record = TrustStore(action_type=action_type, success_count=0)
        db_session.add(record)
        db_session.commit()
        db_session.refresh(record)
    return record


def validate_target_id(db_session: Session, target_id: int) -> ContentQueue:
    target = db_session.query(ContentQueue).filter(ContentQueue.id == target_id).first()
    if not target:
        raise ValueError(f"Validation Error: Target row ID {target_id} does not exist in content_queue.")
    return target


def process_agent_intent(intent: ToolCallIntent, db_session: Session) -> Dict[str, Any]:
    """Intercepts LLM tool intents and applies structural trust logic.

    1. Validates target_id exists in content_queue (fails fast if invalid).
    2. Checks trust_store for that action_type.
    3. If success_count >= TRUST_THRESHOLD:
           Autonomously executes via execute_with_reversible_log().
    4. Else:
           Halts execution, creates persistent PendingAction record.
           Returns deterministic simulation response.
    """
    # 1. Validate target_id against the database
    validate_target_id(db_session, intent.target_id)

    action_type = intent.action_name
    trust_record = get_or_create_trust_record(db_session, action_type)

    # 2. Check trust threshold
    if trust_record.success_count >= settings.TRUST_THRESHOLD:
        # Trusted: Autonomous execution
        mutation_func = get_mutation_func(action_type)
        log_entry = execute_with_reversible_log(
            db_session=db_session,
            action_type=action_type,
            target_id=intent.target_id,
            mutation_func=lambda tid: mutation_func(db_session, tid)
        )
        append_trace({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "target_id": intent.target_id,
            "action": action_type,
            "validated_payload": intent.model_dump(),
            "guardrail_checks": {
                "id_exists": True,
                "trust_threshold_passed": True,
                "trust_score": trust_record.success_count,
                "threshold": settings.TRUST_THRESHOLD,
            },
            "outcome": "executed_autonomously",
            "action_id": log_entry.action_id,
        })
        return {
            "status": "executed",
            "message": f"Action '{action_type}' executed autonomously (trust level: {trust_record.success_count}/{settings.TRUST_THRESHOLD}).",
            "action_id": log_entry.action_id,
            "action_name": action_type,
            "target_id": intent.target_id,
        }
    else:
        # Untrusted: Stage in pending queue for Human-In-The-Loop review
        pending = PendingAction(
            intent_id=str(uuid.uuid4()),
            action_type=action_type,
            target_id=intent.target_id,
            reason=getattr(intent, "reason", None),
            payload=intent.model_dump(),
            status="PENDING"
        )
        db_session.add(pending)
        db_session.commit()
        db_session.refresh(pending)

        append_trace({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "target_id": intent.target_id,
            "action": action_type,
            "validated_payload": intent.model_dump(),
            "guardrail_checks": {
                "id_exists": True,
                "trust_threshold_passed": False,
                "trust_score": trust_record.success_count,
                "threshold": settings.TRUST_THRESHOLD,
            },
            "outcome": "paused_pending_hitl",
            "intent_id": pending.intent_id,
        })

        return {
            "status": "paused",
            "message": "Action registered and pending human review.",
            "intent_id": pending.intent_id,
            "action_name": action_type,
            "target_id": intent.target_id,
        }
