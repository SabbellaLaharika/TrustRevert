from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.queue import ContentQueue, QueueStatus
from app.models.trust import TrustStore
from app.models.action_log import ActionLog
from app.schemas.api_models import QueueItemCreate, QueueItemResponse

router = APIRouter(prefix="/api", tags=["Content Queue & Audit"])


@router.get("/queue", response_model=List[QueueItemResponse])
def list_queue_items(
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """List items currently in the content queue."""
    query = db.query(ContentQueue)
    if status:
        query = query.filter(ContentQueue.status == status)
    items = query.order_by(ContentQueue.id).all()
    return [item.to_dict() for item in items]


@router.get("/queue/{item_id}", response_model=QueueItemResponse)
def get_queue_item(item_id: int, db: Session = Depends(get_db)):
    """Fetch details of a single queue item."""
    item = db.query(ContentQueue).filter(ContentQueue.id == item_id).first()
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Queue item {item_id} not found."
        )
    return item.to_dict()


@router.post("/queue", response_model=QueueItemResponse, status_code=status.HTTP_201_CREATED)
def create_queue_item(
    payload: QueueItemCreate,
    db: Session = Depends(get_db)
):
    """Create a new item in the content queue."""
    status_enum = QueueStatus(payload.status) if payload.status else QueueStatus.PENDING
    item = ContentQueue(
        content_text=payload.content_text,
        status=status_enum
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item.to_dict()


@router.get("/trust")
def list_trust_scores(db: Session = Depends(get_db)):
    """List trust counters across all action types."""
    records = db.query(TrustStore).all()
    return [r.to_dict() for r in records]


@router.get("/logs")
def list_action_logs(target_id: Optional[int] = None, db: Session = Depends(get_db)):
    """Query append-only action logs for auditing."""
    query = db.query(ActionLog)
    if target_id is not None:
        query = query.filter(ActionLog.target_row_id == target_id)
    logs = query.order_by(ActionLog.executed_at.desc()).all()
    return [l.to_dict() for l in logs]
