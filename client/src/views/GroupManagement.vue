<template>
  <div class="group-manage-container">
    <div class="page-header">
      <div class="header-left">
        <div class="title-indicator"></div>
        <h3 class="page-title">分组管理</h3>
      </div>
      <div v-if="authStore.canViewAllData" class="header-actions">
        <el-button type="primary" :icon="Plus" @click="showCreateDialog = true" class="header-btn">新建分组</el-button>
      </div>
    </div>

    <el-empty v-if="projects.length === 0 && !loading" description="暂无分组项目">
      <el-button v-if="authStore.canViewAllData" type="primary" @click="showCreateDialog = true">立即创建</el-button>
    </el-empty>

    <div v-for="project in projects" :key="project.id" class="project-card">
      <el-card class="modern-card" shadow="never">
        <div class="project-header" @click="toggleProject(project.id)">
          <div class="project-info">
            <el-icon class="project-icon"><Files /></el-icon>
            <div class="project-text-box">
              <h4 class="project-name">{{ project.name }}</h4>
              <div class="project-meta">
                {{ project.group_count }} 个组 · 每组 {{ project.members_per_group }} 人 · 已分配 {{ project.total_assigned }} 人
                <div v-if="project.deadline" class="deadline-text" :class="{ 'is-expired': isExpired(project.deadline) }">
                  截止：{{ formatTime(project.deadline) }}
                  <el-tag v-if="isExpired(project.deadline)" size="small" type="danger" effect="dark" style="margin-left: 6px;">已截止</el-tag>
                </div>
              </div>
            </div>
          </div>
          <div class="project-actions-header">
            <el-progress 
              :percentage="Math.round(project.total_assigned / (project.group_count * project.members_per_group) * 100)"
              :stroke-width="6"
              :show-text="false"
              class="header-progress"
            />
            <el-icon :class="{ 'arrow-rotate': expandedProjectId === project.id }">
              <ArrowDown />
            </el-icon>
          </div>
        </div>

        <el-collapse-transition>
          <div v-show="expandedProjectId === project.id" class="project-detail">
            <el-divider />

            <div v-if="!authStore.canViewAllData" class="student-join-area">
              <div v-if="myAssignment[project.id]" class="my-group-info">
                <el-alert 
                  :title="`你已加入第 ${myAssignment[project.id].group_number} 组 · 身份：${myAssignment[project.id].role === 'leader' ? '组长' : '组员'}`"
                  type="success" :closable="false" show-icon
                />
                <el-button 
                  type="danger" plain size="small" class="leave-btn"
                  :disabled="isExpired(project.deadline)"
                  @click="handleLeave(project.id)"
                >
                  退出当前小组
                </el-button>
              </div>
              <div v-else class="join-area">
                <div v-if="isExpired(project.deadline)" class="join-closed-hint">
                  <el-alert title="已过截止时间，系统已自动分配小组" type="info" :closable="false" show-icon />
                </div>
                <template v-else>
                  <div class="join-item">
                    <span class="join-label">选择小组：</span>
                    <el-select v-model="joinGroupNum[project.id]" placeholder="请选择小组" class="group-select">
                      <el-option 
                        v-for="n in project.group_count" :key="n" :label="`第 ${n} 组`" :value="n"
                        :disabled="isGroupFull(project.id, n)"
                      >
                        <span>第 {{ n }} 组 ({{ getGroupMemberCount(project.id, n) }}/{{ getGroupCapacity(project.id, n) }})</span>
                      </el-option>
                    </el-select>
                  </div>
                  <div class="join-item">
                    <span class="join-label">选择角色：</span>
                    <el-select v-model="joinRole[project.id]" placeholder="选角色" class="role-select">
                      <el-option label="组员" value="member" />
                      <el-option label="组长" value="leader" />
                    </el-select>
                  </div>
                  <el-button 
                    type="primary" 
                    class="join-btn"
                    :disabled="!joinGroupNum[project.id] || !joinRole[project.id]" 
                    @click="handleJoin(project.id)"
                  >
                    确认加入
                  </el-button>
                </template>
              </div>
            </div>

            <div v-if="authStore.canViewAllData" class="admin-actions">
              <el-button type="primary" plain size="small" :icon="Download" @click="handleExport(project.id)">下载名单</el-button>
              <el-button type="success" plain size="small" :icon="Edit" @click="openGroupNameDialog(project)">编辑组名</el-button>
              <el-button type="warning" plain size="small" :icon="List" @click="handleShowUnassigned(project.id)">未填写名单</el-button>
              <el-button type="warning" plain size="small" :icon="ChatDotSquare" :loading="qqNotifyMap[project.id]" @click="handleQQNotify(project)">QQ群通知</el-button>
              <el-button type="danger" plain size="small" :icon="Delete" @click="handleDeleteProject(project.id)">删除此分组</el-button>
            </div>

            <el-row :gutter="16" class="groups-grid">
              <el-col :xs="24" :sm="12" :md="8" :lg="6" v-for="n in project.group_count" :key="n">
                <div class="group-card" :class="{ 'group-full': isGroupFull(project.id, n) }">
                  <div class="group-card-header">
                    <span class="group-num">{{ getGroupDisplayName(project, n) }}</span>
                    <el-tag size="small" round effect="light">
                      {{ getGroupMemberCount(project.id, n) }} / {{ getGroupCapacity(project.id, n) }}
                    </el-tag>
                  </div>
                  <div class="group-members">
                    <div v-for="member in getGroupMembers(project.id, n)" :key="member.id" class="member-item">
                      <el-avatar :size="28" :style="{ background: member.role === 'leader' ? '#FF7D00' : '#165DFF' }">
                        {{ member.student_name?.charAt(0) || '?' }}
                      </el-avatar>
                      <div class="member-info">
                        <span class="member-name">
                          {{ member.student_name }}
                          <el-tag v-if="member.role === 'leader'" size="small" type="warning" effect="dark" round class="leader-tag">组长</el-tag>
                        </span>
                        <span class="member-id">{{ member.student_student_id }}</span>
                      </div>
                    </div>
                    <div v-if="getGroupMemberCount(project.id, n) === 0" class="empty-group">
                      暂无成员
                    </div>
                  </div>
                </div>
              </el-col>
            </el-row>
          </div>
        </el-collapse-transition>
      </el-card>
    </div>

    <el-dialog 
      v-model="showCreateDialog" 
      title="新建分组项目" 
      :width="isMobile ? '100%' : '550px'" 
      :fullscreen="isMobile"
      class="modern-dialog" 
      destroy-on-close
    >
      <el-form :model="createForm" label-position="top" size="large">
        <el-form-item label="项目名称">
          <el-input v-model="createForm.name" placeholder="如：数据结构课程设计分组" />
        </el-form-item>
        
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="小组数量">
              <el-input-number v-model="createForm.group_count" :min="1" :max="50" @change="syncCapacities" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="统一每组人数">
              <el-input-number v-model="createForm.members_per_group" :min="1" :max="20" @change="syncCapacities" style="width: 100%" />
            </el-form-item>
          </el-col>
        </el-row>

        <el-divider content-position="left">每组个性化容量（可分别调整）</el-divider>
        <el-row :gutter="12">
          <el-col :xs="12" :sm="8" v-for="n in createForm.group_count" :key="'cap'+n" style="margin-bottom: 12px;">
            <div class="group-cap-item">
              <span class="cap-label">第 {{ n }} 组</span>
              <el-input-number 
                v-model="createForm.group_capacities[n - 1]" 
                :min="1" :max="50" 
                size="small" 
                controls-position="right"
                style="width: 100%"
              />
            </div>
          </el-col>
        </el-row>
        
        <el-divider content-position="left">截止时间</el-divider>
        <el-form-item label="报名截止时间（选填）">
          <el-date-picker 
            v-model="createForm.deadline" 
            type="datetime" 
            style="width: 100%"
            value-format="YYYY-MM-DD HH:mm:ss" 
            placeholder="时间截止后将禁止学生自由加入/退出" 
            :editable="false"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <div class="dialog-footer">
          <el-button @click="showCreateDialog = false">取消</el-button>
          <el-button type="primary" :loading="creating" @click="handleCreate">确认创建</el-button>
        </div>
      </template>
    </el-dialog>

    <el-dialog v-model="unassignedVisible" title="未分配名单" :width="isMobile ? '100%' : '500px'" :fullscreen="isMobile" class="modern-dialog">
      <div v-if="unassignedList.length === 0" class="empty-questions" style="text-align: center; padding: 20px; color: #86909C; background: #F7F8FA; border-radius: 6px;">
        🎉 全部学生都已加入分组
      </div>
      <el-table v-else :data="unassignedList" size="small" class="unassigned-table" max-height="400">
        <el-table-column prop="real_name" label="姓名" />
        <el-table-column prop="student_id" label="学号" />
      </el-table>
      <template #footer>
        <div class="dialog-footer">
          <el-button @click="unassignedVisible = false">关闭</el-button>
          <el-button type="primary" :icon="ChatDotSquare" :loading="qqRemindLoading" @click="handleQQRemind">QQ私聊提醒</el-button>
        </div>
      </template>
    </el-dialog>

    <el-dialog v-model="groupNameVisible" title="编辑自定义组名" :width="isMobile ? '100%' : '500px'" :fullscreen="isMobile" class="modern-dialog" destroy-on-close>
      <el-form label-position="top" size="large">
        <el-form-item v-for="n in editingProject?.group_count" :key="n" :label="`第 ${n} 组`">
          <el-input v-model="groupNameForm[n]" placeholder="留空则使用默认「第N组」" clearable />
        </el-form-item>
      </el-form>
      <template #footer>
        <div class="dialog-footer">
          <el-button @click="groupNameVisible = false">取消</el-button>
          <el-button type="primary" :loading="savingGroupNames" @click="saveGroupNames">保存</el-button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, onBeforeUnmount } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Files, ArrowDown, Delete, Download, List, Timer, ChatDotSquare, Edit } from '@element-plus/icons-vue'
