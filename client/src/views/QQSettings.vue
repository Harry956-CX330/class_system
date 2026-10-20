<template>
  <div class="qq-settings-page" v-loading="loading">
    <h2>QQ 提醒设置</h2><p class="intro">统一管理机器人和多个通知群。每次发群通知、私信或邮件前都可以选择接收目标。</p>
    <el-alert title="机器人需要已加入所选群；私信是否可达取决于好友关系及 QQ 风控。测试连接通过服务器执行。" type="info" :closable="false" show-icon />
    <el-form label-position="top" @submit.prevent="save">
      <section class="settings-section"><h3>机器人连接</h3><el-form-item label="启用 QQ 提醒"><el-switch v-model="form.enabled" :active-value="1" :inactive-value="0" /></el-form-item><el-form-item label="OneBot HTTP API 地址"><el-input v-model="form.api_url" maxlength="300" placeholder="http://napcat:3001" /></el-form-item><el-form-item label="访问令牌"><el-input v-model="form.access_token" type="password" show-password autocomplete="new-password" :disabled="form.clear_token" :placeholder="configured?'留空保留已有令牌':'机器人 access_token（如已设置）'" maxlength="300" /></el-form-item><el-checkbox v-model="form.clear_token">删除已有访问令牌</el-checkbox><p class="hint">已有令牌不会回传到浏览器。变更连接地址后请重新填写令牌。</p></section>
      <section class="settings-section"><div class="section-heading"><h3>通知群（{{ form.groups.length }} / 10）</h3><el-button :disabled="form.groups.length>=10" @click="form.groups.push({id:'',name:''})">添加 QQ 群</el-button></div><p class="hint">默认群会在发送窗口预先选中；其他群需手动勾选，避免误发。删除群不会清除已发消息。</p><div v-for="(group,index) in form.groups" :key="index" class="group-row"><el-form-item :label="`第 ${index+1} 个群名称`"><el-input v-model="group.name" maxlength="50" placeholder="如：班级通知群" /></el-form-item><el-form-item label="QQ群号"><el-input v-model="group.id" inputmode="numeric" maxlength="12" placeholder="5–12 位群号" /></el-form-item><el-button type="danger" plain @click="removeGroup(index)">移除</el-button></div><el-form-item label="默认通知群"><el-select v-model="form.group_id" clearable placeholder="选择一个默认群"><el-option v-for="group in validGroups" :key="group.id" :label="`${group.name||'QQ群'} · ${group.id}`" :value="group.id" /></el-select></el-form-item></section>
      <div class="settings-actions"><el-button type="primary" native-type="submit" :loading="saving" :disabled="testing">保存设置</el-button><el-button :loading="testing" :disabled="saving" @click="testConnection">保存并测试机器人</el-button></div><el-alert v-if="feedback" :title="feedback" :type="feedbackType" show-icon :closable="false" class="feedback" />
    </el-form>
  </div>
</template>
<script setup>
import { computed,onMounted,reactive,ref } from 'vue'
import api from '../api'
const loading=ref(false),saving=ref(false),testing=ref(false),configured=ref(false),feedback=ref(''),feedbackType=ref('info')
const form=reactive({api_url:'',access_token:'',clear_token:false,group_id:'',groups:[],enabled:0})
const validGroups=computed(()=>form.groups.filter(group=>/^[1-9][0-9]{4,11}$/.test(group.id)))
function apply(data){form.api_url=data.api_url;form.group_id=data.group_id;form.groups=data.groups||[];form.enabled=data.enabled;form.access_token='';form.clear_token=false;configured.value=data.token_configured}
function removeGroup(index){const [removed]=form.groups.splice(index,1);if(removed.id===form.group_id)form.group_id=form.groups[0]?.id||''}
async function save(){
  if(saving.value)return false
  const groups=form.groups.map(row=>({id:row.id.trim(),name:row.name.trim()}))
  if(groups.some(row=>!/^[1-9][0-9]{4,11}$/.test(row.id))||new Set(groups.map(row=>row.id)).size!==groups.length){feedback.value='请输入有效且不重复的群号';feedbackType.value='error';return false}
  saving.value=true;feedback.value=''
  try{apply((await api.put('/api/qq-config',{...form,groups,group_id:form.group_id||groups[0]?.id||''})).data);feedback.value='QQ 提醒设置已保存';feedbackType.value='success';return true}
  catch(error){feedback.value=error.response?.data?.detail||'保存失败';feedbackType.value='error';return false}
  finally{saving.value=false}
}
async function testConnection(){if(testing.value||!await save())return;testing.value=true;try{const {data}=await api.post('/api/qq-config/test');feedback.value=`${data.message} · QQ ${data.qq_number||'已登录'}`;feedbackType.value='success'}catch(error){feedback.value=error.response?.data?.detail||'连接失败';feedbackType.value='error'}finally{testing.value=false}}
onMounted(async()=>{loading.value=true;try{apply((await api.get('/api/qq-config')).data)}catch{feedback.value='无法加载 QQ 设置';feedbackType.value='error'}finally{loading.value=false}})
</script>
<style scoped>
.qq-settings-page{max-width:1000px;margin:auto;min-width:0}h2{margin:0 0 12px}h3{margin:0 0 18px}.intro,.hint{font-size:13px;color:var(--el-text-color-secondary);line-height:1.8}.settings-section{padding:24px;border:1px solid var(--el-border-color-lighter);border-radius:16px;background:var(--el-bg-color);margin:20px 0}.section-heading,.settings-actions{display:flex;gap:12px;justify-content:space-between;flex-wrap:wrap}.settings-actions{justify-content:flex-start}.settings-actions .el-button{margin-left:0}.group-row{display:grid;grid-template-columns:1fr 1fr auto;gap:14px;align-items:center;border-bottom:1px solid var(--el-border-color-lighter);margin:16px 0}.feedback{margin-top:18px}@media(max-width:600px){.settings-section{padding:18px 14px}.group-row{grid-template-columns:minmax(0,1fr);gap:0;padding-bottom:16px}.group-row>.el-button{justify-self:end}.section-heading h3{margin-bottom:0}}
</style>
