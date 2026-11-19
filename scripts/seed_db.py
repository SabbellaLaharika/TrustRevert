import sys
import os

# Add root directory to path so script can import app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

from app.core.database import Base, SessionLocal, engine
from app.models.queue import ContentQueue, QueueStatus
from app.models.trust import TrustStore


def get_working_session():
    """Returns a working database session maker and engine."""
    try:
        with engine.connect() as conn:
            pass
        Base.metadata.create_all(bind=engine)
        return SessionLocal, engine
    except Exception:
        print("[Notice] PostgreSQL not accessible on localhost:5432. Using SQLite engine for seed.")
        local_engine = create_engine(
            "sqlite:///./trustrevert_simulation.db",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool
        )
        Base.metadata.create_all(bind=local_engine)
        LocalSession = sessionmaker(autocommit=False, autoflush=False, bind=local_engine)
        return LocalSession, local_engine


def seed_database():
    """Initializes tables and populates the database with 10 realistic initial rows."""
    SessionFactory, db_engine = get_working_session()
    db: Session = SessionFactory()

    try:
        # Check if rows already exist
        existing_count = db.query(ContentQueue).count()
        if existing_count >= 10:
            print(f"[Seed] Database already contains {existing_count} rows in content_queue. Skipping seed.")
            return

        sample_posts = [
            ("Excited to announce our new AI Progressive Autonomy Harness! #AI #Safety", QueueStatus.PENDING),
            ("Weekly engineering digest: Best practices for LLM structural guardrails in production", QueueStatus.POSTED),
            ("Database connection timeout during webhook retry attempt #infrastructure", QueueStatus.FAILED),
            ("Scheduled for next week: Product Launch 2.0 release notes [FUTURE-DATED]", QueueStatus.PENDING),
            ("Q3 metrics update: 99.99% uptime achieved across all distributed services", QueueStatus.PENDING),
            ("Security Advisory: Verify all tool execution harnesses use structural code constraints", QueueStatus.PENDING),
            ("Deprecation notice: Legacy advisory prompt wrappers are being sunset", QueueStatus.POSTED),
            ("Transient memory pressure while indexing content vectors #bugfix", QueueStatus.FAILED),
            ("Future feature teaser: Calibrated trust graduation engine coming soon [FUTURE-DATED]", QueueStatus.PENDING),
            ("Draft announcement: Welcome our new contributors to the open source project", QueueStatus.PENDING),
        ]

        print("[Seed] Populating initial content_queue records...")
        for text, status in sample_posts:
            item = ContentQueue(content_text=text, status=status)
            db.add(item)

        # Ensure default trust store rows exist
        for action in ["purge", "mark_posted", "retry"]:
            trust_record = db.query(TrustStore).filter(TrustStore.action_type == action).first()
            if not trust_record:
                db.add(TrustStore(action_type=action, success_count=0))

        db.commit()
        total = db.query(ContentQueue).count()
        print(f"[Seed] Successfully seeded {total} rows into content_queue and initialized trust_store!")

    except Exception as e:
        db.rollback()
        print(f"[Seed Error] Failed to seed database: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_database()
