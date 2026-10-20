# 班级管理系统

## 2.2.1 使用入口

。支持学号 / 姓名 / 原账号登录、管理员验证码重置密码、浏览器密码保存、蓝色浅深主题与跟随系统外观。管理员和班干可在管理端「登录页外观」更换班级轮播照片。公告支持分类和多图，文件任务支持限制上传格式。框架和现有数据库结构保持不变，详细部署及证书续期见 `DEPLOYMENT.md`，APK 与 iOS 说明见 `MOBILE.md`。本次仅更新网站，Android 工作流改为手动触发。

基于 Vue 3、FastAPI、SQLAlchemy 和 SQLite 的班级事务管理系统。当前版本保留已有业务 API 和数据库结构，适用于约 50 名用户的小型部署。

版本 2 增加三端自适应界面、富文本与图文附件通知、问卷校验、完整 ZIP 下载及 3 Mbps 带宽下的总限速。见 [更新记录](CHANGELOG.md)、[部署说明](DEPLOYMENT.md) 和 [Android/iOS 安装说明](MOBILE.md)。Android APK 可在 Actions 的 Android APK 工作流成功后下载。

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

## AI 班务助手

2.4.0 新增多个 QQ 群、按群/个人选择提醒目标，以及服务器状态、异常请求防护和向全体班干发送邮件/QQ 安全告警。使用方式见 [提醒与防护指南](docs/notifications-and-security.md)。本次不修改数据库结构，不更新安卓包。

2.3.0 新增 GLM-4.6V-Flash 操作问答、公告解读和公告图片解题。管理员在「AI 服务设置」配置密钥并测试连接后启用；默认并发 1，支持个人与全站限流，不改数据库结构。使用步骤、图片限制和部署说明见 [AI 使用指南](docs/ai-assistant.md)。

## 本地开发

后端使用 Python 3.11+，安装 `backend/requirements.txt` 并设置指向完整数据库副本的 `DATABASE_URL`，从 `backend/` 目录以 `uvicorn main:app` 运行。前端使用 Node.js 22+，在 `client/` 目录执行 `npm ci --legacy-peer-deps` 和 `npm run dev`。Vite 将 `/api` 和 `/static` 代理至本地 8000 端口。

应用启动时只读校验数据库所需结构；不会自动创建或修改表。请使用与当前代码兼容的数据库。
