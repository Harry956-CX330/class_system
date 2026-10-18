# 限时扫码签到模块

基于现有 Vue 3 + Vite + Element Plus + Pinia 前端、FastAPI + SQLAlchemy + SQLite 后端实现，与项目原有「活动签到（四位数字签到码）」相互独立，互不影响。

## 功能概览

管理员可创建限时签到任务，选择静态二维码或动态二维码（3/5/10 秒刷新）；只有管理员能生成二维码。学生用手机摄像头扫码签到，后端校验任务有效期、签到码、学生与设备是否重复签到，并写入 SQLite。

管理员名单页支持手动「设为已签到」和「请假」，未签到学生标红；可提前关闭签到、导出 Excel、删除历史记录。Excel 使用项目已有的 openpyxl 导出，缺勤行标红、请假行标黄，并区分扫码自动签到与管理员手动补签。

## 安装依赖

后端（项目虚拟环境）：

```powershell
.\.venv\Scripts\python.exe -m pip install "qrcode[pil]"
```

前端：

```powershell
cd client
..\.tools\node-v22.23.3-win-x64\npm.cmd install html5-qrcode
```

依赖已写入 `backend/requirements.txt`（`qrcode==8.2`）和 `client/package.json`。

## 数据库

本地开发已通过 `scripts/init_dev_db.py` 创建 `checkin_tasks` 与 `checkin_records` 两张表。生产环境启动前需执行：

```powershell
.\.venv\Scripts\python.exe -m sqlite3 backend\data\data.db < backend\sql\qr_checkin.sql
```

建表语句见 `backend/sql/qr_checkin.sql`。

## 使用说明

管理员：登录后进入管理端菜单「扫码签到」，填写名称与有效时长，选择静态/动态二维码；点击「二维码」展示，动态二维码按所选间隔自动刷新并显示倒计时。点击「名单」查看实时状态并手动补签/请假，点击「导出」下载 Excel。

学生：登录后进入「扫码签到」，点击「开启摄像头」并对准二维码，识别后自动提交当前学号与设备指纹，页面弹窗显示签到结果。

默认本地测试账号：`admin / 123456`、`stu1 / 123456`、`stu2 / 123456`。

## 性能优化说明

- `current_code`、`student_id`、`device_id` 均建立索引，扫码校验为单次索引查询。
- `(task_id, student_id)` 与 `(task_id, device_id)` 唯一约束在数据库层兜底防代签，避免竞态重复写入。
- 动态二维码刷新直接更新 `current_code`，旧 code 无需删除即失效，保证 <2 秒响应。

## 移动端与 HTTPS

前端扫码页在路由切换、组件卸载或页面进入后台时自动关闭摄像头，适配 iPhone Safari 权限弹窗。Capacitor 安卓打包脚本 `client/scripts/prepare-mobile.mjs` 已自动注入 `android.permission.CAMERA` 权限。生产环境需保持 HTTPS，否则手机浏览器无法调用摄像头。
