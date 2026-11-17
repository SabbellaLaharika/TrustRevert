import uuid
from sqlalchemy import Column, Integer, String, JSON, DateTime, ForeignKey, func
from app.core.database import Base


class ActionLog(Base):
    __tablename__ = "action_log"

    action_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    action_type = Column(String, nullable=False, index=True)
    target_row_id = Column(Integer, ForeignKey("content_queue.id", ondelete="CASCADE"), nullable=True, index=True)
    previous_state = Column(JSON, nullable=True)
    new_state = Column(JSON, nullable=True)
    executed_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    def to_dict(self):
        return {
            "action_id": self.action_id,
            "action_type": self.action_type,
            "target_row_id": self.target_row_id,
            "previous_state": self.previous_state,
            "new_state": self.new_state,
            "executed_at": self.executed_at.isoformat() if self.executed_at else None,
        }