import { useAuthStore } from '../stores/auth'
import api from '../api'

const authStore = useAuthStore()
const projects = ref([])
const loading = ref(false)
const showCreateDialog = ref(false)
const creating = ref(false)
const expandedProjectId = ref(null)
const projectDetails = ref({})
const joinGroupNum = ref({})
const joinRole = ref({})
const myAssignment = ref({})

// 移动端适配
const isMobile = ref(false)
const checkDevice = () => {
  isMobile.value = window.innerWidth <= 768
}

// 未填写名单
const unassignedVisible = ref(false)
const unassignedList = ref([])
const qqNotifyMap = reactive({})
const qqRemindLoading = ref(false)

// 自定义组名编辑
const groupNameVisible = ref(false)
const editingProject = ref(null)
const groupNameForm = reactive({})
const savingGroupNames = ref(false)

const createForm = reactive({
  name: '',
  group_count: 4,
  members_per_group: 6,
  group_capacities: [6, 6, 6, 6],
  deadline: '',
})

onMounted(() => {
  checkDevice()
  window.addEventListener('resize', checkDevice)
  loadProjects()
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', checkDevice)
})

function syncCapacities() {
  const diff = createForm.group_count - createForm.group_capacities.length
  if (diff > 0) {
    for (let i = 0; i < diff; i++) {
      createForm.group_capacities.push(createForm.members_per_group)
    }
  } else if (diff < 0) {
    createForm.group_capacities.splice(createForm.group_count)
  }
}

