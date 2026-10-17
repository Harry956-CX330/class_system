<template>
  <div class="user-manage-container">
    <el-card class="page-card" shadow="never">
      <div class="page-header">
        <div class="header-left">
          <div class="title-indicator"></div>
          <h3 class="page-title">用户管理</h3>
        </div>
        <div class="header-actions">
          <el-button type="success" plain :icon="Upload" @click="openImportDialog">批量导入</el-button>
          <el-button type="primary" :icon="Plus" @click="openCreateDialog">添加学生</el-button>
        </div>
      </div>

      <el-table 
        v-if="!isMobile"
        :data="users" 
        style="width: 100%" 
        v-loading="loading"
        class="custom-table"
        :header-cell-style="{ background: '#F7F8FA', color: '#4E5969', fontWeight: '500' }"
      >
        <el-table-column prop="username" label="系统账号" min-width="120" />
        <el-table-column prop="real_name" label="真实姓名" min-width="120">
          <template #default="{ row }">
            <span class="user-name">{{ row.real_name || '-' }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="student_id" label="学号" min-width="140">
          <template #default="{ row }">
            <span class="id-text">{{ row.student_id || '-' }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="political_status" label="政治面貌" width="120">
          <template #default="{ row }">
            <el-tag size="small" type="info" effect="plain" round v-if="row.political_status">
              {{ row.political_status }}
            </el-tag>
            <span v-else style="color: #C9CDD4">-</span>
          </template>
        </el-table-column>
        <el-table-column prop="email" label="邮箱" min-width="180" show-overflow-tooltip>
          <template #default="{ row }">
            <span v-if="row.email" style="color: var(--el-color-primary);">{{ row.email }}</span>
            <span v-else style="color: #C9CDD4">未填写</span>
          </template>
        </el-table-column>
        <el-table-column prop="qq_number" label="QQ号" min-width="130">
          <template #default="{ row }">
            <span v-if="row.qq_number" style="color: var(--el-color-primary);">{{ row.qq_number }}</span>
            <span v-else style="color: #C9CDD4">未填写</span>
          </template>
        </el-table-column>
        <el-table-column prop="role" label="角色身份" width="140" align="center">
          <template #default="{ row }">
            <el-tag v-if="row.role === 'admin'" type="danger" effect="light" round size="small">
              管理员
            </el-tag>
            <div v-else class="role-cell">
              <el-tag :type="row.is_class_leader ? 'warning' : 'primary'" effect="light" round size="small">
                {{ row.is_class_leader ? '班干' : '学生' }}
              </el-tag>
              <el-button 
                v-if="row.role !== 'admin'"
                size="small" 
                type="warning" 
                link 
                class="leader-toggle-btn"
                @click="toggleClassLeader(row)"
              >
                {{ row.is_class_leader ? '取消班干' : '设为班干' }}
              </el-button>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="dorm" label="宿舍" width="100">
          <template #default="{ row }">
            <span v-if="row.dorm" style="font-size: 13px">{{ row.dorm }}</span>
            <span v-else style="color: #C9CDD4; font-size: 12px">未设置</span>
          </template>
        </el-table-column>
        <el-table-column label="宿舍长" width="100" align="center">
          <template #default="{ row }">
            <div v-if="row.role !== 'admin'" class="role-cell">
              <el-tag :type="row.is_dorm_leader ? 'success' : 'info'" effect="light" round size="small">
                {{ row.is_dorm_leader ? '是' : '否' }}
              </el-tag>
              <el-button 
                size="small" 
                type="success" 
                link 
                class="leader-toggle-btn"
                @click="toggleDormLeader(row)"
              >
                {{ row.is_dorm_leader ? '取消' : '设为宿舍长' }}
              </el-button>
            </div>
            <span v-else style="color: #C9CDD4">-</span>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="注册时间" width="180">
          <template #default="{ row }">
            <span class="time-text">{{ new Date(row.created_at).toLocaleString('zh-CN', { hour12: false }) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="180" fixed="right">
          <template #default="{ row }">
            <el-button v-if="authStore.user?.role==='admin'" size="small" type="primary" link @click="issueResetCode(row)">重置验证码</el-button>
            <el-button v-if="row.role !== 'admin'" size="small" type="primary" link :icon="Edit" @click="openEditDialog(row)">编辑</el-button>
            <el-button v-if="row.role !== 'admin'" size="small" type="danger" link :icon="Delete" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <div v-else class="mobile-list" v-loading="loading">
        <el-card v-for="row in users" :key="row.id" class="mobile-user-card" shadow="sm">
          <div class="card-header">
            <div class="user-title">
              <span class="user-name">{{ row.real_name || '未命名' }}</span>
              <span class="user-account">({{ row.username }})</span>
            </div>
            <el-tag v-if="row.role === 'admin'" type="danger" effect="light" round size="small">
              管理员
            </el-tag>
            <el-tag v-else :type="row.is_class_leader ? 'warning' : 'primary'" effect="light" round size="small">
              {{ row.is_class_leader ? '班干' : '学生' }}
            </el-tag>
          </div>
          <div class="card-body">
            <div class="info-row">
              <span class="label">学号：</span>
              <span class="value id-text">{{ row.student_id || '-' }}</span>
            </div>
            <div class="info-row">
              <span class="label">政治面貌：</span>
              <span class="value">
                <el-tag size="small" type="info" effect="plain" round v-if="row.political_status">{{ row.political_status }}</el-tag>
                <span v-else style="color: #C9CDD4">-</span>
              </span>
            </div>
            <div class="info-row">
              <span class="label">邮箱：</span>
              <span class="value" :class="{'highlight-text': row.email, 'empty-text': !row.email}">{{ row.email || '未填写' }}</span>
            </div>
            <div class="info-row">
              <span class="label">QQ号：</span>
              <span class="value" :class="{'highlight-text': row.qq_number, 'empty-text': !row.qq_number}">{{ row.qq_number || '未填写' }}</span>
            </div>
            <div class="info-row">
              <span class="label">宿舍：</span>
              <span class="value">{{ row.dorm || '未设置' }}</span>
            </div>
            <div class="info-row">
              <span class="label">注册时间：</span>
              <span class="value time-text">{{ new Date(row.created_at).toLocaleString('zh-CN', { hour12: false }) }}</span>
            </div>
          </div>
          <div class="card-footer">
            <el-button v-if="authStore.user?.role==='admin'" size="small" type="primary" plain @click="issueResetCode(row)">重置验证码</el-button>
            <template v-if="row.role !== 'admin'">
            <el-button size="small" type="primary" plain :icon="Edit" @click="openEditDialog(row)">编辑信息</el-button>
            <el-button size="small" type="warning" plain @click="toggleClassLeader(row)">
              {{ row.is_class_leader ? '取消班干' : '设为班干' }}
            </el-button>
            <el-button size="small" type="success" plain @click="toggleDormLeader(row)">
              {{ row.is_dorm_leader ? '取消宿舍长' : '设为宿舍长' }}
            </el-button>
            <el-button size="small" type="danger" plain :icon="Delete" @click="handleDelete(row)">移除用户</el-button>
            </template>
          </div>
        </el-card>
        <el-empty v-if="users.length === 0" description="暂无用户数据" />
      </div>
    </el-card>

    <el-dialog 
      v-model="dialogVisible" 
      :title="isEdit ? '编辑学生信息' : '添加新学生'" 
      :width="isMobile ? '100%' : '480px'" 
      :fullscreen="isMobile"
      class="modern-dialog flex-dialog" 
      destroy-on-close
    >
      <div class="dialog-scroll-body">
        <el-form 
          :model="userForm" 
          :label-width="isMobile ? 'auto' : '90px'" 
          :label-position="isMobile ? 'top' : 'right'"
          size="large"
        >
          <el-form-item label="系统账号">
            <el-input v-model="userForm.username" :disabled="isEdit" placeholder="用于登录的账号 (如: stu001)" />
          </el-form-item>
          <el-form-item v-if="!isEdit" label="初始密码">
            <el-input v-model="userForm.password" type="password" show-password placeholder="请设置初始密码" />
          </el-form-item>
          <el-form-item label="真实姓名">
            <el-input v-model="userForm.real_name" placeholder="请输入真实姓名" />
          </el-form-item>
          <el-form-item label="学号/工号">
            <el-input v-model="userForm.student_id" placeholder="请输入学号" />
          </el-form-item>
          <el-form-item label="政治面貌">
            <el-select v-model="userForm.political_status" placeholder="请选择" style="width: 100%">
              <el-option label="群众" value="群众" />
              <el-option label="共青团员" value="共青团员" />
              <el-option label="预备党员" value="预备党员" />
              <el-option label="中共党员" value="中共党员" />
              <el-option label="其他" value="其他" />
            </el-select>
          </el-form-item>
          <el-form-item label="电子邮箱">
            <el-input v-model="userForm.email" placeholder="请输入邮箱等联系方式" />
          </el-form-item>
          <el-form-item label="QQ号">
            <el-input v-model="userForm.qq_number" placeholder="用于接收QQ提醒消息" />
          </el-form-item>
          <el-form-item label="手机号">
            <el-input v-model="userForm.phone" placeholder="请输入手机号码" />
          </el-form-item>
          <el-form-item label="宿舍">
            <el-input v-model="userForm.dorm" placeholder="如 B3-205" />
          </el-form-item>
          <el-form-item label="班级职务">
            <el-input v-model="userForm.class_position" placeholder="如 班长、团支书" />
          </el-form-item>
          <el-form-item label="宿舍长">
            <el-switch v-model="userForm.is_dorm_leader" active-text="是" inactive-text="否" />
          </el-form-item>
        </el-form>
      </div>
      <template #footer>
        <div class="dialog-footer">
          <el-button @click="dialogVisible = false">取消</el-button>
          <el-button type="primary" @click="handleSubmit">{{ isEdit ? '保存更改' : '确认添加' }}</el-button>
        </div>
      </template>
    </el-dialog>

    <el-dialog 
      v-model="importVisible" 
      title="批量导入用户" 
      :width="isMobile ? '100%' : '600px'" 
      :fullscreen="isMobile"
      class="modern-dialog flex-dialog" 
      destroy-on-close
    >
      <div class="dialog-scroll-body" style="padding-top: 5px;">
        <el-tabs v-model="importActiveTab" class="import-tabs">
          <el-tab-pane label="Excel / CSV 导入" name="file">
            <div class="upload-wrapper">
              <div class="template-download">
                <span class="hint-text">请先下载标准数据模板，按格式填写后上传：</span>
                <el-button type="primary" link :icon="Download" @click="downloadTemplate" class="download-btn">下载标准模板</el-button>
              </div>
              
              <el-upload
                ref="uploadRef"
                class="drag-upload"
                drag
                :auto-upload="false"
                :limit="1"
                accept=".xlsx,.xls,.csv"
                :on-change="handleFileChange"
                :on-remove="handleFileRemove"
              >
                <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
                <div class="el-upload__text">
                  将文件拖到此处，或 <em>点击上传</em>
                </div>
                <template #tip>
                  <div class="el-upload__tip">仅支持 .xlsx, .xls, .csv 格式文件</div>
                </template>
              </el-upload>

              <div class="action-row">
                <el-button type="primary" :loading="importLoading" :disabled="!selectedFile" @click="handleFileImport" style="width: 100%" size="large">
                  开始导入数据
                </el-button>
              </div>
            </div>
          </el-tab-pane>

          <el-tab-pane label="JSON 数据导入" name="json">
            <div class="json-wrapper">
              <div class="json-hint">
                请粘贴合法的 JSON 数组，必须包含：<code>username</code>, <code>real_name</code>, <code>student_id</code>, <code>political_status</code>, <code>email</code>, <code>qq_number</code>, <code>password</code>
              </div>
              <el-input 
                v-model="importJson" 
                type="textarea" 
                :rows="isMobile ? 12 : 8" 
                class="json-input"
                placeholder='[
  {
    "username": "stu1",
    "real_name": "张三",
    "student_id": "2024001",
    "political_status": "共青团员",
    "password": "password123"
  }
]' 
              />
              <div class="action-row">
                <el-button type="primary" :loading="importLoading" :disabled="!importJson.trim()" @click="handleImport" style="width: 100%" size="large">
                  执行 JSON 导入
                </el-button>
              </div>
            </div>
          </el-tab-pane>
        </el-tabs>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, onBeforeUnmount } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Upload, UploadFilled, Download, Edit, Delete } from '@element-plus/icons-vue'
import api from '../api'
import { useAuthStore } from '../stores/auth'
const authStore=useAuthStore()
async function issueResetCode(row) {
  try {
    await ElMessageBox.confirm(`为 ${row.real_name||row.username} 生成新的重置验证码？旧验证码将失效。请先核实本人身份。`,'生成验证码')
    const {data}=await api.post(`/api/users/${row.id}/reset-code`)
    await ElMessageBox.alert(`验证码：${data.code}。有效期 10 分钟，仅可使用一次。请通过可靠方式告知本人。`,'密码重置验证码',{confirmButtonText:'已记录',closeOnClickModal:false})
  } catch(error) { if(error?.response)ElMessage.error(error.response.data.detail||'生成失败') }
}

const users = ref([])
const loading = ref(false)

// 响应式状态探测
const isMobile = ref(false)
const checkMobile = () => {
  isMobile.value = window.innerWidth <= 768
}

// 弹窗与 Tab 状态
const dialogVisible = ref(false)
const importVisible = ref(false)
const importActiveTab = ref('file')
const importLoading = ref(false)

// 数据绑定
const importJson = ref('')
const uploadRef = ref(null)
const selectedFile = ref(null)
const isEdit = ref(false)
const editId = ref(null)

const userForm = reactive({
  username: '',
  password: '',
  real_name: '',
  student_id: '',
  political_status: '',
  email: '',
  qq_number: '',
  phone: '',
  dorm: '',
  class_position: '',
  is_dorm_leader: false,
})

onMounted(() => {
  checkMobile()
  window.addEventListener('resize', checkMobile)
  loadUsers()
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', checkMobile)
})

async function loadUsers() {
  loading.value = true
  try {
    const res = await api.get('/api/users')
    users.value = res.data
  } catch {
    ElMessage.error('加载用户失败')
  } finally {
    loading.value = false
  }
}

function openCreateDialog() {
  isEdit.value = false
  editId.value = null
  userForm.username = ''
  userForm.password = ''
  userForm.real_name = ''
  userForm.student_id = ''
  userForm.political_status = ''
  userForm.email = ''
  userForm.qq_number = ''
  userForm.phone = ''
  userForm.dorm = ''
  userForm.class_position = ''
  userForm.is_dorm_leader = false
  dialogVisible.value = true
}

function openEditDialog(row) {
  isEdit.value = true
  editId.value = row.id
  userForm.username = row.username
  userForm.password = ''
  userForm.real_name = row.real_name
  userForm.student_id = row.student_id
  userForm.political_status = row.political_status
  userForm.email = row.email
  userForm.qq_number = row.qq_number || ''
  userForm.phone = row.phone || ''
  userForm.dorm = row.dorm || ''
  userForm.class_position = row.class_position || ''
  userForm.is_dorm_leader = !!row.is_dorm_leader
  dialogVisible.value = true
}

function openImportDialog() {
  importJson.value = ''
  selectedFile.value = null
  importActiveTab.value = 'file'
  if (uploadRef.value) {
    uploadRef.value.clearFiles()
  }
  importVisible.value = true
}

function handleFileChange(file) {
  selectedFile.value = file
}

function handleFileRemove() {
  selectedFile.value = null
}

function downloadTemplate() {
  window.open('/api/users/template', '_blank')
}

async function handleFileImport() {
  if (!selectedFile.value) {
    return ElMessage.warning('请先选择要导入的文件')
  }
  importLoading.value = true
  try {
    const formData = new FormData()
    formData.append('file', selectedFile.value.raw)
    const res = await api.post('/api/users/import-file', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    ElMessage.success(`导入完成: 成功添加 ${res.data.created} 名用户`)
    if (res.data.errors && res.data.errors.length) {
      ElMessage.warning(`部分失败: ${res.data.errors.join(', ')}`)
    }
    importVisible.value = false
    selectedFile.value = null
    loadUsers()
  } catch (err) {
    ElMessage.error(err.response?.data?.detail || '文件导入失败')
  } finally {
    importLoading.value = false
  }
}

async function handleSubmit() {
  // 简易校验
  if (!userForm.username || !userForm.real_name) {
    return ElMessage.warning('请至少填写用户名和真实姓名')
  }

  try {
    if (isEdit.value) {
      await api.put(`/api/users/${editId.value}`, {
        real_name: userForm.real_name,
        student_id: userForm.student_id,
        political_status: userForm.political_status,
        email: userForm.email,
        qq_number: userForm.qq_number,
        phone: userForm.phone,
        dorm: userForm.dorm,
        class_position: userForm.class_position,
        is_dorm_leader: userForm.is_dorm_leader,
      })
      ElMessage.success('信息更新成功')
    } else {
      if (!userForm.password) return ElMessage.warning('请设置初始密码')
      await api.post('/api/users', { ...userForm, role: 'student' })
      ElMessage.success('用户添加成功')
    }
    dialogVisible.value = false
    loadUsers()
  } catch (err) {
    ElMessage.error(err.response?.data?.detail || '操作失败')
  }
}

async function handleImport() {
  try {
    const items = JSON.parse(importJson.value)
    if (!Array.isArray(items)) return ElMessage.warning('解析失败：请输入有效的 JSON 数组')
    
    importLoading.value = true
    const res = await api.post('/api/users/import', items)
    ElMessage.success(`导入完成: 成功添加 ${res.data.created} 名用户`)
    if (res.data.errors.length) {
      ElMessage.warning(`部分失败: ${res.data.errors.join(', ')}`)
    }
    importVisible.value = false
    loadUsers()
  } catch (err) {
    if (err instanceof SyntaxError) {
      ElMessage.error('JSON 格式错误，请检查语法')
    } else {
      ElMessage.error(err.response?.data?.detail || '导入失败')
    }
  } finally {
    importLoading.value = false
  }
}

async function toggleClassLeader(row) {
  try {
    const newValue = !row.is_class_leader
    await api.put(`/api/users/${row.id}`, { is_class_leader: newValue })
    row.is_class_leader = newValue
    ElMessage.success(newValue ? '已设为班干' : '已取消班干')
  } catch (err) {
    ElMessage.error(err.response?.data?.detail || '操作失败')
  }
}

async function toggleDormLeader(row) {
  try {
    const newValue = !row.is_dorm_leader
    await api.put(`/api/users/${row.id}`, { is_dorm_leader: newValue })
    row.is_dorm_leader = newValue
    ElMessage.success(newValue ? '已设为宿舍长' : '已取消宿舍长')
  } catch (err) {
    ElMessage.error(err.response?.data?.detail || '操作失败')
  }
}

async function handleDelete(row) {
  try {
    await ElMessageBox.confirm(`确定要移除学生 "${row.real_name || row.username}" 吗？该操作不可撤销。`, '删除确认', { 
      confirmButtonText: '确定删除',
      cancelButtonText: '取消',
      type: 'warning' 
    })
    await api.delete(`/api/users/${row.id}`)
    ElMessage.success('用户已删除')
    loadUsers()
  } catch {}
}
</script>

<style scoped>
/* 容器与卡片 */
.user-manage-container {
  padding: 0;
}

.page-card {
  border: none;
  border-radius: 8px;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.05);
  min-height: calc(100vh - 120px);
}

/* 顶部标题与操作区 */
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
  color: var(--el-text-color-primary);
}

