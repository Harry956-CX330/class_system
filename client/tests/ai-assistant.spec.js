import { test, expect } from '@playwright/test'
test.use({ reducedMotion: 'reduce' })
const authCache = new Map()
const png = 'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aM1sAAAAASUVORK5CYII='
const settings = { enabled:true, configured:true, model:'glm-4.6v-flash', max_concurrent:1, min_interval_seconds:2, user_per_minute:3, user_per_day:40, global_per_minute:12, global_per_day:300, timeout_seconds:60, max_tokens:2048 }
const notice = { id:71, title:'活动报名与图片题目', content:'<p>请准备学生证，先阅读报名说明。</p>', text_preview:'请准备学生证', images:[0,1].map(index => ({index,url:`/test-image-${index}.png`,name:'题目图片'})) }
async function login(page, request, username='preview-student') {
  if (!authCache.has(username)) {
    const response = await request.post('/api/login', {data:{username,password:'PreviewOnly123!'}})
    expect(response.ok(), await response.text()).toBeTruthy()
    authCache.set(username, await response.json())
  }
  await page.addInitScript(({access_token,user}) => {
    localStorage.setItem('token',access_token);localStorage.setItem('user',JSON.stringify(user));localStorage.setItem('login_time',String(Date.now()));localStorage.setItem('currentView',user.role==='admin'?'admin':'user');localStorage.setItem('theme','dark')
  }, authCache.get(username))
  await page.route('**/api/ai/status', r=>r.fulfill({json:settings}))
  await page.route('**/api/ai/notices?*', r=>r.fulfill({json:[notice]}))
  await page.route('**/api/ai/notices/71', r=>r.fulfill({json:notice}))
  await page.route('**/test-image-*.png', r=>r.fulfill({contentType:'image/png',body:Buffer.from(png,'base64')}))
}
async function fits(page) { expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+2)).toBeTruthy() }

test('linked notice images, safe answer, followup, source dialog and responsive layout',async({page,request},info)=>{
  await login(page,request)
  const calls=[]
  await page.route('**/api/ai/chat', r=>{calls.push(r.request().postDataJSON());return r.fulfill({json:{answer:'先准备学生证。<img src=x onerror="window.aiInjected=true">',sources:[{id:71,title:notice.title,images_used:2}],images_used:2}})})
  await page.goto('/ai?notice=71')
  let dialog=page.getByRole('dialog',{name:'关联或导入公告',exact:true})
  await expect(dialog.locator('.image-choice input:checked')).toHaveCount(2)
  await expect(dialog).toContainText('2 / 4 张图片');await fits(page)
  expect(await dialog.evaluate(el=>{const r=el.getBoundingClientRect();return r.left>=0&&r.right<=innerWidth+1})).toBeTruthy()
  await expect(dialog).toHaveCSS('opacity','1')
  await page.screenshot({path:`test-results/ai-context-${info.project.name}.png`,fullPage:true,animations:'disabled'})
  await dialog.getByRole('button',{name:'完成关联',exact:true}).click()
  await page.getByRole('textbox',{name:'你的问题',exact:true}).fill('请讲解第1题并说明报名材料')
  await page.getByRole('button',{name:'发送问题',exact:true}).click()
  await expect(page.locator('.message.assistant')).toContainText('<img src=x')
  expect(await page.evaluate(()=>window.aiInjected)).toBeUndefined()
  expect(calls[0].notice_ids).toEqual([71]);expect(calls[0].notice_images).toEqual([{notice_id:71,image_index:0},{notice_id:71,image_index:1}])
  await page.locator('.answer-sources').getByRole('button').click()
  dialog=page.getByRole('dialog',{name:notice.title,exact:true});await expect(dialog).toContainText('请准备学生证');await dialog.getByRole('button',{name:'关闭原文',exact:true}).click()
  await page.getByRole('textbox',{name:'你的问题',exact:true}).fill('继续说明第二步')
  await expect(page.getByRole('button',{name:'发送问题',exact:true})).toBeEnabled()
  await page.getByRole('button',{name:'发送问题',exact:true}).click();await expect(page.locator('.message.assistant')).toHaveCount(2)
  expect(calls[1].history).toHaveLength(2)
  await page.getByRole('button',{name:'关联 / 导入公告',exact:true}).click()
  await page.getByRole('checkbox',{name:'公告 71 第 2 张图片',exact:true}).uncheck()
  await page.getByRole('button',{name:'完成关联',exact:true}).click()
  await expect(page.locator('.message')).toHaveCount(0);await fits(page)
})

