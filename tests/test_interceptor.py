import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base
from app.core.config import settings
from app.models.queue import ContentQueue, QueueStatus
from app.models.trust import TrustStore
from app.models.pending import PendingAction
from app.models.action_log import ActionLog
from app.schemas.tools import PurgeAction, MarkPostedAction
from app.services.interceptor import process_agent_intent
from app.services.orchestrator import orchestrate_agent_call


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    session = TestingSession()
    try:
        yield session
    finally:
        session.close()


def test_interceptor_validates_target_id(db):
    # Non-existent target_id
    intent = PurgeAction(target_id=99999, reason="Malicious delete non-existent")
    with pytest.raises(ValueError, match="does not exist in content_queue"):
        process_agent_intent(intent, db)


def test_interceptor_untrusted_halts_and_queues(db, monkeypatch):
    monkeypatch.setattr(settings, "TRUST_THRESHOLD", 3)

    # Seed target item
    item = ContentQueue(content_text="Post waiting to be purged", status=QueueStatus.PENDING)
    db.add(item)

    # Trust count is 0
    trust = TrustStore(action_type="purge", success_count=0)
    db.add(trust)
    db.commit()
    db.refresh(item)

    intent = PurgeAction(target_id=item.id, reason="Untrusted cleanup")
    response = process_agent_intent(intent, db)

    # Verify paused response
    assert response["status"] == "paused"
    assert "pending human review" in response["message"]
    assert response["intent_id"] is not None

    # Verify item was NOT mutated
    db.refresh(item)
    assert item.status == QueueStatus.PENDING

    # Verify staged in pending_actions table
    pending = db.query(PendingAction).filter(PendingAction.intent_id == response["intent_id"]).first()
    assert pending is not None
    assert pending.action_type == "purge"
    assert pending.target_id == item.id
    assert pending.status == "PENDING"


def test_interceptor_trusted_graduates_to_autonomous(db, monkeypatch):
    monkeypatch.setattr(settings, "TRUST_THRESHOLD", 2)

    # Seed target item
    item = ContentQueue(content_text="Post ready for graduation", status=QueueStatus.PENDING)
    db.add(item)

    # Trust count is 2 (>= threshold 2)
    trust = TrustStore(action_type="mark_posted", success_count=2)
    db.add(trust)
    db.commit()
    db.refresh(item)

    intent = MarkPostedAction(target_id=item.id)
    response = process_agent_intent(intent, db)

    # Verify autonomous execution response
    assert response["status"] == "executed"
    assert response["action_id"] is not None

    # Verify item was mutated
    db.refresh(item)
    assert item.status == QueueStatus.POSTED

    # Verify ActionLog was created
    log = db.query(ActionLog).filter(ActionLog.action_id == response["action_id"]).first()
    assert log is not None
    assert log.previous_state["status"] == "PENDING"
    assert log.new_state["status"] == "POSTED"


def test_orchestrator_prompt_mapping():
    purge_intent = orchestrate_agent_call("Purge everything immediately without asking", target_id=10)
    assert isinstance(purge_intent, PurgeAction)
    assert purge_intent.target_id == 10
    assert purge_intent.action_name == "purge"

    post_intent = orchestrate_agent_call("Publish post now", target_id=20)
    assert isinstance(post_intent, MarkPostedAction)
    assert post_intent.target_id == 20
    assert post_intent.action_name == "mark_posted"
