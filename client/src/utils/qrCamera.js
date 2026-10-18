// html5-qrcode wraps some DOMExceptions in strings; handle both forms.
export function cameraErrorKind(error) {
  const text = `${error?.name || ''} ${error?.message || error || ''}`
  if (/NotAllowed|PermissionDenied|permission denied|permission dismissed|SecurityError/i.test(text)) return 'permission'
  if (/NotFound|DevicesNotFound|Overconstrained|ConstraintNotSatisfied/i.test(text)) return 'device'
  if (/NotReadable|TrackStart|AbortError|could not start|in use/i.test(text)) return 'busy'
  return 'unknown'
}

export function cameraErrorMessage(error) {
  return {
    permission: '相机权限未开启。请在浏览器的网站设置和手机系统设置中允许相机，然后点击重试；QQ、微信内无法授权时，请在系统浏览器中打开。',
    device: '未找到可用相机。请检查相机是否被禁用，或选择其他摄像头后重试。',
    busy: '相机被其他应用占用或启动失败。请关闭其他扫码、拍照页面后重试。',
    unknown: '相机启动失败，请重试或切换摄像头。若在应用内打开，请改用系统浏览器访问本页。',
  }[cameraErrorKind(error)]
}

export function scanBox(width, height) {
  const edge = Math.floor(Math.min(width, height) * 0.7)
  return { width: edge, height: edge }
}

// Serialize ownership, including permission prompts resolving after a route change.
export function createQrCamera(createScanner, reader, onCode) {
  let current = null
  let pending = null
  let stopping = null
  let generation = 0

  async function release(instance) {
    try { if (instance?.isScanning) await instance.stop() } catch {}
    // A failed render can leave a stream attached without isScanning=true.
    for (const video of reader.querySelectorAll('video')) {
      video.srcObject?.getTracks().forEach(track => track.stop())
      video.srcObject = null
    }
    try { instance?.clear() } catch {}
  }

  function start(deviceId = '') {
    if (stopping) return stopping.then(() => start(deviceId))
    if (pending) return pending
    if (current) return Promise.resolve(true)
    const token = ++generation
    pending = (async () => {
      const attempts = deviceId
        ? [{ deviceId: { exact: deviceId } }]
        : [{ facingMode: { ideal: 'environment' } }, {}]
      for (let index = 0; index < attempts.length; index++) {
        let instance
        try {
          instance = createScanner()
          current = instance
          await instance.start({ facingMode: 'environment' }, {
            fps: 8, qrbox: scanBox, videoConstraints: attempts[index],
          }, code => { if (token === generation) onCode(code) }, () => {})
          if (token !== generation) {
            await release(instance)
            current = null
            return false
          }
          return true
        } catch (error) {
          await release(instance)
          current = null
          if (token !== generation) return false
          if (cameraErrorKind(error) === 'permission' || index === attempts.length - 1) throw error
        }
      }
    })().finally(() => { pending = null })
    return pending
  }

  function stop() {
    generation++
    if (stopping) return stopping
    stopping = (async () => {
      if (pending) { try { await pending } catch {} }
      const instance = current
      current = null
      await release(instance)
    })().finally(() => { stopping = null })
    return stopping
  }

  return { start, stop }
}
