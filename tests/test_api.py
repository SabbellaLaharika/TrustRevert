import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.core.database import Base, get_db
from app.core.config import settings
from app.models.queue import ContentQueue, QueueStatus
from app.models.trust import TrustStore
from app.models.action_log import ActionLog
from app.models.pending import PendingAction


# Test SQLite database engine
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(SQLALCHEMY_DATABASE_URL)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture
def test_db():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    # Initialize default trust rows
    db.add(TrustStore(action_type="purge", success_count=0))
    db.add(TrustStore(action_type="mark_posted", success_count=0))
    db.add(TrustStore(action_type="retry", success_count=0))
    db.commit()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client(test_db):
    def override_get_db():
        try:
            yield test_db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def test_core_req_2_agent_execute_untrusted_halts(client, test_db, monkeypatch):
    monkeypatch.setattr(settings, "TRUST_THRESHOLD", 3)

    # 1. Seed row
    item = ContentQueue(content_text="Post awaiting review", status=QueueStatus.PENDING)
    test_db.add(item)
    test_db.commit()
    test_db.refresh(item)

    # 2. Call /api/agent/execute with untrusted purge intent
    response = client.post("/api/agent/execute", json={
        "prompt": "Clean queue by purging row",
        "target_id": item.id
    })

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "paused"
    assert "pending human review" in data["message"]
    assert data["intent_id"] is not None

    # 3. Verify content_queue row was NOT purged
    test_db.refresh(item)
    assert item.status == QueueStatus.PENDING


def test_core_req_3_hitl_pending_and_approve(client, test_db, monkeypatch):
    monkeypatch.setattr(settings, "TRUST_THRESHOLD", 3)

    # 1. Seed item
    item = ContentQueue(content_text="Post for HITL approval", status=QueueStatus.PENDING)
    test_db.add(item)
    test_db.commit()
    test_db.refresh(item)

    # 2. Trigger untrusted action
    exec_resp = client.post("/api/agent/execute", json={
        "prompt": "Mark as posted",
        "target_id": item.id
    })
    intent_id = exec_resp.json()["intent_id"]

    # 3. GET /api/hitl/pending
    pending_resp = client.get("/api/hitl/pending")
    assert pending_resp.status_code == 200
    pending_list = pending_resp.json()
    assert any(p["intent_id"] == intent_id for p in pending_list)

    # 4. POST /api/hitl/approve/{intent_id}
    approve_resp = client.post(f"/api/hitl/approve/{intent_id}")
    assert approve_resp.status_code == 200
    appr_data = approve_resp.json()
    assert appr_data["success"] is True
    assert appr_data["new_trust_count"] == 1

    # 5. Verify database mutation
    test_db.refresh(item)
    assert item.status == QueueStatus.POSTED

    # 6. Verify trust_store success_count incremented exactly by 1
    trust = test_db.query(TrustStore).filter(TrustStore.action_type == "mark_posted").first()
    assert trust.success_count == 1


def test_core_req_4_action_log_snapshots(client, test_db, monkeypatch):
    monkeypatch.setattr(settings, "TRUST_THRESHOLD", 1)

    item = ContentQueue(content_text="Snapshot test post", status=QueueStatus.PENDING)
    test_db.add(item)
    test_db.commit()
    test_db.refresh(item)

    # Trigger action
    exec_resp = client.post("/api/agent/execute", json={
        "prompt": "Mark this item posted",
        "target_id": item.id
    })
    intent_id = exec_resp.json()["intent_id"]

    # Approve
    client.post(f"/api/hitl/approve/{intent_id}")

    # Query action_log
    log = test_db.query(ActionLog).filter(ActionLog.target_row_id == item.id).first()
    assert log is not None
    assert log.previous_state["status"] == "PENDING"
    assert log.new_state["status"] == "POSTED"


def test_core_req_5_autonomous_graduation(client, test_db, monkeypatch):
    monkeypatch.setattr(settings, "TRUST_THRESHOLD", 2)

    # Manually set success_count = 2 for purge
    purge_trust = test_db.query(TrustStore).filter(TrustStore.action_type == "purge").first()
    purge_trust.success_count = 2
    test_db.commit()

    # Seed row with specific target
    item = ContentQueue(id=999, content_text="Graduated item", status=QueueStatus.PENDING)
    test_db.add(item)
    test_db.commit()

    # Send execute request
    response = client.post("/api/agent/execute", json={
        "prompt": "Purge item immediately",
        "target_id": 999
    })

    assert response.status_code == 200
    data = response.json()
    # Verify autonomous execution (no pending state)
    assert data["status"] == "executed"
    assert data["action_id"] is not None

    # Verify ID 999 was mutated to PURGED
    test_db.refresh(item)
    assert item.status == QueueStatus.PURGED


def test_core_req_6_and_10_deterministic_restore_with_trust_penalty(client, test_db, monkeypatch):
    monkeypatch.setattr(settings, "TRUST_THRESHOLD", 1)

    # Ensure trust count is 2 initially
    trust = test_db.query(TrustStore).filter(TrustStore.action_type == "purge").first()
    trust.success_count = 2
    test_db.commit()

    # Seed row
    item = ContentQueue(content_text="Item to be restored", status=QueueStatus.PENDING)
    test_db.add(item)
    test_db.commit()
    test_db.refresh(item)

    # Autonomously purge (since count 2 >= threshold 1)
    exec_resp = client.post("/api/agent/execute", json={
        "prompt": "Purge item",
        "target_id": item.id
    })
    action_id = exec_resp.json()["action_id"]

    test_db.refresh(item)
    assert item.status == QueueStatus.PURGED

    # Trigger POST /api/system/restore
    restore_resp = client.post("/api/system/restore", json={"action_id": action_id})
    assert restore_resp.status_code == 200
    rest_data = restore_resp.json()
    assert rest_data["success"] is True

    # Verify item status reverted to PENDING
    test_db.refresh(item)
    assert item.status == QueueStatus.PENDING

    # Verify Core Req 10: trust_store decremented by 1 (from 2 to 1)
    test_db.refresh(trust)
    assert trust.success_count == 1
