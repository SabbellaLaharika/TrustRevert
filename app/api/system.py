from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.action_log import ActionLog
from app.models.trust import TrustStore
from app.schemas.api_models import RestoreRequest, RestoreResponse
from app.services.rollback import restore_from_log

router = APIRouter(prefix="/api/system", tags=["System"])


@router.post("/restore", response_model=RestoreResponse)
def restore_action_state(
    request: RestoreRequest,
    db: Session = Depends(get_db)
):
    """Deterministically reverse an action using the append-only action log.

    1. Reads the action_log for the provided action_id.
    2. Extracts the previous_state JSON snapshot.
    3. Overwrites the corresponding row in content_queue with values from previous_state.
    4. Core Requirement 10: Decrements the success_count for that action_type in trust_store by 1 (min 0).
    """
    try:
        # Fetch log first to return details
        log_entry = db.query(ActionLog).filter(ActionLog.action_id == request.action_id).first()
        if not log_entry:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"ActionLog with action_id '{request.action_id}' not found."
            )

        action_type = log_entry.action_type
        target_id = log_entry.target_row_id

        # Perform rollback
        restore_from_log(db, request.action_id)

        # Get updated trust count
        trust_record = db.query(TrustStore).filter(TrustStore.action_type == action_type).first()
        new_count = trust_record.success_count if trust_record else 0

        return {
            "success": True,
            "message": f"Successfully restored item {target_id} to state before '{action_type}'. Trust score decremented.",
            "action_id": request.action_id,
            "reverted_target_id": target_id,
            "action_type": action_type,
            "new_trust_count": new_count,
        }
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Rollback failed: {str(e)}"
        )
