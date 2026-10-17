from contextlib import asynccontextmanager
import os
import anyio.to_thread
from fastapi import FastAPI, HTTPException
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from services.staticfiles import CompressedStaticFiles
from services.buildinfo import inspect_build
from config import CORS_ORIGINS, FRONTEND_DIST, THREAD_TOKENS, UPLOAD_DIR, prepare_directories
from database import engine, validate_schema
from middleware import ResourceLimitsMiddleware
from security import SecurityMiddleware
from routers.transfers import TransferTicketMiddleware
from routers import media, transfers, branding, password_reset
from routers import users, notices, settings, grades, certificates, activities, groups, social_practices, dashboard, file_tasks, surveys, meetings, resources, textbooks, qq


@asynccontextmanager
async def lifespan(app):
    prepare_directories()
    anyio.to_thread.current_default_thread_limiter().total_tokens = THREAD_TOKENS
    validate_schema()
    app.state.frontend_build = inspect_build(FRONTEND_DIST)
    if os.environ.get('REQUIRE_FRONTEND_BUILD') == '1' and not app.state.frontend_build['ready']:
        raise RuntimeError('Frontend build validation failed: ' + app.state.frontend_build.get('error', 'unknown'))
    yield
    engine.dispose()


prepare_directories()
app = FastAPI(title="数科2441班数据管理系统", version="2.0", lifespan=lifespan)
app.add_middleware(ResourceLimitsMiddleware)
app.add_middleware(TransferTicketMiddleware)
app.add_middleware(SecurityMiddleware)
app.add_middleware(ProxyHeadersMiddleware, trusted_hosts=os.environ.get("TRUSTED_PROXY_HOSTS", "127.0.0.1").split(","))
app.add_middleware(CORSMiddleware, allow_origins=CORS_ORIGINS, allow_credentials=True,
                   allow_methods=["*"], allow_headers=["*"],
                   expose_headers=["Content-Disposition", "Accept-Ranges", "Content-Range", "Retry-After"])
for module in (users, notices, settings, grades, certificates, activities, groups, social_practices,
               dashboard, file_tasks, surveys, meetings, resources, textbooks, qq, media, transfers, branding, password_reset):
    app.include_router(module.router)

# Validation failures must never echo passwords or verification codes.
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
@app.exception_handler(RequestValidationError)
async def validation_error(request, error):
    return JSONResponse(status_code=422, content={"detail":"输入格式不正确，请检查必填项和内容长度", "errors":[{"loc":list(item["loc"]),"type":item["type"]} for item in error.errors()]})


@app.get("/api/health", include_in_schema=False)
def health():
    from sqlalchemy import text
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
    return {"status": "ok", "revision": os.environ.get('APP_REVISION', 'unknown'),
            "frontend": getattr(app.state, 'frontend_build', {"ready": False})}



if (FRONTEND_DIST / "assets").is_dir():
    app.mount("/assets", CompressedStaticFiles(directory=FRONTEND_DIST / "assets"), name="frontend_assets")


@app.get("/{full_path:path}", include_in_schema=False)
def serve_spa(full_path: str):
    if full_path == "api" or full_path.startswith("api/"):
        raise HTTPException(404, "接口不存在")
    root = FRONTEND_DIST.resolve()
    path = (root / full_path).resolve()
    if not path.is_relative_to(root):
        raise HTTPException(404, "文件不存在")
    if path.is_file():
        return FileResponse(path, headers={"Cache-Control": "no-cache"},
                            media_type="application/manifest+json" if path.suffix == '.webmanifest' else None)
    if path.suffix or full_path.startswith(('assets/', 'icons/')):
        raise HTTPException(404, "文件不存在")
    index = root / "index.html"
    if index.is_file():
        return FileResponse(index, headers={"Cache-Control": "no-cache"})
    raise HTTPException(404, "前端尚未构建")
