import os
import asyncio
from sqlalchemy import create_engine, event, inspect
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from config import DATA_DIR

SQLALCHEMY_DATABASE_URL = os.environ.get("DATABASE_URL", f"sqlite:///{(DATA_DIR / 'data.db').as_posix()}")
engine = create_engine(SQLALCHEMY_DATABASE_URL,
                       connect_args={"check_same_thread": False, "timeout": 15},
                       pool_size=4, max_overflow=0, pool_timeout=15, pool_pre_ping=True)


@event.listens_for(engine, "connect")
def configure_sqlite(connection, _record):
    cursor = connection.cursor()
    cursor.execute("PRAGMA busy_timeout=15000")
    cursor.execute("PRAGMA cache_size=-4096")
    cursor.execute("PRAGMA temp_store=FILE")
    cursor.close()


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def validate_schema():
    """Read-only check: never add tables, columns or indexes on startup."""
    inspector = inspect(engine)
    missing = []
    for table in Base.metadata.sorted_tables:
        if not inspector.has_table(table.name):
            missing.append(table.name + " (table)")
            continue
        columns = {c["name"] for c in inspector.get_columns(table.name)}
        missing.extend(f"{table.name}.{c.name}" for c in table.columns if c.name not in columns)
    if missing:
        raise RuntimeError("Database schema is incompatible; no changes were made. Missing: " + ", ".join(missing))


_session_slots = asyncio.Semaphore(4)


async def get_db():
    # Wait before entering a sync auth/route worker. Otherwise all workers can
    # block waiting for connections held by requests whose routes cannot run.
    async with _session_slots:
        with SessionLocal() as db:
            try:
                yield db
            except Exception:
                db.rollback()
                raise
