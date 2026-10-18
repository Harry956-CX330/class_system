"""独立的扫码签到持久化存储。

签到任务和记录使用单独的 SQLite 文件 qr_checkin.db，不修改主库 data.db 的
表结构，从而不触发主库启动时的 schema 校验失败。
"""
import os
from datetime import datetime, timedelta, timezone

from sqlalchemy import Column, DateTime, Integer, String, UniqueConstraint, create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from config import DATA_DIR

BEIJING_TZ = timezone(timedelta(hours=8))


def beijing_now():
    return datetime.now(BEIJING_TZ).replace(tzinfo=None)


QR_DATABASE_URL = os.environ.get(
    "QR_DATABASE_URL",
    f"sqlite:///{(DATA_DIR / 'qr_checkin.db').as_posix()}",
)
qr_engine = create_engine(
    QR_DATABASE_URL,
    connect_args={"check_same_thread": False, "timeout": 15},
    pool_size=4,
    max_overflow=0,
    pool_timeout=15,
    pool_pre_ping=True,
)


@event.listens_for(qr_engine, "connect")
def configure_sqlite(connection, _record):
    cursor = connection.cursor()
    cursor.execute("PRAGMA busy_timeout=15000")
    cursor.execute("PRAGMA cache_size=-4096")
    cursor.execute("PRAGMA temp_store=FILE")
    cursor.close()


QrSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=qr_engine)


class QrBase(DeclarativeBase):
    pass


class CheckinTask(QrBase):
    """限时扫码签到任务（静态/动态二维码）"""
    __tablename__ = "checkin_tasks"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    duration_minutes = Column(Integer, nullable=False)
    qr_type = Column(String(20), nullable=False, default="static")  # static / dynamic
    refresh_seconds = Column(Integer, nullable=True)               # dynamic 刷新间隔：3/5/10
    current_code = Column(String(64), nullable=False, index=True)   # 当前有效签到 code
    code_updated_at = Column(DateTime, default=beijing_now)
    status = Column(String(20), nullable=False, default="active")   # active / closed
    started_at = Column(DateTime, default=beijing_now)
    expires_at = Column(DateTime, nullable=False)
    closed_at = Column(DateTime, nullable=True)
    author_id = Column(Integer, nullable=False, index=True)
    created_at = Column(DateTime, default=beijing_now)


class CheckinRecord(QrBase):
    """签到记录：防重复提交 + 生成名单"""
    __tablename__ = "checkin_records"
    __table_args__ = (
        UniqueConstraint("task_id", "student_id", name="uq_checkin_task_student"),
        UniqueConstraint("task_id", "device_id", name="uq_checkin_task_device"),
    )

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, nullable=False, index=True)
    student_id = Column(Integer, nullable=False, index=True)
    device_id = Column(String(128), nullable=True, index=True)
    status = Column(String(20), nullable=False, default="auto")  # auto / manual / leave
    sign_time = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=beijing_now)


def get_qr_db():
    db = QrSessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
