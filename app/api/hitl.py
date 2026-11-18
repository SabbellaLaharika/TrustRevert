from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.pending import PendingAction
from app.models.trust import TrustStore
from app.schemas.api_models import PendingActionResponse, ApproveResponse
from app.services.reversible import execute_with_reversible_log
from app.services.mutations import get_mutation_func
from app.services.interceptor import get_or_create_trust_record

router = APIRouter(prefix="/api/hitl", tags=["Human-in-the-Loop"])


@router.get("/pending", response_model=List[PendingActionResponse])
def get_pending_actions(db: Session = Depends(get_db)):
    """Returns an array of paused tool execution intents awaiting human review."""
    pending_items = db.query(PendingAction).filter(PendingAction.status == "PENDING").all()
    return [item.to_dict() for item in pending_items]


@router.post("/approve/{intent_id}", response_model=ApproveResponse)
def approve_pending_action(intent_id: str, db: Session = Depends(get_db)):
    """Approves and executes a paused tool execution intent.

    1. Executes the paused mutation against the database.
    2. Captures the before/after state in action_log.
    3. Increments the success_count for that action_type in the trust_store by 1.
    """
    pending = db.query(PendingAction).filter(
        PendingAction.intent_id == intent_id,
        PendingAction.status == "PENDING"
    ).first()

    if not pending:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pending intent '{intent_id}' not found or already processed."
        )

    action_type = pending.action_type
    target_id = pending.target_id
    mutation_func = get_mutation_func(action_type)

    try:
        # Execute mutation with reversible log
        log_entry = execute_with_reversible_log(
            db_session=db,
            action_type=action_type,
            target_id=target_id,
            mutation_func=lambda tid: mutation_func(db, tid)
        )

        # Increment success_count by 1
        trust_record = get_or_create_trust_record(db, action_type)
        trust_record.success_count += 1

        # Mark pending action as APPROVED
        pending.status = "APPROVED"

        db.commit()
        db.refresh(trust_record)

        return {
            "success": True,
            "message": f"Action '{action_type}' on item {target_id} approved and executed.",
            "intent_id": intent_id,
            "action_id": log_entry.action_id,
            "action_type": action_type,
            "target_id": target_id,
            "new_trust_count": trust_record.success_count,
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to execute approved action: {str(e)}"
        )


@router.post("/reject/{intent_id}")
def reject_pending_action(intent_id: str, db: Session = Depends(get_db)):
    """Rejects a paused tool execution intent without mutating the queue."""
    pending = db.query(PendingAction).filter(
        PendingAction.intent_id == intent_id,
        PendingAction.status == "PENDING"
    ).first()

    if not pending:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pending intent '{intent_id}' not found or already processed."
        )

    pending.status = "REJECTED"
    db.commit()

    return {
        "success": True,
        "message": f"Pending action '{pending.action_type}' on item {pending.target_id} was rejected.",
        "intent_id": intent_id
    }
