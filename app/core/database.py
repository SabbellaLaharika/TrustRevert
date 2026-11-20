from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from app.core.config import settings

connect_args = {"connect_timeout": 3} if "postgresql" in settings.DATABASE_URL else {}

engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    connect_args=connect_args
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db(max_retries: int = 10, retry_interval: float = 1.0):
    import sys
    import os
    if settings.TESTING or "pytest" in sys.modules or "PYTEST_CURRENT_TEST" in os.environ:
        return

    import time
    from app.models import ContentQueue, TrustStore, ActionLog, PendingAction

    # Retry loop to gracefully wait for PostgreSQL if it's still completing startup
    for attempt in range(max_retries):
        try:
            Base.metadata.create_all(bind=engine)
            break
        except Exception as e:
            if attempt < max_retries - 1 and "postgresql" in settings.DATABASE_URL:
                time.sleep(retry_interval)
            else:
                raise

    # Initialize default action types in trust_store if they do not exist
    default_actions = ["purge", "mark_posted", "retry"]
    db = SessionLocal()
    try:
        for action in default_actions:
            existing = db.query(TrustStore).filter(TrustStore.action_type == action).first()
            if not existing:
                db.add(TrustStore(action_type=action, success_count=0))
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
