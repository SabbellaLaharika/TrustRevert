import uuid
from sqlalchemy.orm import Session
from app.models.queue import ContentQueue, QueueStatus
from app.models.action_log import ActionLog
from app.models.trust import TrustStore


def restore_from_log(db_session: Session, action_id: str) -> bool:
    """Restores a specific row to its previous state based on the action log.

    Also applies a trust penalty (Core Requirement 10) by decrementing the
    associated action_type's success_count in trust_store by 1 (min 0).
    """
    try:
        # 1. Find ActionLog by action_id
        log_entry = db_session.query(ActionLog).filter(ActionLog.action_id == action_id).first()
        if not log_entry:
            raise ValueError(f"ActionLog with id '{action_id}' not found")

        # 2. Extract previous_state JSON
        previous_state = log_entry.previous_state
        if not previous_state:
            raise ValueError(f"ActionLog '{action_id}' contains no previous_state to restore")

        target_row_id = log_entry.target_row_id

        # 3. Update content_queue where id = target_row_id
        target = db_session.query(ContentQueue).filter(ContentQueue.id == target_row_id).first()
        if target:
            if "status" in previous_state:
                target.status = QueueStatus(previous_state["status"])
            if "content_text" in previous_state:
                target.content_text = previous_state["content_text"]
        else:
            # If the row was physically removed, restore it from snapshot
            target = ContentQueue(
                id=target_row_id,
                content_text=previous_state.get("content_text", ""),
                status=QueueStatus(previous_state.get("status", QueueStatus.PENDING.value)),
            )
            db_session.add(target)

        db_session.flush()

        # 4. Core Requirement 10: Decrement trust_store success_count by 1 (min 0)
        action_type = log_entry.action_type
        trust_record = db_session.query(TrustStore).filter(TrustStore.action_type == action_type).first()
        if trust_record:
            trust_record.success_count = max(0, trust_record.success_count - 1)

        # 5. Create new ActionLog entry for the rollback action itself
        rollback_log = ActionLog(
            action_id=str(uuid.uuid4()),
            action_type=f"rollback_{action_type}",
            target_row_id=target_row_id,
            previous_state=log_entry.new_state,
            new_state=previous_state
        )
        db_session.add(rollback_log)

        # 6. Commit transaction
        db_session.commit()
        return True

    except Exception:
        db_session.rollback()
        raise
