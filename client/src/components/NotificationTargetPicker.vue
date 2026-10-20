<template>
  <el-dialog :model-value="state.visible" :title="title" width="min(680px, calc(100vw - 24px))" class="target-picker-dialog" :close-on-click-modal="false" @close="finishNotificationPicker(true)">
    <p class="target-scope">{{ state.scope }}。确认后只向选中的目标发送；发送时系统会重新核验完成状态。</p>
    <el-input v-model="state.filter" clearable placeholder="搜索姓名、学号、群名或号码" aria-label="搜索通知目标" />
    <div class="target-tools"><span>已选择 {{ state.selected.length }} / {{ available.length }} {{ state.channel==='group'?'个群':'人' }}</span><el-button link type="primary" @click="selectVisible">选中当前搜索结果</el-button><el-button link @click="state.selected=[]">清空</el-button></div>
    <el-checkbox-group v-model="state.selected" class="target-options" aria-label="通知目标">
      <label v-for="row in filtered" :key="row.id" class="target-row" :class="{unavailable:!isAvailable(row)}"><el-checkbox :value="row.id" :disabled="!isAvailable(row)"><span class="target-name">{{ row.name || row.id }}</span><span class="target-meta">{{ state.channel==='group' ? `群号 ${row.id}` : `${row.student_id || ''} · ${row.address || '未填写联系方式'}` }}</span><span v-if="!isAvailable(row)" class="target-unavailable">请先在用户管理补全有效{{ state.channel==='qq'?'QQ号':'邮箱' }}</span></el-checkbox></label>
    </el-checkbox-group>
    <el-empty v-if="!filtered.length" description="当前没有可选目标" :image-size="50" />
    <div v-if="state.channel==='group'" class="mention-all"><el-checkbox v-model="state.atAll">@全体成员</el-checkbox><p class="target-scope">仅对本次选中的群生效。机器人需要具备权限及可用次数；无法 @ 时会提示该群未发送，可取消勾选后发送普通通知。</p></div>
    <div v-if="state.email" class="original-email"><el-checkbox :model-value="!state.selected.length" @change="state.selected=[]">使用原指定邮箱：{{ state.email }}</el-checkbox><p>选择系统用户后仅发送给所选用户，不会同时发送原指定邮箱。</p></div>
    <template #footer><div class="target-footer"><el-button @click="finishNotificationPicker(true)">取消发送</el-button><el-button type="primary" :disabled="!state.selected.length&&!state.email" @click="finishNotificationPicker()">确认发送{{ state.channel==='group'&&state.atAll?'并@全体成员':'' }}{{ state.selected.length ? `（${state.selected.length}${state.channel==='group'?'个群':'人'}）`:'' }}</el-button></div></template>
  </el-dialog>
</template>
<script setup>
import { computed, watch } from 'vue'
import { notificationPicker as state, finishNotificationPicker } from '../utils/notificationPicker'
const title=computed(()=>state.channel==='group'?'选择要通知的 QQ 群':state.channel==='qq'?'选择 QQ 私信收件人':'选择邮件收件人')
const rows=computed(()=>state.channel==='group'?state.groups:state.users)
const isAvailable=row=>state.channel==='group'||row.available
const available=computed(()=>rows.value.filter(isAvailable))
const filtered=computed(()=>rows.value.filter(row=>`${row.name} ${row.student_id||''} ${row.address||row.id}`.toLowerCase().includes(state.filter.toLowerCase())))
function selectVisible(){state.selected=[...new Set([...state.selected,...filtered.value.filter(isAvailable).map(row=>row.id)])]}
watch(()=>state.visible,value=>{if(!value)finishNotificationPicker(true)})
</script>
<style scoped>
.target-scope{font-size:13px;line-height:1.8;color:var(--el-text-color-secondary);margin-top:0}.target-tools{display:flex;gap:12px;align-items:center;flex-wrap:wrap;font-size:13px;margin:16px 0}.target-options{display:flex;flex-direction:column;max-height:48dvh;overflow:auto;overscroll-behavior:contain;gap:8px}.target-row{border:1px solid var(--el-border-color-lighter);border-radius:10px;padding:12px;min-width:0}.target-row :deep(.el-checkbox){height:auto;white-space:normal;width:100%;margin:0}.target-row :deep(.el-checkbox__label){display:flex;flex-direction:column;gap:5px;white-space:normal;overflow-wrap:anywhere;line-height:1.6;min-width:0}.target-name{font-weight:600}.target-meta,.target-unavailable{font-size:12px;color:var(--el-text-color-secondary)}.unavailable{opacity:.7}.target-footer{display:flex;flex-wrap:wrap;gap:10px;justify-content:flex-end}.original-email{font-size:12px;line-height:1.7;margin-top:14px}.original-email :deep(.el-checkbox){height:auto;white-space:normal}.original-email :deep(.el-checkbox__label){white-space:normal;overflow-wrap:anywhere}
</style>
