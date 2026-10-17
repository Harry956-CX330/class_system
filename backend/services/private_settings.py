"""Small atomic settings files; these never change the database schema."""
import json
import os
import threading
from config import DATA_DIR

settings_lock = threading.RLock()

def read_settings(name, default):
    path = DATA_DIR / name
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default

def write_settings(name, value):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    path = DATA_DIR / name
    temporary = path.with_suffix(".tmp")
    with temporary.open("w", encoding="utf-8") as stream:
        stream.write(json.dumps(value, ensure_ascii=False))
        stream.flush()
        os.fsync(stream.fileno())
    temporary.chmod(0o600)
    temporary.replace(path)
