import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.database import Base
from app.models.queue import ContentQueue, QueueStatus
from app.models.trust import TrustStore
from app.models.action_log import ActionLog
from app.models.pending import PendingAction


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


def test_content_queue_model(db_session):
    item = ContentQueue(content_text="Test post", status=QueueStatus.PENDING)
    db_session.add(item)
    db_session.commit()
    db_session.refresh(item)

    assert item.id is not None
    assert item.content_text == "Test post"
    assert item.status == QueueStatus.PENDING
    assert item.created_at is not None

    # Test dictionary serialization
    d = item.to_dict()
    assert d["status"] == "PENDING"
    assert d["content_text"] == "Test post"


def test_trust_store_model(db_session):
    trust = TrustStore(action_type="purge")
    db_session.add(trust)
    db_session.commit()
    db_session.refresh(trust)

    assert trust.action_type == "purge"
    assert trust.success_count == 0


def test_action_log_model(db_session):
    item = ContentQueue(content_text="Reversible item", status=QueueStatus.PENDING)
    db_session.add(item)
    db_session.commit()
    db_session.refresh(item)

    log = ActionLog(
        action_type="mark_posted",
        target_row_id=item.id,
        previous_state={"status": "PENDING"},
        new_state={"status": "POSTED"}
    )
    db_session.add(log)
    db_session.commit()
    db_session.refresh(log)

    assert log.action_id is not None
    assert log.action_type == "mark_posted"
    assert log.target_row_id == item.id
    assert log.previous_state == {"status": "PENDING"}
    assert log.new_state == {"status": "POSTED"}


def test_pending_action_model(db_session):
    item = ContentQueue(content_text="Untrusted item", status=QueueStatus.PENDING)
    db_session.add(item)
    db_session.commit()
    db_session.refresh(item)

    pending = PendingAction(
        action_type="purge",
        target_id=item.id,
        reason="Stale item cleanup",
        payload={"action_name": "purge", "target_id": item.id}
    )
    db_session.add(pending)
    db_session.commit()
    db_session.refresh(pending)

    assert pending.intent_id is not None
    assert pending.status == "PENDING"
    assert pending.action_type == "purge"
