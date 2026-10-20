import { test,expect } from '@playwright/test'
test.use({reducedMotion:'reduce'})
const cache=new Map()
async function login(page,request,user='preview-leader'){
  if(!cache.has(user)){
    const response=await request.post('/api/login',{data:{username:user,password:'PreviewOnly123!'}})
    expect(response.ok(),await response.text()).toBeTruthy();cache.set(user,await response.json())
  }
  await page.addInitScript(({access_token,user})=>{localStorage.setItem('token',access_token);localStorage.setItem('user',JSON.stringify(user));localStorage.setItem('login_time',String(Date.now()));localStorage.setItem('currentView',user.role==='admin'||user.is_class_leader?'admin':'user');localStorage.setItem('theme','dark')},cache.get(user))
}
async function fits(page){expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+2)).toBeTruthy()}
const notice={id:700,title:'多群与指定收件人测试',content:'<p>这是一条测试公告</p>',category:'活动安排',author_name:'测试班干',created_at:'2026-10-20T10:00:00'}
const users=[{id:2,name:'测试同学甲',student_id:'20260001',address:'100002',available:true},{id:3,name:'测试同学乙',student_id:'20260002',address:'100003',available:true},{id:4,name:'未填写同学',student_id:'20260003',address:'',available:false}]

test('pick multiple groups, select private recipients, select mail recipients and cancel without sending',async({page,request},info)=>{
  await login(page,request)
  const calls=[]
  await page.route('**/api/notices',r=>r.fulfill({json:[notice]}))
  await page.route('**/api/notifications/targets?*',r=>{
    const endpoint=new URL(r.request().url()).searchParams.get('endpoint');const group=endpoint.endsWith('/notify');const email=endpoint.endsWith('/send-email')
    return r.fulfill({json:{channel:group?'group':email?'email':'qq',scope:group?'已配置的 QQ 群':'全班同学',groups:[{id:'123456',name:'班级通知群'},{id:'654321',name:'班干事务群'}],default_group_id:'123456',users:email?users.map(user=>({...user,address:user.available?`user${user.id}@example.test`:''})):users}})
  })
  await page.route('**/api/qq/notice/700/*',r=>{calls.push({url:r.request().url(),data:r.request().postDataJSON()});return r.fulfill({json:{message:'通知发送完成',sent:1,failed:0,success:true}})})
  await page.route('**/api/notices/700/send-email',r=>{calls.push({url:r.request().url(),data:r.request().postDataJSON()});return r.fulfill({json:{success:true,detail:{success:true,sent:1,failed:0}}})})
  await page.goto('/notices');await page.getByRole('button',{name:'QQ群',exact:true}).click()
  await page.getByRole('dialog',{name:'QQ群通知确认',exact:true}).getByRole('button',{name:'发送',exact:true}).click()
  let dialog=page.getByRole('dialog',{name:'选择要通知的 QQ 群',exact:true})
  await expect(dialog).toBeVisible();await expect(dialog.getByRole('checkbox',{checked:true})).toHaveCount(1)
  await dialog.locator('.target-row').filter({hasText:'班干事务群'}).locator('label.el-checkbox').click()
  await expect(dialog.getByRole('checkbox',{checked:true})).toHaveCount(2);await fits(page)
  await page.screenshot({path:`test-results/notify-groups-${info.project.name}.png`,fullPage:true,animations:'disabled'})
  await dialog.getByRole('button',{name:'确认发送（2个群）',exact:true}).click()
  await expect.poll(()=>calls.length).toBe(1);expect(calls[0].data.group_ids).toEqual(['123456','654321'])
  await page.getByRole('button',{name:'私信',exact:true}).click();dialog=page.getByRole('dialog',{name:'选择 QQ 私信收件人',exact:true})
  await expect(dialog.getByRole('checkbox',{checked:true})).toHaveCount(2)
  await expect(dialog.locator('.target-row').filter({hasText:'未填写同学'}).getByRole('checkbox')).toBeDisabled()
  await dialog.getByRole('button',{name:'清空',exact:true}).click();await dialog.getByRole('textbox',{name:'搜索通知目标'}).fill('20260002')
  await dialog.getByRole('button',{name:'选中当前搜索结果',exact:true}).click()
  await dialog.getByRole('button',{name:'确认发送（1人）',exact:true}).click();await expect.poll(()=>calls.length).toBe(2);expect(calls[1].data.recipient_ids).toEqual([3])
  await page.getByRole('button',{name:'邮件',exact:true}).click();await page.getByRole('dialog',{name:'邮件通知确认',exact:true}).getByRole('button',{name:'发送',exact:true}).click()
  dialog=page.getByRole('dialog',{name:'选择邮件收件人',exact:true});await dialog.getByRole('button',{name:'清空',exact:true}).click()
  await dialog.locator('.target-row').filter({hasText:'测试同学甲'}).locator('label.el-checkbox').click();await dialog.getByRole('button',{name:'确认发送（1人）',exact:true}).click()
  await expect.poll(()=>calls.length).toBe(3);expect(calls[2].data.recipient_ids).toEqual([2])
  await page.getByRole('button',{name:'私信',exact:true}).click();await page.getByRole('dialog',{name:'选择 QQ 私信收件人',exact:true}).getByRole('button',{name:'取消发送',exact:true}).click()
  await expect(page.getByRole('dialog',{name:'选择 QQ 私信收件人',exact:true})).toBeHidden();expect(calls.length).toBe(3)
  await expect(page.getByText('发送失败',{exact:true})).toHaveCount(0)
})

