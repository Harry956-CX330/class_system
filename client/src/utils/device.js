const STORAGE_KEY = 'device_fingerprint'

function hashString(value) {
  let hash = 5381
  for (let i = 0; i < value.length; i += 1) {
    hash = ((hash << 5) + hash + value.charCodeAt(i)) >>> 0
  }
  return `fp${hash.toString(16)}`
}

export function getDeviceId() {
  const cached = localStorage.getItem(STORAGE_KEY)
  if (cached) return cached
  const raw = [
    navigator.userAgent,
    navigator.language,
    navigator.platform,
    `${screen.width}x${screen.height}x${screen.colorDepth}`,
    Intl.DateTimeFormat().resolvedOptions().timeZone || '',
    navigator.hardwareConcurrency || '',
  ].join('|')
  const id = hashString(`${raw}:${Date.now().toString(36)}:${Math.random().toString(36).slice(2, 10)}`)
  localStorage.setItem(STORAGE_KEY, id)
  return id
}
