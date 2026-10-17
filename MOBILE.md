# Android、iPhone 与 iPad

应用显示名称为 **sk2441班务**，使用白底班徽图标。Android 常规图标、自适应图标、PWA 与 iOS 工程图标由版本库中的资源统一生成。

同一 Vue 前端提供 PWA 和 Capacitor 包装工程，连接现有 FastAPI 服务，无需新增数据库字段。

## Android APK

**Android APK** 工作流仅支持手动触发；2.2.1 不构建或更新安卓包。在 GitHub Actions 手动运行成功后的 Artifacts 中下载 `class-system-android-debug`，解压得到 `app-debug.apk` 后传到手机安装。已有 2.2.0 包默认连接 `https://8.163.67.49:8000`，禁止明文请求。文件任务和资料的下载使用限时票据交给系统浏览器，避免 WebView 缓冲大文件；网页版持续可用。

全面屏适配同时使用 `viewport-fit=cover`、Web 安全区和 Capacitor 8 的 `SystemBars.insetsHandling=css`。旧版 APK 需要更新以获得完整原生设置；网页更新不能替换 APK 的原生配置。浏览器测试模拟顶部安全区并验证实际触摸滚动，刘海屏、横屏、手势导航及软键盘仍需在真实设备验证。

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

 iPhone/iPad 用 Safari 打开 `https://8.163.67.49:8000`，通过分享菜单添加到主屏幕。PWA 缓存仅包含公开构建资源，接口和私人附件不会离线缓存，业务操作仍需联网。

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
