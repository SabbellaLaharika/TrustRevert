import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.database import Base
from app.models.queue import ContentQueue, QueueStatus
from app.models.trust import TrustStore
from app.models.action_log import ActionLog
from app.services.reversible import execute_with_reversible_log
from app.services.rollback import restore_from_log
from app.services.mutations import mutate_purge, mutate_mark_posted


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


def test_execute_with_reversible_log_success(db):
    # Seed item
    item = ContentQueue(content_text="Draft post", status=QueueStatus.PENDING)
    db.add(item)
    db.commit()
    db.refresh(item)

    # Execute mark_posted
    log_entry = execute_with_reversible_log(
        db_session=db,
        action_type="mark_posted",
        target_id=item.id,
        mutation_func=lambda tid: mutate_mark_posted(db, tid)
    )

    # Verify log contents
    assert log_entry.action_id is not None
    assert log_entry.action_type == "mark_posted"
    assert log_entry.target_row_id == item.id
    assert log_entry.previous_state["status"] == "PENDING"
    assert log_entry.new_state["status"] == "POSTED"

    # Verify database was mutated
    db.refresh(item)
    assert item.status == QueueStatus.POSTED


def test_execute_with_reversible_log_fail_closed(db):
    # Seed item
    item = ContentQueue(content_text="Immutable post", status=QueueStatus.PENDING)
    db.add(item)
    db.commit()
    db.refresh(item)

    # Mutation that throws an error
    def failing_mutation(tid):
        item.status = QueueStatus.PURGED
        raise RuntimeError("Simulated mid-mutation crash!")

    with pytest.raises(RuntimeError):
        execute_with_reversible_log(
            db_session=db,
            action_type="purge",
            target_id=item.id,
            mutation_func=failing_mutation
        )

    # Verify status did not change and no log was committed
    db.refresh(item)
    assert item.status == QueueStatus.PENDING
    logs = db.query(ActionLog).all()
    assert len(logs) == 0


def test_restore_from_log_with_trust_penalty(db):
    # Seed trust store with initial count 2
    trust = TrustStore(action_type="purge", success_count=2)
    db.add(trust)

    # Seed content queue item
    item = ContentQueue(content_text="Delete me later", status=QueueStatus.PENDING)
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

    # Now restore from log
    success = restore_from_log(db_session=db, action_id=log.action_id)
    assert success is True

    # Verify content_queue item reverted to PENDING
    db.refresh(item)
    assert item.status == QueueStatus.PENDING

    # Verify Core Requirement 10: trust_store success_count decremented from 2 to 1
    db.refresh(trust)
    assert trust.success_count == 1

    # Verify rollback action was logged
    rollback_log = db.query(ActionLog).filter(ActionLog.action_type == "rollback_purge").first()
    assert rollback_log is not None
    assert rollback_log.target_row_id == item.id
    assert rollback_log.new_state["status"] == "PENDING"
