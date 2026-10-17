# Android、iPhone 与 iPad

同一 Vue 前端提供 PWA 和 Capacitor 包装工程，连接现有 FastAPI 服务，无需新增数据库字段。

## Android APK

推送 main 的客户端更新会触发 **Android APK** 工作流。在 GitHub Actions 成功运行的 Artifacts 中下载 `class-system-android-debug`，解压得到 `app-debug.apk` 后传到手机安装。默认连接 `http://8.163.67.49:8000`，HTTP 明文仅放行这一主机。大文件建议使用手机浏览器下载；网页版持续可用。

产物为调试签名包。CI 临时调试密钥可能变化，更新安装时可能需要卸载旧包。正式分发应使用固定私有 release keystore，通过 Secrets 或本地安全存储注入，勿提交密钥。修改服务器地址后需重新构建。

本地需要 Node.js 22+、JDK 21 和匹配生成工程版本的 Android SDK（见 `android/variables.gradle`）：

```sh
cd client
npm ci --legacy-peer-deps
npm run build
# 可选：export MOBILE_SERVER_URL=https://class.example.com
npm run mobile:android
cd android
./gradlew assembleDebug
```

Windows 使用 `gradlew.bat assembleDebug`。产物位于 `client/android/app/build/outputs/apk/debug/app-debug.apk`。原生工程由脚本生成并忽略提交。

## iOS 安装

HTTPS 部署后，iPhone/iPad 用 Safari 打开并通过分享菜单添加到主屏幕。PWA 缓存仅包含公开构建资源，接口和私人附件不会离线缓存，业务操作仍需联网。当前 HTTP 地址无法启用完整 PWA 安全能力。

如需 `.ipa`，需要 macOS、Xcode、Apple Developer 签名及 HTTPS 服务地址：

```sh
cd client
npm ci --legacy-peer-deps
npm run build
export MOBILE_SERVER_URL=https://class.example.com
npm run mobile:ios
npx cap open ios
```

在 Xcode 配置唯一 Bundle ID、签名 Team、证书及分发渠道，Archive 后导出。Windows 不能完成 Apple 签名，仓库不包含已签名 IPA；生成包装工程不意味着通过商店审核。
