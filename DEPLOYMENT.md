# 部署与资源配置

## 2.2.0 登录、外观和 HTTPS

正式入口为 `https://8.163.67.49:8000`。系统管理员在「登录页外观」管理最多 6 张公开轮播图，在「用户管理」生成密码重置验证码。照片、配置、验证码摘要及会话撤销记录保存在 `DATA_DIR`，需纳入备份；数据库结构保持不变。验证码只在生成时返回管理员，10 分钟有效、5 次错误后作废；新验证码替换旧码，成功重置后旧会话及用户下载票据失效。

「保存密码」使用浏览器密码管理器及 `autocomplete`，支持 Credential Management API 的 HTTPS 浏览器还可调用其保存接口；是否允许保存由浏览器及用户设置决定。应用只记住账号选项，不明文保存密码。开发者工具仍能查看本机提交的表单数据，这是浏览器正常行为；HTTPS 保护传输，不能隐藏使用者自己的网络面板。

TLS 代理使用单进程 Nginx Docker 容器（0.15 CPU / 48 MiB），业务容器绑定 `127.0.0.1:18000`，候选容器使用 `18001`。Nginx 在 8000 提供 TLS，80 提供 ACME 验证和 HTTPS 跳转，普通 HTTP 访问 8000 也跳转 HTTPS。不依赖公网 443，云安全组需放行 80/8000。关闭代理缓冲，继续使用应用的下载总限速、并发限制和 Range。

服务器 `/root/class-system-tls` 包含私密证书、ACME 配置、固定镜像摘要的 Compose 配置和续期脚本，不进入 Git。首次签发使用 Certbot 5.8.0 的 `certonly --standalone --ip-address 8.163.67.49 --required-profile shortlived`，需接受 CA 条款并挂载同一配置目录。证书有效期约 6 天，`class-system-certificate.timer` 每六小时检查续期，使用 webroot 验证保持网站在线，成功后 reload Nginx。部署后必须验证公网证书及 `renew.sh --dry-run`，并检查 systemd 定时器与失败日志。

已签发证书的当前服务器发布流程：

```sh
python3 scripts/deploy_server.py --release /root/class-system-releases/提交号 --source /root/class-sys-app --old-container class-system --public-url https://8.163.67.49:8000 --backend-port 18000 --candidate-port 18001
# 宿主机防火墙允许 8000/tcp；Docker 镜像预先下载。
NGINX_IMAGE=public.ecr.aws/docker/library/nginx:stable-alpine python3 scripts/configure_tls.py --port 8000 --backend-port 18000
/root/class-system-tls/renew.sh --dry-run
```

`configure_tls.py` 读取已有证书并配置代理和续期定时器。若需回滚到旧版 HTTP 部署，先停止 `class-system-https` 释放 8000，再执行该次发布的 `rollback.sh`，避免端口冲突。证书续期失败应检查 `journalctl -u class-system-certificate.service` 和云安全组 80 端口，不能跳过证书验证。

系统保持 Vue 3、FastAPI、SQLAlchemy 和 SQLite。Docker 构建时打包 Vue 前端，运行单个 Uvicorn worker；应用容器限制为 1.5 CPU、512 MiB RAM。剩余资源留给宿主机和可选的 NapCat 服务。默认面向 50 人的小班使用。

## 避免更新后仍显示旧页面

不能把旧后端目录整体挂载到 `/app`，否则会覆盖镜像中的代码与新前端。只挂载服务器已有数据库所在目录、上传目录、私密配置和磁盘临时目录。数据库与 `.session-secret` 使用服务器原文件，禁止把开发数据库打包上传。

每个构建生成公开的 `build-info.json`，记录版本、Git 提交、入口 HTML 与 JS/CSS 校验值。生产镜像启动时核对所有标识和 App 清单，不匹配时启动失败。`/api/health` 同时返回后端提交和前端构建状态；侧栏显示版本和提交缩写。不存在的 JS、图标或 manifest 返回 404，避免 SPA 回退掩盖部署问题。

小服务器可先在开发机运行前端构建，再使用预构建目标：

