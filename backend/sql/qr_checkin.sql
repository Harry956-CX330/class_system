-- 限时扫码签到模块（SQLite）
-- 生产环境启动前执行：python -m sqlite3 backend/data/data.db < backend/sql/qr_checkin.sql
-- 或使用 SQLite 客户端执行本文件。应用启动仅做只读 schema 校验，不会自动建表。
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS checkin_tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(200) NOT NULL,
    duration_minutes INTEGER NOT NULL,
    qr_type VARCHAR(20) NOT NULL DEFAULT 'static',
    refresh_seconds INTEGER,
    current_code VARCHAR(64) NOT NULL,
    code_updated_at DATETIME,
    status VARCHAR(20) NOT NULL DEFAULT 'active',
    started_at DATETIME,
    expires_at DATETIME NOT NULL,
    closed_at DATETIME,
    author_id INTEGER NOT NULL REFERENCES users(id),
    created_at DATETIME
);

CREATE INDEX IF NOT EXISTS ix_checkin_tasks_current_code ON checkin_tasks (current_code);
CREATE INDEX IF NOT EXISTS ix_checkin_tasks_author_id ON checkin_tasks (author_id);

CREATE TABLE IF NOT EXISTS checkin_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id INTEGER NOT NULL REFERENCES checkin_tasks(id) ON DELETE CASCADE,
    student_id INTEGER NOT NULL REFERENCES users(id),
    device_id VARCHAR(128),
    status VARCHAR(20) NOT NULL DEFAULT 'auto',
    sign_time DATETIME,
    created_at DATETIME,
    CONSTRAINT uq_checkin_task_student UNIQUE (task_id, student_id),
    CONSTRAINT uq_checkin_task_device UNIQUE (task_id, device_id)
);

CREATE INDEX IF NOT EXISTS ix_checkin_records_task_id ON checkin_records (task_id);
CREATE INDEX IF NOT EXISTS ix_checkin_records_student_id ON checkin_records (student_id);
CREATE INDEX IF NOT EXISTS ix_checkin_records_device_id ON checkin_records (device_id);
