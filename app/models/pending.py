import uuid
from sqlalchemy import Column, Integer, String, JSON, DateTime, ForeignKey, func
from app.core.database import Base


class PendingAction(Base):
    __tablename__ = "pending_actions"

    intent_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    action_type = Column(String, nullable=False, index=True)
    target_id = Column(Integer, ForeignKey("content_queue.id", ondelete="CASCADE"), nullable=False, index=True)
    reason = Column(String, nullable=True)
    payload = Column(JSON, nullable=True)
    status = Column(String, default="PENDING", nullable=False)  # PENDING, APPROVED, REJECTED
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    def to_dict(self):
        return {
            "intent_id": self.intent_id,
            "action_type": self.action_type,
            "target_id": self.target_id,
            "reason": self.reason,
            "payload": self.payload,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
