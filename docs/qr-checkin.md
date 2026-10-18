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

扫码签到数据使用独立的 SQLite 文件 `backend/data/qr_checkin.db`，不修改主库 `data.db` 的表结构。应用启动时会在该独立文件中自动创建 `checkin_tasks` 与 `checkin_records` 两张表，因此线上主库的 schema 校验不会受到影响，也不需要手工执行建表 SQL。

## 使用说明

管理员：登录后进入管理端菜单「扫码签到」，填写名称与有效时长，选择静态/动态二维码；点击「二维码」展示，动态二维码按所选间隔自动刷新并显示倒计时。点击「名单」查看实时状态并手动补签/请假，点击「导出」下载 Excel。

学生：登录后进入「扫码签到」，点击「开启摄像头」并对准二维码，识别后自动提交当前学号与设备指纹，页面弹窗显示签到结果。

默认本地测试账号：`admin / 123456`、`stu1 / 123456`、`stu2 / 123456`。

## 性能优化说明

- `current_code`、`student_id`、`device_id` 均建立索引，扫码校验为单次索引查询。
- `(task_id, student_id)` 与 `(task_id, device_id)` 唯一约束在数据库层兜底防重复提交，避免竞态重复写入。
- 动态二维码刷新直接更新 `current_code`，后端按 `code_updated_at` 校验动态码有效期，旧码超时即失效，保证 <2 秒响应。

## 安全说明

- 响应头 `Permissions-Policy` 已允许本站同源摄像头 `camera=(self)`，麦克风和定位保持禁用。
- 动态二维码的有效期由后端强制校验（`refresh_seconds + 1 秒网络余量`），不依赖管理页是否持续打开。
- 设备标识是前端生成的最佳努力防重复手段，用于阻止同一浏览器重复提交；Web 环境无法可靠证明物理设备身份，不能作为强安全边界。
- Excel 导出时所有用户输入（姓名、学号、设备标识等）都强制按文本写入，防止公式注入。
- 删除学生时会先做主库约束检查，再清理其签到记录；任务作者改用不会与真实用户 ID 冲突的哨兵值，避免主库 ID 复用后旧记录错挂到新账号，被删除作者的任务显示为「已删除用户」。
- 补签前会在主库校验目标学生存在且角色为学生，避免写入无效记录。
- 部署预检容器以只读方式挂载数据目录时，独立签到库会跳过建表，只做健康检查；正式容器可写后会正常建表。

## 移动端与 HTTPS

前端扫码页在路由切换、组件卸载或页面进入后台时自动关闭摄像头，适配 iPhone Safari 权限弹窗。Capacitor 安卓打包脚本 `client/scripts/prepare-mobile.mjs` 已自动注入 `android.permission.CAMERA` 权限。生产环境需保持 HTTPS，否则手机浏览器无法调用摄像头。
