# 部署与资源配置

系统保持 Vue 3、FastAPI、SQLAlchemy 和 SQLite。Docker 构建时打包 Vue 前端，运行单个 Uvicorn worker；应用容器限制为 1.5 CPU、1 GiB RAM。剩余资源留给宿主机和可选的 NapCat 服务。默认面向 50 人的小班使用。

## 部署现有数据库

部署前备份服务器当前 SQLite 数据库，并确认 `DATABASE_URL` 指向该完整数据库。Compose 默认使用 `./data/data.db`；原服务器的数据库在其他路径时，用环境变量覆盖。应用启动只读校验表和字段，不执行 `CREATE TABLE`、`ALTER TABLE`、索引变更或管理员账号初始化。结构不符合当前版本时，应用会停止启动并报告缺少的字段，现有数据库不会被自动修改。

将服务器现有完整数据库备份后放在项目根目录的 `data.db`。Compose 将它直接挂载为容器内的 `/app/data/data.db`；ZIP 临时文件写入项目根目录的 `temp/`。

例：

```powershell
$env:SECRET_KEY = '<至少32字节的随机密钥>'
docker compose up -d --build app
```

`SECRET_KEY` 保持旧密钥时，现有令牌继续有效；更换密钥会使现有用户重新登录。建议先在维护窗口设置随机密钥。

## 上传和大文件下载

单次 multipart 请求默认为最多 100 MiB，最多同时接收 2 个上传。用户或成绩表格导入最多 5 MiB。上传按 256 KiB 分块写入持久化上传卷。大文件下载通过文件响应从磁盘传输，支持 HTTP Range 请求；ZIP 每批默认 50 MiB，同一时间仅生成一个 ZIP。ZIP 临时文件放在 `./data/tmp`，默认最多打包 2 GiB，且要求目标卷额外保留至少 256 MiB 空闲空间。请保证 `./data` 卷有足够空间，并配置反向代理上传限制至少 101 MiB、读取超时足以覆盖慢速大文件传输。应用最多接受 8 个并发下载。

Compose 中可通过 `MAX_UPLOAD_MB`、`MAX_IMPORT_MB`、`MAX_CONCURRENT_UPLOADS`、`MAX_CONCURRENT_DOWNLOADS`、`MAX_CONCURRENT_ARCHIVES`、`MAX_ARCHIVE_MB`、`MIN_FREE_DISK_MB`、`THREAD_TOKENS` 调整限制。修改容器 CPU 或内存限额前，请同时考虑宿主机和 NapCat 的资源需求。

## 验证

健康检查端点为 `/api/health`。部署时查看容器日志；如果启动报告 `Database schema is incompatible`，先核对 `DATABASE_URL` 和服务器备份，不要对线上数据库执行未经审核的迁移。