.header-actions {
  display: flex;
  gap: 12px;
}

/* ================= 移动端卡片视图 ================= */
.mobile-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.mobile-user-card {
  border-radius: 8px;
  border: 1px solid #E5E6EB;
}

.mobile-user-card .card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
  padding-bottom: 12px;
  border-bottom: 1px dashed #F2F3F5;
}

.user-title {
  display: flex;
  align-items: baseline;
  gap: 6px;
}

.user-account {
  font-size: 13px;
  color: var(--el-text-color-secondary);
}

.mobile-user-card .card-body {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.info-row {
  display: flex;
  align-items: flex-start;
  font-size: 13px;
  line-height: 1.5;
}

.info-row .label {
  color: var(--el-text-color-secondary);
  width: 70px;
  flex-shrink: 0;
}

.info-row .value {
  color: var(--el-text-color-regular);
  flex: 1;
  word-break: break-all;
}

.highlight-text {
  color: var(--el-color-primary) !important;
}

.empty-text {
  color: #C9CDD4 !important;
}

.mobile-user-card .card-footer {
  margin-top: 16px;
  padding-top: 12px;
  border-top: 1px solid #F2F3F5;
  display: flex;
  flex-wrap: wrap; /* 防止窄屏幕按钮被过度挤压 */
  gap: 10px;
}

.mobile-user-card .card-footer .el-button {
  margin-left: 0 !important;
  flex: 1;
  min-width: 80px; /* 保证文字不换行 */
}

/* 班干角色切换样式 */
.role-cell {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
}

.leader-toggle-btn {
  font-size: 12px;
  padding: 0;
}

/* 表格内文字优化 */
.user-name {
  font-weight: 500;
  color: var(--el-text-color-primary);
}

.id-text {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
  color: var(--el-text-color-regular);
}

.time-text {
  font-size: 13px;
  color: var(--el-text-color-secondary);
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}

/* 去除表格底边框 */
:deep(.custom-table::before) {
  display: none;
}

/* 全屏弹窗滚动结构优化 */
:deep(.flex-dialog) {
  display: flex;
  flex-direction: column;
}

:deep(.flex-dialog .el-dialog__body) {
  flex: 1;
  overflow: hidden;
  padding: 0;
  display: flex;
  flex-direction: column;
}

.dialog-scroll-body {
  flex: 1;
  overflow-y: auto;
  padding: 16px 20px;
}

/* 弹窗底部操作区 */
.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}

