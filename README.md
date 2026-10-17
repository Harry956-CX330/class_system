# 班级管理系统

基于 Vue 3、FastAPI、SQLAlchemy 和 SQLite 的班级事务管理系统。当前版本保留已有业务 API 和数据库结构，适用于约 50 名用户的小型部署。

## 部署

服务器需预先提供完整的 SQLite 数据库文件 `data.db`。数据库、上传内容、邮件配置和密钥均作为服务器运行数据，不存放在 Git 仓库。首次部署前请把现有数据库放在项目根目录，并备份数据库和上传目录。

配置强随机 `SECRET_KEY` 后构建并启动：

```sh
export SECRET_KEY="$(openssl rand -hex 32)"
docker compose up -d --build app
```

Windows PowerShell：

```powershell
$env:SECRET_KEY = '<随机密钥>'
docker compose up -d --build app
```

健康检查：`GET /api/health`。部署、资源限额、上传下载约束和数据库兼容行为详见 [DEPLOYMENT.md](DEPLOYMENT.md)。

## 本地开发

后端从 `backend/` 目录以 `uvicorn main:app` 运行；前端在 `client/` 目录执行 `npm ci` 和 `npm run dev`。Vite 开发服务器将 `/api` 和 `/static` 代理至本地 8000 端口。

应用启动时只读校验数据库所需结构；不会自动创建或修改表。请使用与当前代码兼容的数据库。