test('multi-group configuration saves names and server-side test without returning token',async({page,request},info)=>{
  await login(page,request);const saved=[]
  let config={api_url:'http://napcat:3001',group_id:'123456',enabled:1,groups:[{id:'123456',name:'原班级群'}],token_configured:true}
  await page.route('**/api/qq-config',r=>{if(r.request().method()==='PUT'){const data=r.request().postDataJSON();saved.push(data);config={...config,...data,token_configured:true};delete config.access_token}return r.fulfill({json:config})})
  await page.route('**/api/qq-config/test',r=>r.fulfill({json:{message:'机器人连接正常',qq_number:'100000'}}))
  await page.goto('/qq-settings');await expect(page.locator('input[autocomplete=new-password]')).toHaveValue('')
  await page.getByRole('button',{name:'添加 QQ 群',exact:true}).click()
  const row=page.locator('.group-row').last();await row.getByRole('textbox').nth(0).fill('第二个通知群');await row.getByRole('textbox').nth(1).fill('654321')
  await page.getByRole('button',{name:'保存并测试机器人',exact:true}).click();await expect(page.locator('.feedback')).toContainText('机器人连接正常')
  expect(saved[0].groups).toEqual([{id:'123456',name:'原班级群'},{id:'654321',name:'第二个通知群'}]);expect(saved[0].access_token).toBe('')
  await fits(page);await page.screenshot({path:`test-results/notify-settings-${info.project.name}.png`,fullPage:true,animations:'disabled'})
})

const status={requests_last_minute:137,rejected_last_minute:24,inflight_requests:2,rejected_requests:36,uptime_seconds:6800,blocked_sources:[{peer:'198.51.100.1',remaining_seconds:240}],events:[{id:1,reason:'同一来源短时间请求过多',action:'临时封禁来源',time:'2026-10-20T12:00:00+08:00',peer:'198.51.100.1',count:3,path:'/api/notices'}],alerts:[{event:'请求超限',time:'2026-10-20T12:00:01+08:00',incidents:3,channels:{email:{sent:4,failed:0,missing:0,state:'已完成'},qq:{sent:3,failed:1,missing:0,state:'部分失败'}}}],alert_readiness:{leaders:4,email_contacts:4,qq_contacts:4,smtp_configured:true,qq_enabled:true},pending_alert:false,can_configure:false,resources:{container_cpu_percent:12.3,container_cpu_limit:1.5,container_memory_used:180*1024**2,container_memory_limit:512*1024**2,host_memory_available:700*1024**2,disk_total:40*1024**3,disk_free:21*1024**3,network_send_bytes_per_second:48000,network_receive_bytes_per_second:10000,scope:'容器及宿主可用内存分开显示'},settings:{enabled:true,alerts_enabled:true,ip_per_10_seconds:300,ip_per_minute:1800,global_per_10_seconds:1500,login_per_minute:120,login_failures_per_minute:30,block_seconds:300,alert_cooldown_seconds:300}}
test('leader can inspect resources and alerts, scroll incidents and unblock without editing thresholds',async({page,request},info)=>{
  await login(page,request);let unblocked
  await page.route('**/api/server/status',r=>r.fulfill({json:status}))
  await page.route('**/api/server/unblock',r=>{unblocked=r.request().postDataJSON();return r.fulfill({json:{message:'已解除'}})})
  await page.goto('/server-status');await expect(page.getByRole('heading',{name:'服务器状态与安全防护'})).toBeVisible()
  await expect(page.getByText('12.3%',{exact:true})).toBeVisible();await expect(page.locator('.server-section').filter({has:page.getByRole('heading',{name:'班干告警投递'})})).toContainText('QQ 私信：部分失败')
  await expect(page.getByRole('button',{name:'保存防护设置',exact:true})).toHaveCount(0)
  await expect(page.getByRole('spinbutton').first()).toBeDisabled();await fits(page)
  await page.screenshot({path:`test-results/server-status-${info.project.name}.png`,fullPage:true,animations:'disabled'})
  await page.getByRole('button',{name:'解除封禁',exact:true}).click();await page.getByRole('dialog',{name:'确认解除',exact:true}).getByRole('button',{name:'确定',exact:true}).click()
  await expect.poll(()=>unblocked?.peer).toBe('198.51.100.1')
})

test('textbook cancel is silent and send errors remain visible',async({page,request})=>{
  await login(page,request)
  let sent=0
  await page.route('**/api/notifications/targets?*',r=>r.fulfill({json:{channel:'email',scope:'教材收件人',users:[{id:2,name:'测试同学',address:'test@example.test',available:true}],groups:[]}}))
  await page.route('**/api/textbooks/orders/send-emails',r=>{sent++;return r.fulfill({status:409,json:{detail:'收件人状态已变更，请重新选择'}})})
  await page.goto('/textbook-order')
  async function pick(){await page.getByRole('button',{name:'发送订购邮件',exact:true}).click();await page.getByRole('dialog',{name:'发送邮件',exact:true}).getByRole('button',{name:'确定',exact:true}).click();const dialog=page.getByRole('dialog',{name:'选择邮件收件人',exact:true});await expect(dialog).toBeVisible();return dialog}
  let dialog=await pick();await dialog.getByRole('button',{name:'取消发送',exact:true}).click();await expect(dialog).toBeHidden();expect(sent).toBe(0)
  await expect(page.getByText('发送失败',{exact:true})).toHaveCount(0)
  dialog=await pick();await dialog.getByRole('button',{name:'确认发送（1人）',exact:true}).click()
  await expect(page.getByText('收件人状态已变更，请重新选择',{exact:true})).toBeVisible();expect(sent).toBe(1)
})
