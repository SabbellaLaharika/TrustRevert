import pytest
import uuid
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.models.queue import ContentQueue, QueueStatus
from app.models.trust import TrustStore
from app.models.action_log import ActionLog
from app.services.reversible import execute_with_reversible_log
from app.services.rollback import restore_from_log
from app.services.mutations import mutate_purge, mutate_mark_posted


@pytest.fixture
def db():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )
    TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    session = TestingSession()

    # Pre-populate trust store
    session.add(TrustStore(action_type="purge", success_count=3))
    session.add(TrustStore(action_type="mark_posted", success_count=2))
    session.commit()

    try:
        yield session
    finally:
        session.close()


def test_restore_purged_item_to_original_state(db):
    """Verifies that a purged queue item is deterministically restored to its exact prior state."""
    item = ContentQueue(
        content_text="Scheduled post for Q4 release [Do Not Delete]",
        status=QueueStatus.PENDING
    )
    db.add(item)
    db.commit()
    db.refresh(item)

    # Execute purge
    log = execute_with_reversible_log(
        db_session=db,
        action_type="purge",
        target_id=item.id,
        mutation_func=lambda tid: mutate_purge(db, tid)
    )

    db.refresh(item)
    assert item.status == QueueStatus.PURGED

    # Trigger restore
    restored = restore_from_log(db_session=db, action_id=log.action_id)
    assert restored is True

    # Verify item status returned to PENDING
    db.refresh(item)
    assert item.status == QueueStatus.PENDING
    assert item.content_text == "Scheduled post for Q4 release [Do Not Delete]"


def test_restore_decrements_trust_penalty_core_req_10(db):
    """Verifies Core Requirement 10: Rollback decrements success_count by 1 (minimum 0)."""
    purge_trust = db.query(TrustStore).filter(TrustStore.action_type == "purge").first()
    assert purge_trust.success_count == 3

    item = ContentQueue(content_text="Item to test penalty", status=QueueStatus.PENDING)
    db.add(item)
    db.commit()
    db.refresh(item)

    log = execute_with_reversible_log(
        db_session=db,
        action_type="purge",
        target_id=item.id,
        mutation_func=lambda tid: mutate_purge(db, tid)
    )

    # Restore from log
    restore_from_log(db_session=db, action_id=log.action_id)

    db.refresh(purge_trust)
    # Trust score should decrement from 3 to 2
    assert purge_trust.success_count == 2


def test_trust_penalty_floors_at_zero(db):
    """Verifies that repeated rollbacks do not decrement trust score below 0."""
    trust = db.query(TrustStore).filter(TrustStore.action_type == "purge").first()
    trust.success_count = 0
    db.commit()

    item = ContentQueue(content_text="Zero trust test", status=QueueStatus.PENDING)
    db.add(item)
    db.commit()
    db.refresh(item)

    log = execute_with_reversible_log(
        db_session=db,
        action_type="purge",
        target_id=item.id,
        mutation_func=lambda tid: mutate_purge(db, tid)
    )

    restore_from_log(db_session=db, action_id=log.action_id)

    db.refresh(trust)
    assert trust.success_count == 0


def test_restore_logs_audit_trail_entry(db):
    """Verifies that the restore operation appends a rollback entry to action_log."""
    item = ContentQueue(content_text="Audit trail test", status=QueueStatus.PENDING)
    db.add(item)
    db.commit()
    db.refresh(item)

    log = execute_with_reversible_log(
        db_session=db,
        action_type="mark_posted",
        target_id=item.id,
        mutation_func=lambda tid: mutate_mark_posted(db, tid)
    )

    restore_from_log(db_session=db, action_id=log.action_id)

    # Find the rollback log
    rollback_log = db.query(ActionLog).filter(
        ActionLog.action_type == "rollback_mark_posted"
    ).first()

    assert rollback_log is not None
    assert rollback_log.target_row_id == item.id
    assert rollback_log.new_state["status"] == "PENDING"


def test_restore_invalid_action_id_raises_error(db):
    """Verifies that attempting to restore a non-existent action_id raises ValueError."""
    with pytest.raises(ValueError, match="not found"):
        restore_from_log(db_session=db, action_id=str(uuid.uuid4()))
