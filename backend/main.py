from contextlib import asynccontextmanager
import anyio.to_thread
from fastapi import FastAPI, HTTPException
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from config import CORS_ORIGINS, FRONTEND_DIST, THREAD_TOKENS, UPLOAD_DIR, prepare_directories
from database import engine, validate_schema
from middleware import ResourceLimitsMiddleware
from routers import users, notices, settings, grades, certificates, activities, groups, social_practices, dashboard, file_tasks, surveys, meetings, resources, textbooks, qq


@asynccontextmanager
async def lifespan(app):
    prepare_directories()
    anyio.to_thread.current_default_thread_limiter().total_tokens = THREAD_TOKENS
    validate_schema()
    yield
    engine.dispose()


prepare_directories()
app = FastAPI(title="数科2441班数据管理系统", version="1.6", lifespan=lifespan)
app.add_middleware(ResourceLimitsMiddleware)
app.add_middleware(ProxyHeadersMiddleware, trusted_hosts=["127.0.0.1"])
app.add_middleware(CORSMiddleware, allow_origins=CORS_ORIGINS, allow_credentials=True,
                   allow_methods=["*"], allow_headers=["*"],
                   expose_headers=["Content-Disposition", "Accept-Ranges", "Content-Range", "Retry-After"])
for module in (users, notices, settings, grades, certificates, activities, groups, social_practices,
               dashboard, file_tasks, surveys, meetings, resources, textbooks, qq):
    app.include_router(module.router)


@app.get("/api/health", include_in_schema=False)
def health():
    from sqlalchemy import text
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
    return {"status": "ok"}


app.mount("/static", StaticFiles(directory=UPLOAD_DIR), name="static")
if (FRONTEND_DIST / "assets").is_dir():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="frontend_assets")


@app.get("/{full_path:path}", include_in_schema=False)
def serve_spa(full_path: str):
    if full_path == "api" or full_path.startswith("api/"):
        raise HTTPException(404, "接口不存在")
    root = FRONTEND_DIST.resolve()
    path = (root / full_path).resolve()
    if not path.is_relative_to(root):
        raise HTTPException(404, "文件不存在")
    if path.is_file():
        return FileResponse(path)
    index = root / "index.html"
    if index.is_file():
        return FileResponse(index, headers={"Cache-Control": "no-cache"})
    raise HTTPException(404, "前端尚未构建")