.dialog-footer .el-button {
  margin-left: 0 !important;
}

/* 导入弹窗专属样式 */
.import-tabs {
  margin-top: -10px;
}

:deep(.import-tabs .el-tabs__item) {
  font-size: 15px;
}

.upload-wrapper, .json-wrapper {
  padding: 10px 0;
}

.template-download {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background-color: var(--el-color-primary-light-9);
  padding: 12px 16px;
  border-radius: 6px;
  margin-bottom: 20px;
  color: var(--el-color-primary);
  font-size: 14px;
}

.drag-upload {
  margin-bottom: 24px;
}

:deep(.drag-upload .el-upload-dragger) {
  background-color: var(--surface-soft);
  border-color: #E5E6EB;
  transition: all 0.3s;
  width: 100%;
}

:deep(.drag-upload .el-upload) {
  width: 100%;
}

:deep(.drag-upload .el-upload-dragger:hover) {
  background-color: var(--el-color-primary-light-9);
  border-color: #165DFF;
}

.json-hint {
  font-size: 13px;
  color: var(--el-text-color-secondary);
  margin-bottom: 12px;
  line-height: 1.6;
}

.json-hint code {
  background: var(--el-bg-color-page);
  padding: 2px 6px;
  border-radius: 4px;
  color: #F53F3F;
  font-family: monospace;
}

