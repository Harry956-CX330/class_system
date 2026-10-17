FROM node:22-alpine AS frontend
WORKDIR /client
COPY client/package.json client/package-lock.json ./
RUN npm ci
COPY client/ ./
RUN npm run build

FROM python:3.11-slim

WORKDIR /app

# 安装依赖
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制后端源码和构建后的前端静态资源
COPY backend/ .
COPY --from=frontend /client/dist/ ./static/dist/

# 确保上传目录存在
RUN mkdir -p static/uploads

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--limit-concurrency", "64", "--timeout-keep-alive", "15", "--no-access-log"]