async function loadProjects() {
  loading.value = true
  try {
    const res = await api.get('/api/group-projects')
    projects.value = res.data
    for (const p of projects.value) {
      try {
        const detail = await api.get(`/api/group-projects/${p.id}`)
        projectDetails.value[p.id] = detail.data
      } catch {}
    }
    if (!authStore.canViewAllData && authStore.user) {
      for (const p of projects.value) {
        const detail = projectDetails.value[p.id]
        if (detail) {
          for (const group of detail.groups) {
            for (const m of group) {
              if (m.student_id === authStore.user.id) {
                myAssignment.value[p.id] = m
              }
            }
          }
        }
      }
    }
  } catch {
    ElMessage.error('加载分组失败')
  } finally {
    loading.value = false
  }
}

function toggleProject(id) {
  expandedProjectId.value = expandedProjectId.value === id ? null : id
}

function getGroupMembers(projectId, groupNum) {
  const detail = projectDetails.value[projectId]
  if (!detail) return []
  return detail.groups[groupNum - 1] || []
}

function getGroupMemberCount(projectId, groupNum) {
  return getGroupMembers(projectId, groupNum).length
}

function getGroupCapacity(projectId, groupNum) {
  const detail = projectDetails.value[projectId]
  if (!detail) return 0
  if (detail.group_capacities && detail.group_capacities[groupNum - 1]) {
    return detail.group_capacities[groupNum - 1]
  }
  return detail.members_per_group || 0
}