.json-input {
  margin-bottom: 24px;
}

:deep(.json-input .el-textarea__inner) {
  font-family: Consolas, Monaco, monospace;
  background-color: var(--surface-soft);
  font-size: 13px;
  color: var(--el-text-color-regular);
}

.action-row {
  margin-top: 10px;
}

/* 输入框聚焦效果统一 */
:deep(.el-input__wrapper.is-focus),
:deep(.el-textarea__inner:focus) {
  box-shadow: 0 0 0 1px #165DFF inset !important;
}

/* =======================================
   移动端响应式适配 (Media Queries)
   ======================================= */
@media screen and (max-width: 768px) {
  /* 顶部导航和按钮区堆叠 */
  .page-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 16px;
  }
  
  .header-actions {
    width: 100%;
    display: flex;
    justify-content: space-between;
    gap: 8px;
  }

  .header-actions .el-button {
    flex: 1;
    margin-left: 0 !important;
  }

  /* 移除弹窗在手机上的 margin，彻底融入全屏 */
  :deep(.modern-dialog) {
    margin: 0 !important;
    height: 100vh !important;
  }
  
  .dialog-scroll-body {
    padding: 16px 15px;
  }

  /* 弹窗底部按钮在手机上均分宽度 */
  .dialog-footer {
    justify-content: space-between;
  }
  
  .dialog-footer .el-button {
    flex: 1;
  }

  /* 导入模板提示框在手机端垂直排版 */
  .template-download {
    flex-direction: column;
    align-items: flex-start;
    gap: 8px;
  }

  .download-btn {
    padding-left: 0;
  }
}
</style>
