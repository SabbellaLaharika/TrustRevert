from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from app.core.config import settings

engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    from app.models import ContentQueue, TrustStore, ActionLog, PendingAction
    Base.metadata.create_all(bind=engine)

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
