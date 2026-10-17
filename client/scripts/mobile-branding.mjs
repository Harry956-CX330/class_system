import { readFile, writeFile, mkdir, copyFile } from 'node:fs/promises'

const xml = value => value.replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;')

export async function applyMobileBranding(platform, configured) {
  const name = xml(configured.appName)
  if (platform === 'android') {
    const res = 'android/app/src/main/res'
    for (const density of ['mdpi', 'hdpi', 'xhdpi', 'xxhdpi', 'xxxhdpi']) {
      const folder = `mipmap-${density}`
      await mkdir(`${res}/${folder}`, { recursive: true })
      for (const file of ['ic_launcher.png', 'ic_launcher_foreground.png']) {
        await copyFile(`mobile-assets/android/${folder}/${file}`, `${res}/${folder}/${file}`)
      }
      await copyFile(`${res}/${folder}/ic_launcher.png`, `${res}/${folder}/ic_launcher_round.png`)
    }
    await mkdir(`${res}/mipmap-anydpi-v26`, { recursive: true })
    const adaptive = '<?xml version="1.0" encoding="utf-8"?><adaptive-icon xmlns:android="http://schemas.android.com/apk/res/android"><background android:drawable="@color/class_icon_background"/><foreground android:drawable="@mipmap/ic_launcher_foreground"/></adaptive-icon>\n'
    for (const file of ['ic_launcher.xml', 'ic_launcher_round.xml']) await writeFile(`${res}/mipmap-anydpi-v26/${file}`, adaptive)
    await writeFile(`${res}/values/class_branding.xml`, '<?xml version="1.0" encoding="utf-8"?><resources><color name="class_icon_background">#FFFFFF</color></resources>\n')
    const strings = `${res}/values/strings.xml`
    let content = await readFile(strings, 'utf8')
    for (const key of ['app_name', 'title_activity_main']) {
      content = content.replace(new RegExp(`(<string name="${key}">)[^<]*(</string>)`), (_, open, close) => open + name + close)
    }
    await writeFile(strings, content)
    const { version } = JSON.parse(await readFile('package.json', 'utf8'))
    const [major, minor, patch] = version.split('.').map(Number)
    const gradle = 'android/app/build.gradle'
    content = (await readFile(gradle, 'utf8'))
      .replace(/versionCode \d+/, `versionCode ${major * 10000 + minor * 100 + patch}`)
      .replace(/versionName "[^"]*"/, `versionName "${version}"`)
    await writeFile(gradle, content)
  } else {
    const folder = 'ios/App/App/Assets.xcassets/AppIcon.appiconset'
    await mkdir(folder, { recursive: true })
    await copyFile('public/icons/app-icon-1024.png', `${folder}/AppIcon-512@2x.png`)
    await writeFile(`${folder}/Contents.json`, JSON.stringify({ images: [{ filename: 'AppIcon-512@2x.png', idiom: 'universal', platform: 'ios', size: '1024x1024' }], info: { author: 'xcode', version: 1 } }, null, 2) + '\n')
    const plist = 'ios/App/App/Info.plist'
    const content = (await readFile(plist, 'utf8')).replace(/(<key>CFBundleDisplayName<\/key>\s*<string>)[^<]*(<\/string>)/, (_, open, close) => open + name + close)
    await writeFile(plist, content)
  }
}
