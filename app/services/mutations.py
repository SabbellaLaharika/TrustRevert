from sqlalchemy.orm import Session
from app.models.queue import ContentQueue, QueueStatus


def mutate_purge(db_session: Session, target_id: int):
    item = db_session.query(ContentQueue).filter(ContentQueue.id == target_id).first()
    if not item:
        raise ValueError(f"ContentQueue item {target_id} not found")
    item.status = QueueStatus.PURGED
    return item


def mutate_mark_posted(db_session: Session, target_id: int):
    item = db_session.query(ContentQueue).filter(ContentQueue.id == target_id).first()
    if not item:
        raise ValueError(f"ContentQueue item {target_id} not found")
    item.status = QueueStatus.POSTED
    return item


def mutate_retry(db_session: Session, target_id: int):
    item = db_session.query(ContentQueue).filter(ContentQueue.id == target_id).first()
    if not item:
        raise ValueError(f"ContentQueue item {target_id} not found")
    item.status = QueueStatus.PENDING
    return item


def mutate_mark_failed(db_session: Session, target_id: int):
    item = db_session.query(ContentQueue).filter(ContentQueue.id == target_id).first()
    if not item:
        raise ValueError(f"ContentQueue item {target_id} not found")
    item.status = QueueStatus.FAILED
    return item


MUTATION_REGISTRY = {
    "purge": mutate_purge,
    "mark_posted": mutate_mark_posted,
    "retry": mutate_retry,
    "mark_failed": mutate_mark_failed,
}


def get_mutation_func(action_type: str):
    if action_type not in MUTATION_REGISTRY:
        raise ValueError(f"Unknown action_type '{action_type}'. Supported actions: {list(MUTATION_REGISTRY.keys())}")
    return MUTATION_REGISTRY[action_type]
