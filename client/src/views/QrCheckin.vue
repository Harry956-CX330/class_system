<template>
  <div class="qr-checkin-page">
    <div class="page-card">
      <div class="page-head">
        <h2>扫码签到</h2>
        <p>对准管理员展示的二维码，完成本次签到</p>
      </div>

      <div class="scanner-wrap">
        <div id="qr-reader" class="qr-reader"></div>
        <div v-if="!scanning" class="scanner-mask">
          <el-button type="primary" :loading="starting" @click="startScan">
            {{ starting ? '正在开启摄像头…' : '开启摄像头' }}
          </el-button>
        </div>
      </div>

      <div class="tips">
        <p>• 请允许浏览器使用相机权限</p>
        <p>• 动态二维码会定期刷新，请扫当前画面</p>
        <p>• 一台设备本场签到只能成功一次</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Html5Qrcode } from 'html5-qrcode'
import api from '../api'
import { getDeviceId } from '../utils/device'

const scanning = ref(false)
const starting = ref(false)
const processing = ref(false)

let scanner = null
let started = false
let disposed = false

function showResult(title, message, type) {
  ElMessageBox.alert(message, title, {
    type,
    confirmButtonText: '知道了',
    showClose: false,
  })
    .catch(() => {})
    .finally(() => {
      processing.value = false
    })
}

async function handleCode(code) {
  if (processing.value) return
  processing.value = true
  try {
    const res = await api.post('/api/qr-checkin/verify', {
      code,
      device_id: getDeviceId(),
    })
    showResult('签到成功', `你已在「${res.data.task_name}」签到成功`, 'success')
  } catch (error) {
    const detail = error.response?.data?.detail || '签到失败，请稍后重试'
    showResult('签到失败', detail, 'error')
  }
}

async function startScan() {
  if (scanner || disposed) return
  starting.value = true
  const instance = new Html5Qrcode('qr-reader', { verbose: false })
  scanner = instance
  try {
    await instance.start(
      { facingMode: 'environment' },
      { fps: 10, qrbox: { width: 240, height: 240 } },
      (decodeText) => handleCode(decodeText),
      () => {},
    )
    started = true
    scanning.value = true
    if (disposed) {
      await stopScan()
    }
  } catch (error) {
    if (!disposed) ElMessage.error('无法打开摄像头，请检查权限或换用浏览器')
  } finally {
    starting.value = false
    if (disposed) scanner = null
  }
}

async function stopScan() {
  const instance = scanner
  if (instance && started) {
    try { await instance.stop() } catch {}
    try { instance.clear() } catch {}
    scanner = null
  }
  started = false
  scanning.value = false
}

function handleVisibility() {
  if (document.hidden) {
    stopScan()
  }
}

onMounted(() => {
  document.addEventListener('visibilitychange', handleVisibility)
})

onBeforeUnmount(() => {
  disposed = true
  document.removeEventListener('visibilitychange', handleVisibility)
  stopScan()
})
</script>

<style scoped>
.qr-checkin-page {
  padding: 16px;
  max-width: 520px;
  margin: 0 auto;
}

.page-card {
  background: var(--el-bg-color);
  border-radius: 14px;
  padding: 20px;
  box-shadow: 0 4px 18px rgba(0, 0, 0, 0.06);
}

.page-head {
  text-align: center;
  margin-bottom: 16px;
}

.page-head h2 {
  margin: 0 0 6px;
  font-size: 20px;
}

.page-head p {
  margin: 0;
  color: var(--el-text-color-secondary);
  font-size: 13px;
}

.scanner-wrap {
  position: relative;
  width: 100%;
  aspect-ratio: 1 / 1;
  max-width: 360px;
  margin: 0 auto;
  overflow: hidden;
  border-radius: 12px;
  background: #111;
}

.qr-reader {
  width: 100%;
  height: 100%;
}

.scanner-mask {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(0, 0, 0, 0.25);
}

.tips {
  margin-top: 16px;
  color: var(--el-text-color-secondary);
  font-size: 13px;
  line-height: 1.8;
}

.tips p {
  margin: 0;
}
</style>
