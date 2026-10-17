"""Resource budgets for the single-process FastAPI/SQLite deployment."""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = Path(os.environ.get("DATA_DIR", BASE_DIR / "data")).resolve()
UPLOAD_DIR = str(Path(os.environ.get("UPLOAD_DIR", BASE_DIR / "static" / "uploads")).resolve())
TEMP_DIR = Path(os.environ.get("TEMP_DIR", DATA_DIR / "tmp")).resolve()
FRONTEND_DIST = Path(os.environ.get("FRONTEND_DIST", BASE_DIR / "static" / "dist")).resolve()
SMTP_CONFIG_PATH = os.environ.get("SMTP_CONFIG_PATH", str(BASE_DIR / "smtp_config.json"))
KDOCS_CONFIG_PATH = os.environ.get("KDOCS_CONFIG_PATH", str(BASE_DIR / "kdocs_config.json"))
TEMPLATES_DIR = str(BASE_DIR / "static" / "templates")


def positive_int(name, default):
    value = int(os.environ.get(name, default))
    if value < 1:
        raise ValueError(f"{name} must be positive")
    return value


MAX_UPLOAD_BYTES = positive_int("MAX_UPLOAD_MB", 100) * 1024 * 1024
MAX_IMPORT_BYTES = positive_int("MAX_IMPORT_MB", 5) * 1024 * 1024
MAX_UPLOADS = positive_int("MAX_CONCURRENT_UPLOADS", 2)
MAX_DOWNLOADS = positive_int("MAX_CONCURRENT_DOWNLOADS", 4)
MAX_ARCHIVES = positive_int("MAX_CONCURRENT_ARCHIVES", 1)
MAX_ARCHIVE_BYTES = positive_int("MAX_ARCHIVE_MB", 2048) * 1024 * 1024
MIN_FREE_BYTES = positive_int("MIN_FREE_DISK_MB", 256) * 1024 * 1024
THREAD_TOKENS = positive_int("THREAD_TOKENS", 8)
ZIP_BATCH_MAX_SIZE = 50 * 1024 * 1024
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
DOCUMENT_EXTENSIONS = {".pdf", ".doc", ".docx"}
ALLOWED_DOC_EXTENSIONS = DOCUMENT_EXTENSIONS | ALLOWED_EXTENSIONS | {
    ".xls", ".xlsx", ".ppt", ".pptx", ".txt", ".zip", ".rar",
}
CORS_ORIGINS = [s.strip() for s in os.environ.get(
    "CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173,http://localhost:5174,http://127.0.0.1:5174,http://8.163.67.49:8000"
).split(",") if s.strip()]


def prepare_directories():
    for path in (DATA_DIR, Path(UPLOAD_DIR), TEMP_DIR, Path(TEMPLATES_DIR)):
        path.mkdir(parents=True, exist_ok=True)

# Leave bandwidth for API requests and QQ/SMTP on the 3 Mbps uplink.
DOWNLOAD_BYTES_PER_SECOND = positive_int("DOWNLOAD_KIB_PER_SECOND", 280) * 1024
PUBLIC_BASE_URL = os.environ.get("PUBLIC_BASE_URL", "").rstrip("/")
MEDIA_DIR = Path(UPLOAD_DIR) / "rich"
MAIL_INLINE_BYTES = positive_int("MAIL_INLINE_KIB", 128) * 1024
MAIL_BATCH_BYTES = positive_int("MAIL_BATCH_MIB", 12) * 1024 * 1024
