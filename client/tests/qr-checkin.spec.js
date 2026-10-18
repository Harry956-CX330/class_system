import { test, expect } from '@playwright/test'
test.use({ launchOptions: { args: ['--use-fake-device-for-media-stream', '--use-fake-ui-for-media-stream'] } })
async function login(page, request, username = 'preview-admin') {
  const response = await request.post('/api/login', { data: { username, password: 'PreviewOnly123!' } })
  expect(response.ok()).toBeTruthy()
  await page.addInitScript(({ access_token, user }) => {
    localStorage.setItem('token', access_token); localStorage.setItem('user', JSON.stringify(user)); localStorage.setItem('login_time', String(Date.now())); localStorage.setItem('currentView', user.role === 'admin' ? 'admin' : 'user'); localStorage.setItem('theme', 'dark')
  }, await response.json())
}
async function fits(page) { expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 2)).toBeTruthy() }

test('camera permission retry, constraint fallback, narrow scan box and stream release', async ({ page, request }) => {
  await login(page, request, 'preview-student')
  await page.addInitScript(() => {
    const native = navigator.mediaDevices.getUserMedia.bind(navigator.mediaDevices)
    window.cameraCalls = []; window.testStreams = []
    navigator.mediaDevices.getUserMedia = async constraints => {
      window.cameraCalls.push(constraints)
      if (window.cameraCalls.length === 1) throw new DOMException('denied', 'NotAllowedError')
      if (window.cameraCalls.length === 2) throw new DOMException('rear unavailable', 'OverconstrainedError')
      const stream = await native(constraints); window.testStreams.push(stream); return stream
    }
  })
  await page.goto('/qr-checkin')
  const start = page.getByRole('button', { name: '开启摄像头', exact: true })
  await start.click(); await expect(page.locator('.camera-error')).toContainText('相机权限未开启')
  expect(await page.evaluate(() => window.cameraCalls.length)).toBe(1)
  await page.setViewportSize({ width: 320, height: 740 })
  await start.click(); await expect(page.getByRole('button', { name: '关闭摄像头', exact: true })).toBeEnabled()
  expect(await page.evaluate(() => window.cameraCalls.length)).toBe(3)
  expect(await page.evaluate(() => window.cameraCalls[2].video)).toEqual({})
  await expect(page.locator('#qr-reader video')).toBeVisible(); await fits(page)
  await page.getByRole('button', { name: '关闭摄像头', exact: true }).click()
  await expect(start).toBeEnabled()
  await expect.poll(() => page.evaluate(() => window.testStreams.every(s => s.getTracks().every(t => t.readyState === 'ended')))).toBeTruthy()
})

test('responsive management, roster filter/edit, expired tasks and QR retry', async ({ page, request }, info) => {
  await login(page, request)
  const task = { id: 700, name: '周一班会签到 · 手机平板与长标题显示测试', status: 'active', qr_type: 'dynamic', refresh_seconds: 3, expires_at: '2099-01-01T12:00:00', signed_count: 1, leave_count: 0, total_students: 50, can_manage_records: true }
  const rows = Array.from({ length: 50 }, (_, i) => ({ student_id: i + 100, name: `测试同学${i}`, student_no: `2026000${i}`, status: i === 0 ? 'auto' : 'absent', sign_time: i === 0 ? '2026-10-18T08:00:00' : null, device_id: i === 0 ? 'long-device-identifier'.repeat(5) : '' }))
  await page.route('**/api/qr-checkin/tasks', route => route.fulfill({ json: [task, { ...task, id: 701, name: '已到期签到', expires_at: '2020-01-01T00:00:00' }] }))
  await page.route('**/api/qr-checkin/tasks/700/records', route => route.fulfill({ json: { task, records: rows } }))
  await page.route('**/api/qr-checkin/tasks/700/manual', async route => { const update = route.request().postDataJSON(); rows.find(r => r.student_id === update.student_id).status = update.status; await route.fulfill({ json: { message: '状态已更新' } }) })
  let qrCalls = 0
  await page.route('**/api/qr-checkin/tasks/700/refresh-code', route => {
    qrCalls++
    return qrCalls === 1 ? route.fulfill({ status: 503, json: { detail: '网络暂不可用' } }) : route.fulfill({ json: { ...task, qr_data_url: 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aM1sAAAAASUVORK5CYII=' } })
  })
  await page.goto('/qr-checkin/manage'); await expect(page.getByText('已到期', { exact: true })).toBeVisible(); await fits(page)
  if (info.project.name !== 'desktop') await expect(page.locator('.task-card')).toHaveCount(2)
  await page.getByRole('button', { name: '二维码', exact: true }).first().click()
  let dialog = page.getByRole('dialog', { name: '签到二维码', exact: true })
  await expect(dialog).toContainText('网络暂不可用'); await dialog.getByRole('button', { name: '重新加载' }).click(); await expect(dialog.locator('.qr-image')).toBeVisible()
  await dialog.getByRole('button', { name: '关闭此对话框' }).click()
  const count = qrCalls; await page.waitForTimeout(3500); expect(qrCalls).toBe(count)
  await page.getByRole('button', { name: '名单', exact: true }).first().click(); dialog = page.getByRole('dialog')
  await expect(dialog).toContainText('当前显示 50 人'); await fits(page)
  await dialog.getByRole('textbox', { name: '搜索姓名或学号' }).fill('202600049'); await expect(dialog).toContainText('当前显示 1 人'); await expect(dialog.getByText('测试同学49', { exact: true })).toBeVisible()
  await dialog.getByRole('button', { name: '设为已签到', exact: true }).click(); await expect(dialog).toContainText('已签到（补签）')
  await dialog.getByRole('textbox', { name: '搜索姓名或学号' }).fill(''); await expect(dialog).toContainText('当前显示 50 人')
  if (info.project.name !== 'desktop') {
    expect(await dialog.locator('.record-cards').evaluate(el => { el.scrollTop = el.scrollHeight; return el.scrollTop > 0 })).toBeTruthy()
  }
  await page.screenshot({ path: `test-results/qr-roster-${info.project.name}.png`, fullPage: true })
  expect(await dialog.evaluate(el => { const rect = el.getBoundingClientRect(); return rect.left >= 0 && rect.right <= innerWidth + 1 })).toBeTruthy()
})