function isGroupFull(projectId, groupNum) {
  return getGroupMemberCount(projectId, groupNum) >= getGroupCapacity(projectId, groupNum)
}

function formatTime(t) {
  if (!t) return ''
  return new Date(t).toLocaleString('zh-CN', {
    year: 'numeric', month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit'
  })
}

function isExpired(deadline) {
  if (!deadline) return false
  return new Date() > new Date(deadline)
}

async function handleCreate() {
  if (!createForm.name.trim()) return ElMessage.warning('请输入项目名称')
  creating.value = true
  try {
    await api.post('/api/group-projects', {
      name: createForm.name,
      group_count: createForm.group_count,
      members_per_group: createForm.members_per_group,
      group_capacities: createForm.group_capacities.slice(0, createForm.group_count),
      deadline: createForm.deadline || undefined,
    })
    ElMessage.success('分组项目已创建')
    showCreateDialog.value = false
    createForm.name = ''
    createForm.group_count = 4
    createForm.members_per_group = 6
    createForm.group_capacities = [6, 6, 6, 6]
    createForm.deadline = ''
    loadProjects()
  } catch (err) {
    ElMessage.error(err.response?.data?.detail || '创建失败')
  } finally {
    creating.value = false
  }
}

async function handleJoin(projectId) {
  try {
    await api.post(`/api/group-projects/${projectId}/join`, {
      group_number: joinGroupNum.value[projectId],
      role: joinRole.value[projectId],
    })
    ElMessage.success('加入成功')
    joinGroupNum.value[projectId] = null
    joinRole.value[projectId] = null
    loadProjects()
  } catch (err) {
    ElMessage.error(err.response?.data?.detail || '加入失败')
  }
}

async function handleLeave(projectId) {
  try {
    await ElMessageBox.confirm('确定要退出当前小组吗？', '退出确认', {
      confirmButtonText: '确定退出',
      cancelButtonText: '取消',
      type: 'warning'
    })
    await api.delete(`/api/group-projects/${projectId}/leave`)
    ElMessage.success('已退出小组')
    myAssignment.value[projectId] = null
    loadProjects()
  } catch (err) {
    if (err !== 'cancel' && err !== 'close') {
      ElMessage.error(err.response?.data?.detail || '退出失败')
    }
  }
}

async function handleDeleteProject(projectId) {
  try {
    await ElMessageBox.confirm('确定要删除此分组项目及所有数据吗？', '删除确认', {
      confirmButtonText: '确定删除',
      cancelButtonText: '取消',
      type: 'warning'
    })
    await api.delete(`/api/group-projects/${projectId}`)
    ElMessage.success('已删除')
    loadProjects()
  } catch (err) {
    if (err !== 'cancel' && err !== 'close') {
      ElMessage.error(err.response?.data?.detail || '删除失败')
    }
  }
}

async function handleExport(projectId) {
  try {
    const res = await api.get(`/api/group-projects/${projectId}/export`, { responseType: 'blob' })
    const url = window.URL.createObjectURL(new Blob([res.data]))
    const link = document.createElement('a')
    link.href = url
    link.download = decodeURIComponent(res.headers['content-disposition']?.match(/filename\*=UTF-8''(.+)/)?.[1] || '分组名单.xlsx')
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    window.URL.revokeObjectURL(url)
    ElMessage.success('下载成功')
  } catch (err) {
    ElMessage.error(err.response?.data?.detail || '下载失败')
  }
}