```sh
# 提交源码后重新构建，构建提交必须与 HEAD 一致。
cd client && npm run build && cd ..
python scripts/package_release.py
# 将生成的发布包上传到服务器并解压，再在服务器执行：
python3 scripts/deploy_server.py --release /root/class-system-releases/提交号 --source /root/class-sys-app --old-container class_system
```

发布脚本使用 `Dockerfile` 的 `prebuilt` 目标，避免在服务器运行 Node 构建；先通过仅绑定回环端口的候选容器验证新前端和服务器只读数据库，然后停旧服务、制作最终数据库备份并切换。保留旧容器、备份、运行配置与回滚脚本，启动失败时自动恢复旧容器。服务器私密配置存于权限 600 的文件，不进入 Git 或镜像。该脚本适用于指定目录布局，其他部署先核对挂载路径。

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

新任务推荐使用“学号-姓名-序号-原文件名”，简洁方案保留学号、姓名与序号；分组方案也使用提交人姓名，避免同组多人的文件混在一起。扩展名自动保留，预览展示两份示例。已有任务保留原规则，可在编辑时切换。单个、按人和全部任务下载使用同一命名逻辑。历史记录缺少文件时，界面提示并在 ZIP 加入 `_缺失文件清单.txt`，不会删除记录或隐瞒缺失。

公开前端资源按页加载、构建时 gzip 预压缩，富文本编辑器延迟加载。私有文件不整文件缓冲。不要用其他静态服务直接公开 `uploads/`，否则会绕过权限和限速。进程内限速要求保持单 worker。

Compose 可通过 `MAX_UPLOAD_MB`、`MAX_IMPORT_MB`、`MAX_CONCURRENT_UPLOADS`、`MAX_CONCURRENT_DOWNLOADS`、`MAX_CONCURRENT_ARCHIVES`、`MAX_ARCHIVE_MB`、`MIN_FREE_DISK_MB`、`THREAD_TOKENS`、`DOWNLOAD_KIB_PER_SECOND` 调整限制。线程池默认 8。可选 NapCat 另限 0.5 CPU / 768 MiB。

数据库连接池固定为 4，请求在异步依赖入口先排队，再进入同步认证与业务函数，避免线程池被等待连接的请求占满。数据库依赖使用函数作用域，在响应发送前关闭会话；长时间 ZIP、附件和表格下载不会持续占用连接。仍保持单个 worker，50 个并发读取通过排队服务。

## 图文、邮件与 QQ

富文本复用现有 Text 字段，兼容旧纯文本。服务端清洗 HTML，仅允许本系统上传图片；图片输入最多 5 MiB、1600 万像素，转为最大 1600px WebP；普通附件最多 20 MiB，富文本目录总配额 1 GiB。

邮件带纯文本和 HTML 版本，小图片 CID 内嵌、小文件 MIME 附件；每封媒体预算 128 KiB，整批最多 12 MiB，较大媒体改用 7 天有效签名链接。邮件同时仅处理一批，约 32 KiB/s 发送。链接持有者在有效期内可下载对应媒体，请按通知范围转发。设置正确 `PUBLIC_BASE_URL`，失效后可登录系统下载。

QQ 服务可用 `docker compose --profile qq up -d`，API/WebUI 仅绑定主机回环地址。通过 SSH 隧道管理 NapCat 并设置访问令牌，系统机器人地址可填 `http://napcat:3001?access_token=...`。共享只读上传目录可发送群图片和不超过 1 MiB 的群文件；较大文件和批量私聊较大媒体使用签名链接，减少 3 Mbps 带宽下的重复传输。QQ 单次媒体调用串行执行，群文件调用允许更长的网络超时。外部机器人需配置 `QQ_ALLOWED_HOSTS` 和一致的 `QQ_UPLOAD_ROOT`；SMTP 主机使用 `SMTP_ALLOWED_HOSTS` 白名单。

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

2.2.1 的公告分类和文件任务格式分别保存在 `DATA_DIR/notice-categories.json`、`DATA_DIR/task-formats.json`，与轮播设置、密钥一起随数据目录持久化和备份。缺少这两个文件时，历史公告显示「未分类」、历史任务保留原有格式范围。此版本没有数据库迁移。

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
