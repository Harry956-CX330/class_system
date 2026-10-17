# 部署与资源配置

系统保持 Vue 3、FastAPI、SQLAlchemy 和 SQLite。Docker 构建时打包 Vue 前端，运行单个 Uvicorn worker；应用容器限制为 1.5 CPU、1 GiB RAM。剩余资源留给宿主机和可选的 NapCat 服务。默认面向 50 人的小班使用。

## 部署现有数据库

维护窗口停止写入并备份服务器完整 SQLite 数据库与上传目录。使用 SQLite 备份接口，或停止服务后复制数据库及已有 WAL 文件，不要在线仅复制主文件。Compose 使用根目录 `./data.db`；原服务器路径不同时调整挂载。应用只读校验表和字段，不执行 `CREATE TABLE`、`ALTER TABLE`、索引变更或账号初始化。结构不兼容时停止启动，以服务器现有完整数据库为准。

将服务器现有完整数据库备份后放在项目根目录的 `data.db`。Compose 将它直接挂载为容器内的 `/app/data/data.db`；ZIP 临时文件写入项目根目录的 `temp/`。

复制 `.env.example` 为 `.env`，设置至少 32 字节的随机 `SECRET_KEY`（例如用 `openssl rand -hex 32` 生成）。保留原密钥可兼容旧令牌，更换后需要重新登录。正式地址默认为 `http://8.163.67.49:8000`。把原 `backend/smtp_config.json`、`backend/kdocs_config.json`（如有）复制到根目录 `config/` 同名文件，QQ 配置仍保存在数据库。

Linux 容器使用 UID/GID 10001，须先准备挂载目录权限：

```sh
mkdir -p config uploads temp
test -f data.db || exit 1
sudo chown -R 10001:10001 config uploads temp
sudo chown 10001:10001 data.db
docker compose config --quiet
docker compose up -d --build app
docker compose logs --tail=100 app
curl --fail http://127.0.0.1:8000/api/health
```

`config/` 也必须可写，以便 SQLite 创建日志。Windows Docker Desktop 的权限处理不同，例如：

```powershell
$env:SECRET_KEY = '<至少32字节的随机密钥>'
docker compose up -d --build app
```

`SECRET_KEY` 保持旧密钥时，现有令牌继续有效；更换密钥会使现有用户重新登录。建议先在维护窗口设置随机密钥。

## 上传和大文件下载

单次 multipart 请求最多 100 MiB，最多同时 2 个上传；表格导入最多 5 MiB。文件分块写入磁盘。下载最多 4 路共享 280 KiB/s，给页面、接口和邮件留余量。100 MiB 独占下载约需 6 分钟，多人下载会更慢；50 人日常使用不代表 50 路大文件可同时满速。

一键下载默认生成一个完整 ZIP，不强制拆成小包；旧分批接口仍兼容。ZIP 生成并发 1，原文件合计上限 2 GiB，使用存储模式节省 CPU。`temp/` 磁盘缓存总预算 2 GiB，后续打包时清理超 2 小时旧包；正在下载的包保留。缓存支持 HTTP Range 续传。磁盘需额外容纳 ZIP 并保留至少 256 MiB；超限按任务或学生下载。不能将缓存放内存盘。

公开前端资源按页加载、构建时 gzip 预压缩，富文本编辑器延迟加载。私有文件不整文件缓冲。不要用其他静态服务直接公开 `uploads/`，否则会绕过权限和限速。进程内限速要求保持单 worker。

Compose 可通过 `MAX_UPLOAD_MB`、`MAX_IMPORT_MB`、`MAX_CONCURRENT_UPLOADS`、`MAX_CONCURRENT_DOWNLOADS`、`MAX_CONCURRENT_ARCHIVES`、`MAX_ARCHIVE_MB`、`MIN_FREE_DISK_MB`、`THREAD_TOKENS`、`DOWNLOAD_KIB_PER_SECOND` 调整限制。线程池默认 8。可选 NapCat 另限 0.5 CPU / 768 MiB。

## 图文、邮件与 QQ

富文本复用现有 Text 字段，兼容旧纯文本。服务端清洗 HTML，仅允许本系统上传图片；图片输入最多 5 MiB、1600 万像素，转为最大 1600px WebP；普通附件最多 20 MiB，富文本目录总配额 1 GiB。

邮件带纯文本和 HTML 版本，小图片 CID 内嵌、小文件 MIME 附件；每封媒体预算 128 KiB，整批最多 12 MiB，较大媒体改用 7 天有效签名链接。邮件同时仅处理一批，约 32 KiB/s 发送。链接持有者在有效期内可下载对应媒体，请按通知范围转发。设置正确 `PUBLIC_BASE_URL`，失效后可登录系统下载。

QQ 服务可用 `docker compose --profile qq up -d`，API/WebUI 仅绑定主机回环地址。通过 SSH 隧道管理 NapCat 并设置访问令牌，系统机器人地址可填 `http://napcat:3001?access_token=...`。共享只读上传目录可发送群图片/群文件，批量私聊较大媒体使用签名链接。外部机器人需配置 `QQ_ALLOWED_HOSTS` 和一致的 `QQ_UPLOAD_ROOT`；SMTP 主机使用 `SMTP_ALLOWED_HOSTS` 白名单。

## HTTPS 与反向代理

当前 HTTP 地址无法保护账号与会话的传输，建议绑定域名和 TLS 证书，再更新 `PUBLIC_BASE_URL`、`CORS_ORIGINS`、Android 的 `MOBILE_SERVER_URL`。完整 PWA 需要安全上下文，iOS 签名条件见 [MOBILE.md](MOBILE.md)。Nginx 示例（TLS 证书按实际域名设置）：

```nginx
location / {
    proxy_pass http://127.0.0.1:8000;
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header X-Forwarded-For $remote_addr;
    client_max_body_size 101m;
    proxy_request_buffering off;
    proxy_buffering off;
    proxy_read_timeout 7200s;
    proxy_send_timeout 7200s;
}
```

应用默认只信任 `127.0.0.1` 的转发头。Docker 桥接代理需在 Uvicorn 可信代理配置中加入实际地址，不能无条件信任公网来源。代理上线后可将 app 端口收紧为 `127.0.0.1:8000:8000`。

## 验证

健康检查端点为 `/api/health`。部署时查看容器日志；如果启动报告 `Database schema is incompatible`，先核对 `DATABASE_URL` 和服务器备份，不要对线上数据库执行未经审核的迁移。

```sh
pip install -r backend/requirements-dev.txt
python -m unittest discover -s backend/tests -v
pip-audit -r backend/requirements.txt --progress-spinner off
cd client
npm ci --legacy-peer-deps
npm audit --omit=dev --registry=https://registry.npmjs.org
npm run build
```

浏览器验证先在另一终端运行 `python backend/tests/preview_app.py`，再执行 `cd client && npm run test:e2e`，需要 Microsoft Edge。测试只使用临时数据库，不发送真实通知。自动测试不能替代实际服务器、50 人负载与真实 SMTP/QQ 联调；上线前用测试收件人核对图文、附件及断点下载。