async function handleShowUnassigned(projectId) {
  unassignedVisible.value = true
  unassignedList.value = []
  try {
    const res = await api.get(`/api/group-projects/${projectId}/unassigned`)
    unassignedList.value = res.data
  } catch (err) {
    ElMessage.error(err.response?.data?.detail || '加载失败')
  }
}

async function handleQQNotify(project) {
  try {
    await ElMessageBox.confirm(`确定向 QQ 群发送分组项目「${project.name}」的通知吗？`, 'QQ群通知确认', {
      confirmButtonText: '发送', cancelButtonText: '取消', type: 'warning'
    })
  } catch { return }
  qqNotifyMap[project.id] = true
  try {
    const res = await api.post(`/api/qq/group-project/${project.id}/notify`)
    ElMessage.success(res.data.message || 'QQ群通知已发送')
  } catch (err) {
    ElMessage.error(err.response?.data?.detail || '发送失败')
  } finally {
    qqNotifyMap[project.id] = false
  }
}

async function handleQQRemind() {
  const project = projects.value.find(p => p.id === expandedProjectId.value)
  if (!project) return
  try {
    await ElMessageBox.confirm(
      '将向所有未加入分组的学生发送 QQ 私聊提醒。确定发送吗？',
      'QQ私聊提醒确认',
      { confirmButtonText: '发送', cancelButtonText: '取消', type: 'warning' }
    )
  } catch { return }
  qqRemindLoading.value = true
  try {
    const res = await api.post(`/api/qq/group-project/${project.id}/remind`)
    const info = res.data
    ElMessage.success(`QQ私聊提醒完成：成功 ${info.sent || 0} 人，失败 ${info.failed || 0} 人`)
  } catch (err) {
    ElMessage.error(err.response?.data?.detail || '发送失败')
  } finally {
    qqRemindLoading.value = false
  }
}

function getGroupDisplayName(project, groupNum) {
  if (project.group_names && project.group_names[String(groupNum)]) {
    return project.group_names[String(groupNum)]
  }
  return `第 ${groupNum} 组`
}

function openGroupNameDialog(project) {
  editingProject.value = project
  for (const key of Object.keys(groupNameForm)) {
    delete groupNameForm[key]
  }
  if (project.group_names) {
    Object.assign(groupNameForm, project.group_names)
  }
  groupNameVisible.value = true
}

async function saveGroupNames() {
  if (!editingProject.value) return
  savingGroupNames.value = true
  try {
    const nonEmpty = {}
    for (let n = 1; n <= editingProject.value.group_count; n++) {
      if (groupNameForm[n] && groupNameForm[n].trim()) {
        nonEmpty[String(n)] = groupNameForm[n].trim()
      }
    }
    await api.put(`/api/group-projects/${editingProject.value.id}`, { group_names: Object.keys(nonEmpty).length > 0 ? nonEmpty : null })
    ElMessage.success('组名已更新')
    groupNameVisible.value = false
    loadProjects()
  } catch (err) {
    ElMessage.error(err.response?.data?.detail || '更新失败')
  } finally {
    savingGroupNames.value = false
  }
}
</script>

<style scoped>
.group-manage-container {
  padding: 0;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}

.header-left {
  display: flex;
  align-items: center;
}

.title-indicator {
  width: 4px;
  height: 18px;
  background-color: #165DFF;
  border-radius: 2px;
  margin-right: 12px;
}

.page-title {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  color: #1D2129;
}

/* 项目卡片 */
.project-card {
  margin-bottom: 16px;
}

.modern-card {
  border: none;
  border-radius: 8px;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.04);
}

.project-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  cursor: pointer;
  user-select: none;
}

.project-info {
  display: flex;
  align-items: center;
  gap: 12px;
  flex: 1;
}

.project-icon {
  font-size: 28px;
  color: #165DFF;
  flex-shrink: 0;
}

.project-text-box {
  flex: 1;
}

.project-name {
  margin: 0 0 6px 0;
  font-size: 16px;
  font-weight: 600;
  color: #1D2129;
}

.project-meta {
  font-size: 13px;
  color: #86909C;
  line-height: 1.5;
}

.deadline-text {
  margin-top: 4px;
  display: block;
}

.deadline-text.is-expired {
  color: #F53F3F;
}

