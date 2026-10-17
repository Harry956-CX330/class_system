import { readFile, writeFile, mkdir, access } from 'node:fs/promises'
import { spawnSync } from 'node:child_process'
const platform = process.argv[2]
if (!['android','ios'].includes(platform)) throw new Error('Choose android or ios')
if (Number(process.versions.node.split('.')[0]) < 22) throw new Error('Node 22+ is required')
if (platform === 'ios' && process.platform !== 'darwin') throw new Error('iOS builds require macOS + Xcode')
const configured = JSON.parse(await readFile('capacitor.config.json','utf8'))
const url = new URL(process.env.MOBILE_SERVER_URL || configured.server.url)
if (!['http:','https:'].includes(url.protocol) || url.username || url.password) throw new Error('Invalid MOBILE_SERVER_URL')
if (platform === 'ios' && url.protocol !== 'https:') throw new Error('iOS archive requires an HTTPS MOBILE_SERVER_URL.')
configured.server.url = url.origin
configured.server.cleartext = url.protocol === 'http:'
await writeFile('capacitor.config.json', JSON.stringify(configured,null,2)+'\n')
function cap(...args) { const r=spawnSync(process.execPath,['node_modules/@capacitor/cli/bin/capacitor',...args],{stdio:'inherit'}); if(r.status)process.exit(r.status) }
try { await access(platform) } catch { cap('add',platform) }
cap('sync',platform)
if (platform === 'android') {
  const dir='android/app/src/main/res/xml'
  await mkdir(dir,{recursive:true})
  await writeFile(dir+'/network_security_config.xml',`<?xml version="1.0" encoding="utf-8"?><network-security-config><base-config cleartextTrafficPermitted="false"/><domain-config cleartextTrafficPermitted="${url.protocol==='http:'}"><domain includeSubdomains="false">${url.hostname}</domain></domain-config></network-security-config>`)
  const path='android/app/src/main/AndroidManifest.xml'
  let manifest=await readFile(path,'utf8')
  manifest=manifest.replace(/android:usesCleartextTraffic="[^"]*"/g,'').replace(/android:networkSecurityConfig="[^"]*"/g,'')
  manifest=manifest.replace('<application','<application android:networkSecurityConfig="@xml/network_security_config" android:usesCleartextTraffic="false"')
  await writeFile(path,manifest)
  // Stable debug key may be supplied by CI for repeat installs; never add a keystore to Git.
  console.log('Android project ready. Build: cd android && ./gradlew assembleDebug')
} else {
  if (url.protocol !== 'https:') throw new Error('iOS archive requires an HTTPS MOBILE_SERVER_URL; use Safari home-screen shortcut until HTTPS is configured.')
  console.log('iOS project ready. Open in Xcode, configure your Apple Team and archive/sign.')
}
