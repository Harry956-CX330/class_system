import { reactive } from 'vue'
export const notificationPicker = reactive({ visible:false, loading:false, endpoint:'', channel:'email', scope:'', users:[], groups:[], selected:[], filter:'', email:'', error:'', atAll:false })
let pending = null
export function openNotificationPicker(endpoint, options, payload={}) {
  if (pending) return Promise.reject(new Error('请先完成当前收件人选择'))
  Object.assign(notificationPicker, {visible:true,endpoint,channel:options.channel,scope:options.scope,users:options.users,groups:options.groups,filter:'',email:payload.email||'',error:'',atAll:false})
  notificationPicker.selected = options.channel === 'group'
    ? options.groups.filter(row=>row.id===options.default_group_id).map(row=>row.id)
    : payload.student_id ? options.users.filter(row=>row.id===payload.student_id&&row.available).map(row=>row.id)
    : options.users.filter(row=>row.available).map(row=>row.id)
  return new Promise((resolve,reject)=>{pending={resolve,reject,payload}})
}
export function finishNotificationPicker(cancel=false) {
  if (!pending) return
  const current=pending;pending=null;notificationPicker.visible=false
  if (cancel) { const error=new Error('已取消发送');error.__notificationCancelled=true;current.reject(error);return }
  const selection=notificationPicker.selected
  if (notificationPicker.channel==='group') current.resolve({...current.payload,group_ids:selection,at_all:notificationPicker.atAll})
  else if (!selection.length && notificationPicker.email) current.resolve({...current.payload,email:notificationPicker.email})
  else current.resolve({...current.payload,recipient_ids:selection})
}
export function needsTargetSelection(url) {
  return /^\/api\/qq\/(notice|file-task|survey|group-project|activity|class-meeting)\/\d+\/(notify|remind|remind-one|remind-leaders)$/.test(url||'') ||
    /^\/api\/(notices|file-tasks|surveys|class-meetings)\/\d+\/send-email$/.test(url||'') ||
    ['/api/textbooks/qq-remind-unordered','/api/textbooks/qq-remind-unordered-email','/api/textbooks/orders/send-emails','/api/textbooks/orders/send-dorm-emails','/api/email-history/resend'].includes(url)
}