.project-actions-header {
  display: flex;
  align-items: center;
}

.header-progress {
  width: 100px;
  margin-right: 16px;
}

.arrow-rotate {
  transform: rotate(180deg);
  transition: transform 0.3s;
}

.project-detail {
  margin-top: 8px;
}

/* 学生加入区域 */
.student-join-area {
  margin-bottom: 20px;
}

.my-group-info {
  margin-bottom: 8px;
}

.leave-btn {
  margin-top: 12px;
}

/* Flex 配合 Wrap 使表单具备响应性 */
.join-area {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.join-item {
  display: flex;
  align-items: center;
}

.join-label {
  font-size: 14px;
  color: #4E5969;
  white-space: nowrap;
}

.group-select {
  width: 140px;
}

.role-select {
  width: 110px;
}

.admin-actions {
  margin-bottom: 16px;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.admin-actions .el-button {
  margin-left: 0 !important;
}

/* 小组网格 */
.groups-grid {
  margin-top: 8px;
}

.group-card {
  background: #F7F8FA;
  border-radius: 8px;
  padding: 12px;
  margin-bottom: 16px;
  min-height: 120px;
  border: 1px solid #E5E6EB;
  transition: all 0.2s;
}

.group-card:hover {
  border-color: #165DFF;
}

.group-card.group-full {
  background: #FFF7E6;
  border-color: #FFD591;
}

.group-card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
  padding-bottom: 8px;
  border-bottom: 1px solid #E5E6EB;
}

.group-num {
  font-weight: 600;
  font-size: 14px;
  color: #1D2129;
}

.group-members {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.member-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 4px 0;
}

.member-info {
  display: flex;
  flex-direction: column;
  line-height: 1.4;
}

.member-name {
  font-size: 13px;
  font-weight: 500;
  color: #1D2129;
  display: flex;
  align-items: center;
}

.leader-tag {
  margin-left: 6px;
  transform: scale(0.85);
}

.member-id {
  font-size: 12px;
  color: #86909C;
}

.empty-group {
  color: #C9CDD4;
  font-size: 13px;
  text-align: center;
  padding: 8px 0;
}

.join-closed-hint {
  width: 100%;
}

:deep(.el-input__wrapper.is-focus),
:deep(.el-select .el-input.is-focus .el-input__wrapper) {
  box-shadow: 0 0 0 1px #165DFF inset !important;
}

.group-cap-item {
  text-align: center;
  background: #F7F8FA;
  padding: 8px;
  border-radius: 6px;
}

.cap-label {
  display: block;
  font-size: 12px;
  color: #86909C;
  margin-bottom: 6px;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}

/* =======================================
   移动端响应式适配
   ======================================= */
@media screen and (max-width: 768px) {
  /* 头部区域改成垂直排列或允许换行 */
  .page-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 16px;
  }

  .header-actions {
    width: 100%;
  }
  
  .header-actions .header-btn {
    width: 100%;
  }

  .project-header {
    flex-direction: column;
    align-items: flex-start;
  }
  
  .project-actions-header {
    margin-top: 16px;
    width: 100%;
    justify-content: space-between;
  }
  
  .header-progress {
    width: 70%; /* 移动端进度条占据大部分空间 */
  }

  /* 学生加入表单铺满宽度 */
  .join-area {
    flex-direction: column;
    align-items: stretch;
  }

  .join-item {
    justify-content: space-between;
  }

  .group-select,
  .role-select {
    width: 60%;
    flex: 1;
    margin-left: 12px;
  }
  
  .join-btn {
    width: 100%;
    margin-top: 8px;
  }

  .leave-btn {
    width: 100%;
  }

  .admin-actions {
    display: flex;
    justify-content: space-between;
  }

  .admin-actions .el-button {
    flex: 1;
  }

  /* 移除弹窗在手机上的 margin，彻底融入全屏 */
  :deep(.modern-dialog) {
    margin: 0 !important;
  }
  
  :deep(.modern-dialog .el-dialog__body) {
    padding: 15px !important;
  }

  .dialog-footer {
    justify-content: space-between;
  }
  
  .dialog-footer .el-button {
    flex: 1;
    margin-left: 0 !important;
  }
}
</style>