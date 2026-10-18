<template>
  <div class="qr-checkin-page">
    <div class="page-card">
      <div class="page-head">
        <h2>扫码签到</h2>
        <p>对准管理员展示的当前二维码，完成本次签到</p>
      </div>
      <div class="scanner-wrap">
        <div id="qr-reader" ref="reader" class="qr-reader"></div>
        <div v-if="!scanning" class="scanner-mask">
          <el-button type="primary" :loading="starting" :disabled="processing" @click="startScan">
            {{ starting ? '正在开启摄像头…' : '开启摄像头' }}
          </el-button>
        </div>
      </div>
      <div class="camera-controls">
        <el-select v-if="cameras.length > 1" v-model="selectedCamera" placeholder="自动选择（优先后置）" aria-label="选择摄像头" :disabled="starting || processing" @change="switchCamera">
          <el-option label="自动选择（优先后置）" value="" />
          <el-option v-for="(item, index) in cameras" :key="item.deviceId" :label="item.label || `摄像头 ${index + 1}`" :value="item.deviceId" />
        </el-select>
        <el-button v-if="scanning || starting" :disabled="starting" @click="stopScan">关闭摄像头</el-button>
      </div>
      <el-alert v-if="errorMessage" :title="errorMessage" type="warning" :closable="false" show-icon class="camera-error" />
      <p v-if="starting" class="permission-hint" role="status">请在弹出的提示中允许使用相机。若没有提示，请检查浏览器的网站权限。</p>
      <div class="tips">
        <p>请允许浏览器使用相机权限，页面需通过 HTTPS 打开。</p>
        <p>动态二维码会定期刷新，请扫管理员当前展示的画面。</p>
        <p>切换页面或签到识别完成后，相机会自动关闭。</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { ElMessageBox } from 'element-plus'
import { Html5Qrcode } from 'html5-qrcode'
import api from '../api'
import { getDeviceId } from '../utils/device'
import { cameraErrorMessage, createQrCamera } from '../utils/qrCamera'

const reader = ref(null)
const scanning = ref(false)
const starting = ref(false)
const processing = ref(false)
const errorMessage = ref('')
const cameras = ref([])
const selectedCamera = ref('')
let camera = null
let disposed = false

async function handleCode(code) {
  if (processing.value || disposed) return
  processing.value = true
  await stopScan()
  let title, message, type
  try {
    const res = await api.post('/api/qr-checkin/verify', { code, device_id: getDeviceId() })
    title = '签到成功'; message = `你已在「${res.data.task_name}」签到成功`; type = 'success'
  } catch (error) {
    title = '签到失败'; message = error.response?.data?.detail || '签到失败，请稍后重试'; type = 'error'
  }
  if (!disposed) {
    try { await ElMessageBox.alert(message, title, { type, confirmButtonText: '知道了', showClose: false }) } catch {}
  }
  processing.value = false
}

async function startScan() {
  if (starting.value || scanning.value || processing.value || disposed || document.hidden) return
  errorMessage.value = ''
  if (!window.isSecureContext) {
    errorMessage.value = '当前页面不在安全连接中，无法使用相机。请通过有效证书的 HTTPS 地址打开签到页面。'
    return
  }
  if (!navigator.mediaDevices?.getUserMedia) {
    errorMessage.value = '当前浏览器未提供相机接口。请在手机系统浏览器（如 Safari、Chrome、Edge）中打开本页，并允许相机权限。'
    return
  }
  starting.value = true
  try {
    const active = await camera.start(selectedCamera.value)
    scanning.value = active && !disposed && !document.hidden
    if (!scanning.value) return
    try {
      const devices = await navigator.mediaDevices.enumerateDevices()
      if (!disposed) cameras.value = devices.filter(device => device.kind === 'videoinput' && device.deviceId)
    } catch {}
  } catch (error) {
    if (!disposed) errorMessage.value = cameraErrorMessage(error)
  } finally { starting.value = false }
}

async function stopScan() {
  scanning.value = false
  await camera?.stop()
}
async function switchCamera() {
  await stopScan()
  await startScan()
}
function handleVisibility() { if (document.hidden) stopScan() }

onMounted(() => {
  camera = createQrCamera(() => new Html5Qrcode('qr-reader', { verbose: false, useBarCodeDetectorIfSupported: false }), reader.value, handleCode)
  document.addEventListener('visibilitychange', handleVisibility)
  window.addEventListener('pagehide', stopScan)
})
onBeforeUnmount(() => {
  disposed = true
  document.removeEventListener('visibilitychange', handleVisibility)
  window.removeEventListener('pagehide', stopScan)
  stopScan()
})
</script>

<style scoped>
.qr-checkin-page { max-width: 520px; margin: 0 auto; min-width: 0; }
.page-card { background: var(--el-bg-color); border: 1px solid var(--el-border-color-lighter); border-radius: 16px; padding: 24px; }
.page-head { text-align: center; margin-bottom: 20px; }
.page-head h2 { margin: 0 0 8px; font-size: 22px; }
.page-head p, .tips, .permission-hint { color: var(--el-text-color-secondary); font-size: 13px; line-height: 1.8; }
.page-head p { margin: 0; }
.scanner-wrap { position: relative; width: 100%; aspect-ratio: 1; max-width: 360px; margin: 0 auto; overflow: hidden; border-radius: 14px; background: #111827; }
.qr-reader { width: 100%; height: 100%; }
.scanner-mask { position: absolute; inset: 0; display: flex; align-items: center; justify-content: center; background: #0004; }
.camera-controls { display: flex; flex-wrap: wrap; gap: 12px; margin-top: 16px; }
.camera-controls .el-select { flex: 1; min-width: 0; }
.camera-error { margin-top: 16px; }
.tips { margin-top: 20px; }
.tips p { margin: 4px 0; }
@media (max-width: 600px) { .page-card { padding: 16px; } .page-head h2 { font-size: 20px; } }
</style>
