import uuid
from typing import Callable, Any
from sqlalchemy.orm import Session
from app.models.queue import ContentQueue, QueueStatus
from app.models.action_log import ActionLog


def execute_with_reversible_log(
    db_session: Session,
    action_type: str,
    target_id: int,
    mutation_func: Callable[..., Any]
) -> ActionLog:
    """Executes a mutation while capturing reversible state.

    Operates within a strict transactional boundary:
    1. Fetch current state of target_id from content_queue
    2. Serialize current state to JSON (previous_state)
    3. Execute mutation_func
    4. Fetch new state of target_id
    5. Serialize new state to JSON (new_state)
    6. Insert into ActionLog
    7. Commit transaction (rolls back on any failure)
    """
    try:
        # 1. Fetch current state
        target = db_session.query(ContentQueue).filter(ContentQueue.id == target_id).first()
        if not target:
            raise ValueError(f"ContentQueue row with ID {target_id} not found")

        # 2. Serialize current state to dict (previous_state)
        previous_state = target.to_dict()

        # 3. Execute mutation
        try:
            mutation_func(target_id)
        except TypeError:
            # Fallback if mutation_func expects db_session as well
            mutation_func(db_session, target_id)

        db_session.flush()

        # 4. Fetch new state
        db_session.refresh(target)
        new_state = target.to_dict()

        # 5. Create action log entry
        action_log = ActionLog(
            action_id=str(uuid.uuid4()),
            action_type=action_type,
            target_row_id=target_id,
            previous_state=previous_state,
            new_state=new_state
        )
        db_session.add(action_log)

        # 6. Commit transaction
        db_session.commit()
        db_session.refresh(action_log)
        return action_log

    except Exception:
        db_session.rollback()
        raise