test('imported screenshot is compressed, retry-after preserves question without auto retry',async({page,request},info)=>{
  await login(page,request);let calls=0;let payload
  await page.route('**/api/ai/chat',r=>{calls++;payload=r.request().postDataJSON();return r.fulfill({status:429,headers:{'Retry-After':'2'},json:{detail:'本分钟额度已用完'}})})
  await page.goto('/ai');await page.getByRole('button',{name:'关联 / 导入公告',exact:true}).click()
  const dialog=page.getByRole('dialog',{name:'关联或导入公告',exact:true})
  await dialog.getByRole('tab',{name:'导入公告文字 / 图片'}).click()
  await dialog.getByRole('textbox',{name:'导入公告文字',exact:true}).fill('外部活动报名：请准备身份证并联系主办方。')
  await dialog.locator('input[type=file][multiple]').setInputFiles({name:'报名截图.png',mimeType:'image/png',buffer:Buffer.from(png,'base64')})
  await expect(dialog.locator('.imported-image')).toHaveCount(1);await fits(page)
  await page.screenshot({path:`test-results/ai-import-${info.project.name}.png`,fullPage:true})
  await dialog.getByRole('button',{name:'完成关联',exact:true}).click()
  await page.locator('.el-radio-button').filter({hasText:'图片解题'}).click()
  const question=page.getByRole('textbox',{name:'你的问题',exact:true});await question.fill('图片中的报名要求是什么？')
  await page.getByRole('button',{name:'发送问题',exact:true}).click()
  await expect(page.locator('.chat-error')).toContainText('本分钟额度已用完')
  expect(payload.imported_images[0].data_url).toMatch(/^data:image\/jpeg;base64,/)
  expect(Buffer.from(payload.imported_images[0].data_url.split(',')[1],'base64').length).toBeLessThanOrEqual(160*1024)
  expect(payload.imported_text).toContain('请准备身份证');expect(payload.mode).toBe('exercise')
  await expect(question).toHaveValue('图片中的报名要求是什么？')
  await expect(page.getByRole('button',{name:'发送问题',exact:true})).toBeEnabled();expect(calls).toBe(1)
})

test('admin key stays blank after save and nonadmins cannot open configuration',async({page,request},info)=>{
  await login(page,request,'preview-admin');const saves=[]
  await page.route('**/api/ai/settings',r=>{if(r.request().method()==='PUT')saves.push(r.request().postDataJSON());return r.fulfill({json:settings})})
  await page.route('**/api/ai/test',r=>r.fulfill({json:{ok:true,message:'已成功连接智谱模型'}}))
  await page.goto('/ai-settings')
  const key=page.locator('input[autocomplete=new-password]');await expect(key).toHaveValue('')
  await key.fill('browser-test-secret-key');await page.getByRole('button',{name:'保存并测试连接',exact:true}).click()
  await expect(page.locator('.feedback')).toContainText('已成功连接智谱模型');await expect(key).toHaveValue('')
  expect(saves[0].api_key).toBe('browser-test-secret-key')
  await page.getByRole('button',{name:'保存设置',exact:true}).click();await expect(page.locator('.feedback')).toContainText('AI 设置已保存');expect(saves[1].api_key).toBe('')
  await fits(page);await page.screenshot({path:`test-results/ai-settings-${info.project.name}.png`,fullPage:true})
})

test('student cannot open AI service settings',async({page,request})=>{
  await login(page,request)
  await page.goto('/ai-settings');await expect(page).toHaveURL(/\/dashboard$/)
})

test('notice detail opens the matching AI context',async({page,request})=>{
  await login(page,request)
  await page.route('**/api/notices',r=>r.fulfill({json:[{...notice,author_name:'测试管理员',created_at:'2026-10-18T10:00:00',category:'活动安排'}]}))
  await page.goto('/notices')
  await page.getByRole('button',{name:'详细阅读',exact:true}).click()
  await page.getByRole('button',{name:'AI 解读 / 图片解题',exact:true}).click()
  await expect(page).toHaveURL(/\/ai\?notice=71$/)
  await expect(page.getByRole('dialog',{name:'关联或导入公告',exact:true})).toContainText(notice.title)
})
