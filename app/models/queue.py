import enum
from sqlalchemy import Column, Integer, String, Enum as SAEnum, DateTime, func
from app.core.database import Base


class QueueStatus(str, enum.Enum):
    PENDING = "PENDING"
    POSTED = "POSTED"
    FAILED = "FAILED"
    PURGED = "PURGED"


class ContentQueue(Base):
    __tablename__ = "content_queue"

    id = Column(Integer, primary_key=True, index=True)
    content_text = Column(String, nullable=False)
    status = Column(
        SAEnum(QueueStatus, native_enum=False, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=QueueStatus.PENDING
    )
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "content_text": self.content_text,
            "status": self.status.value if isinstance(self.status, QueueStatus) else str(self.status),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
