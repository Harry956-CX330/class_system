FROM node:22-alpine AS frontend
WORKDIR /client
COPY client/package.json client/package-lock.json ./
RUN npm ci --legacy-peer-deps
COPY client/ ./
ARG APP_REVISION=unknown
ENV APP_REVISION=$APP_REVISION
RUN npm run build

FROM python:3.11-slim AS runtime
ENV REQUIRE_FRONTEND_BUILD=1 PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1

WORKDIR /app

# 安装依赖
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制后端源码和构建后的前端静态资源
COPY backend/ .

# 确保上传目录存在
RUN groupadd --gid 10001 classapp && useradd --uid 10001 --gid classapp --no-create-home classapp \
    && mkdir -p static/uploads data archive-tmp \
    && chown -R classapp:classapp /app

ARG APP_REVISION=unknown
ENV APP_REVISION=$APP_REVISION
LABEL org.opencontainers.image.revision=$APP_REVISION
USER classapp

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health',timeout=4)"

CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--limit-concurrency", "64", "--timeout-keep-alive", "15", "--no-access-log"]

# Use the locally verified frontend bundle on small servers, avoiding a Node build there.
FROM runtime AS prebuilt
COPY --chown=classapp:classapp frontend-dist/ ./static/dist/

FROM runtime AS production
COPY --chown=classapp:classapp --from=frontend /client/dist/ ./static/dist/
