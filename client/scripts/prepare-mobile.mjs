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
  if (!manifest.includes('xmlns:tools=')) manifest=manifest.replace('<manifest','<manifest xmlns:tools="http://schemas.android.com/tools"')
  manifest=manifest.replace(/android:usesCleartextTraffic="[^"]*"/g,'').replace(/android:networkSecurityConfig="[^"]*"/g,'')
  manifest=manifest.replace(/tools:replace="[^"]*"/g,'')
  manifest=manifest.replace('<application','<application tools:replace="android:usesCleartextTraffic" android:networkSecurityConfig="@xml/network_security_config" android:usesCleartextTraffic="false"')
  manifest=manifest.replace('android:allowBackup="true"','android:allowBackup="false"')
  await writeFile(path,manifest)
  const javaPath=`android/app/src/main/java/${configured.appId.replaceAll('.','/')}/MainActivity.java`
  await writeFile(javaPath,`package ${configured.appId};
import android.os.Bundle;
import android.content.Intent;
import android.content.ActivityNotFoundException;
import android.net.Uri;
import com.getcapacitor.BridgeActivity;
import com.getcapacitor.Plugin;
import com.getcapacitor.annotation.CapacitorPlugin;
public class MainActivity extends BridgeActivity {
  @Override public void onCreate(Bundle savedInstanceState) {
    registerPlugin(SystemDownloads.class);
    super.onCreate(savedInstanceState);
  }
  @CapacitorPlugin(name="SystemDownloads")
  public static class SystemDownloads extends Plugin {
    @Override public Boolean shouldOverrideLoad(Uri uri) {
      Uri server = Uri.parse(${JSON.stringify(url.origin)});
      if (server.getScheme().equals(uri.getScheme()) && server.getHost().equals(uri.getHost())
          && server.getPort() == uri.getPort() && uri.getPath() != null
          && uri.getPath().startsWith("/api/transfers/open/")) {
        try { getActivity().startActivity(new Intent(Intent.ACTION_VIEW, uri)); }
        catch (ActivityNotFoundException error) {
          android.widget.Toast.makeText(getContext(), "请安装浏览器后下载", android.widget.Toast.LENGTH_LONG).show();
        }
        return true;
      }
      return null;
    }
  }
}
`)
  // Stable debug key may be supplied by CI for repeat installs; never add a keystore to Git.
  console.log('Android project ready. Build: cd android && ./gradlew assembleDebug')
} else {
  if (url.protocol !== 'https:') throw new Error('iOS archive requires an HTTPS MOBILE_SERVER_URL; use Safari home-screen shortcut until HTTPS is configured.')
  console.log('iOS project ready. Open in Xcode, configure your Apple Team and archive/sign.')
}
