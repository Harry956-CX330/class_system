import { test, expect } from '@playwright/test'
async function signIn(page, request, student=false) {
  const response=await request.post('/api/login',{data:{username:student?'preview-student':'preview-admin',password:'PreviewOnly123!'}})
  expect(response.ok()).toBeTruthy()
  const {access_token,user}=await response.json()
  await page.addInitScript(({token,user})=>{ localStorage.setItem('token',token);localStorage.setItem('user',JSON.stringify(user));localStorage.setItem('login_time',String(Date.now())); },{token:access_token,user})
}
test('navigation, notice editor and layout stay within viewport',async({page,request},testInfo)=>{
  const errors=[];page.on('pageerror',e=>errors.push(e.message))
  await signIn(page,request)
  for(const route of ['/dashboard','/notices','/file-tasks','/surveys','/survey-editor']) {
    await page.goto(route);await page.waitForLoadState('networkidle')
    expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+2),route).toBeTruthy()
    await page.screenshot({path:`test-results/${testInfo.project.name}-${route.slice(1)}.png`,fullPage:true})
  }
  await page.goto('/notices')
  await page.getByRole('button',{name:'发布新通知'}).click()
  const editor=page.getByRole('textbox',{name:'富文本正文'})
  await expect(editor).toBeVisible()
  await editor.fill('多端富文本测试')
  await expect(editor).toContainText('多端富文本测试')
  await page.getByRole('button',{name:'加粗',exact:true}).click()
  expect(errors).toEqual([])
})
test('student can complete a choice/rating survey',async({page,request})=>{
  await signIn(page,request,true)
  await page.goto('/surveys')
  await page.getByRole('button',{name:/填写|作答|再次/}).first().click()
  const dialog=page.getByRole('dialog')
  await expect(dialog.getByText('已完成 0 / 3 题')).toBeVisible()
  await dialog.getByText('户外运动',{exact:true}).click()
  await dialog.getByText('周三下午',{exact:true}).click()
  await dialog.locator('.el-rate__item').nth(3).click()
  await expect(dialog.getByText('已完成 3 / 3 题')).toBeVisible()
  await dialog.getByRole('button',{name:'提交答卷'}).click()
  await expect(dialog).toBeHidden()
  await expect(page.getByRole('button',{name:'再次填写'}).first()).toBeEnabled()
})
