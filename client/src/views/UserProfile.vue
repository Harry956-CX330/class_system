<template>
  <div class="profile-container">
    <el-card class="page-card" shadow="never">
      <!-- 顶部标题栏 -->
      <div class="page-header">
        <div class="header-left">
          <div class="title-indicator"></div>
          <h3 class="page-title">个人中心</h3>
        </div>
        <div class="header-actions" v-if="!editing">
          <el-button type="primary" plain :icon="Edit" @click="startEdit">
            编辑资料
          </el-button>
          <el-button type="warning" plain :icon="Lock" @click="openPasswordDialog">
            修改密码
          </el-button>
        </div>
      </div>

      <!-- 用户身份展示区 (常驻) -->
      <div class="user-identity">
        <el-avatar :size="isMobile ? 64 : 80" class="user-avatar">
          {{ (authStore.user?.real_name || authStore.user?.username)?.charAt(0) || 'U' }}
        </el-avatar>
        <div class="user-greeting">
          <div class="name-row">
            <h2>{{ authStore.user?.real_name || authStore.user?.username }}</h2>
            <el-tag :type="authStore.isAdmin ? 'danger' : 'primary'" effect="light" round class="role-tag">
              {{ authStore.isAdmin ? '系统管理员' : '班级学生' }}
            </el-tag>
          </div>
          <p class="user-subtitle">
            <span>学号：{{ authStore.user?.student_id || '暂无' }}</span>
            <el-divider v-if="!isMobile" direction="vertical" />
            <span>注册时间：{{ formatTime(authStore.user?.created_at) }}</span>
          </p>
        </div>
      </div>

      <el-divider border-style="dashed" class="custom-divider" />

      <!-- 详细信息展示模式 -->
      <div v-if="!editing" class="info-view-section">
        <div class="section-title">详细信息</div>
        <el-descriptions 
          :column="isMobile ? 1 : 2" 
          :direction="isMobile ? 'vertical' : 'horizontal'"
          border 
          class="modern-descriptions"
        >
          <el-descriptions-item label="系统用户名">
            {{ authStore.user?.username }}
          </el-descriptions-item>
          <el-descriptions-item label="真实姓名">
            {{ authStore.user?.real_name || '未填写' }}
          </el-descriptions-item>
          <el-descriptions-item label="学号/工号">
            {{ authStore.user?.student_id }}
          </el-descriptions-item>
          <el-descriptions-item label="政治面貌">
            {{ authStore.user?.political_status || '未填写' }}
          </el-descriptions-item>
          <el-descriptions-item label="电子邮箱">
            {{ authStore.user?.email || '未填写' }}
          </el-descriptions-item>
          <el-descriptions-item label="QQ号">
            {{ authStore.user?.qq_number || '未填写' }}
          </el-descriptions-item>
          <el-descriptions-item label="账号状态">
            <span style="color: #00B42A; display: flex; align-items: center; gap: 4px;">
              <el-icon><CircleCheckFilled /></el-icon> 正常
            </span>
          </el-descriptions-item>
        </el-descriptions>
      </div>

      <!-- 编辑模式 -->
      <div v-else class="info-edit-section">
        <div class="section-title">编辑详细资料</div>
        <div class="form-wrapper">
          <el-form 
            :model="profileForm" 
            :label-width="isMobile ? 'auto' : '100px'" 
            :label-position="isMobile ? 'top' : 'right'"
            size="large" 
            class="modern-form"
          >
            <el-form-item label="真实姓名">
              <el-input v-model="profileForm.real_name" placeholder="请输入您的真实姓名" />
            </el-form-item>
            <el-form-item label="政治面貌">
              <el-select v-model="profileForm.political_status" placeholder="请选择政治面貌" style="width: 100%;">
                <el-option label="群众" value="群众" />
                <el-option label="共青团员" value="共青团员" />
                <el-option label="预备党员" value="预备党员" />
                <el-option label="中共党员" value="中共党员" />
                <el-option label="其他" value="其他" />
              </el-select>
            </el-form-item>
            <el-form-item label="电子邮箱">
              <el-input v-model="profileForm.email" placeholder="请输入您的邮箱" />
            </el-form-item>
            <el-form-item label="QQ号">
              <el-input v-model="profileForm.qq_number" placeholder="用于接收QQ提醒消息" />
            </el-form-item>
            <el-form-item class="form-actions">
              <el-button @click="editing = false" :icon="Close" class="action-btn">取消修改</el-button>
              <el-button type="primary" :loading="saving" :icon="Check" @click="handleSave" class="action-btn">保存资料</el-button>
            </el-form-item>
          </el-form>
        </div>
      </div>
    </el-card>

    <!-- 修改密码弹窗 -->
    <el-dialog 
      v-model="passwordDialogVisible" 
      title="修改账户密码" 
      :width="isMobile ? '100%' : '480px'" 
      :fullscreen="isMobile"
      class="modern-dialog" 
      destroy-on-close
    >
      <div class="dialog-desc">为了您的账号安全，请定期更改密码。新密码长度不能少于6位。</div>
      <el-form 
        :model="passwordForm" 
        :label-width="isMobile ? 'auto' : '90px'" 
        :label-position="isMobile ? 'top' : 'right'"
        size="large"
      >
        <el-form-item label="当前密码">
          <el-input v-model="passwordForm.old_password" type="password" show-password placeholder="请输入原密码" />
        </el-form-item>
        <el-form-item label="新密码" :style="{ marginTop: isMobile ? '0' : '24px' }">
          <el-input v-model="passwordForm.new_password" type="password" show-password placeholder="请输入新密码 (至少6位)" />
        </el-form-item>
        <el-form-item label="确认密码">
          <el-input v-model="passwordForm.confirm_password" type="password" show-password placeholder="请再次输入新密码" />
        </el-form-item>
      </el-form>
      <template #footer>
        <div class="dialog-footer">
          <el-button @click="passwordDialogVisible = false">取消</el-button>
          <el-button type="primary" :loading="changingPassword" @click="handlePasswordChange">确认修改</el-button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, onBeforeUnmount } from 'vue'
import { ElMessage } from 'element-plus'
import { Edit, Lock, Close, Check, CircleCheckFilled } from '@element-plus/icons-vue'
import { useAuthStore } from '../stores/auth'
import api from '../api'

const authStore = useAuthStore()
const editing = ref(false)
const saving = ref(false)
const passwordDialogVisible = ref(false)
const changingPassword = ref(false)

// 响应式状态探测
const isMobile = ref(false)
const checkMobile = () => {
  isMobile.value = window.innerWidth <= 768
}

onMounted(() => {
  checkMobile()
  window.addEventListener('resize', checkMobile)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', checkMobile)
})

const profileForm = reactive({
  real_name: '',
  political_status: '',
  email: '',
  qq_number: '',
})

const passwordForm = reactive({
  old_password: '',
  new_password: '',
  confirm_password: '',
})

function formatTime(t) {
  if (!t) return '未知'
  return new Date(t).toLocaleString('zh-CN', { 
    year: 'numeric', month: '2-digit', day: '2-digit', 
    hour: '2-digit', minute: '2-digit' 
  })
}

function startEdit() {
  profileForm.real_name = authStore.user?.real_name || ''
  profileForm.political_status = authStore.user?.political_status || ''
  profileForm.email = authStore.user?.email || ''
  profileForm.qq_number = authStore.user?.qq_number || ''
  editing.value = true
}

async function handleSave() {
  saving.value = true
  try {
    await api.put('/api/users/me', {
      real_name: profileForm.real_name,
      political_status: profileForm.political_status,
      email: profileForm.email,
      qq_number: profileForm.qq_number,
    })
    authStore.user.real_name = profileForm.real_name
    authStore.user.political_status = profileForm.political_status
    authStore.user.email = profileForm.email
    authStore.user.qq_number = profileForm.qq_number
    localStorage.setItem('user', JSON.stringify(authStore.user))
    ElMessage.success('资料保存成功')
    editing.value = false
  } catch (err) {
    ElMessage.error(err.response?.data?.detail || '保存失败')
  } finally {
    saving.value = false
  }
}

function openPasswordDialog() {
  passwordForm.old_password = ''
  passwordForm.new_password = ''
  passwordForm.confirm_password = ''
  passwordDialogVisible.value = true
}

async function handlePasswordChange() {
  if (passwordForm.new_password.length < 6) {
    ElMessage.error('新密码长度不能少于6位')
    return
  }
  if (passwordForm.new_password !== passwordForm.confirm_password) {
    ElMessage.error('两次输入的密码不一致')
    return
  }
  changingPassword.value = true
  try {
    await api.put('/api/users/me/password', {
      old_password: passwordForm.old_password,
      new_password: passwordForm.new_password,
    })
    ElMessage.success('密码修改成功，下次请使用新密码登录')
    passwordDialogVisible.value = false
  } catch (err) {
    ElMessage.error(err.response?.data?.detail || '密码修改失败')
  } finally {
    changingPassword.value = false
  }
}
</script>

<style scoped>
/* 容器与卡片基底 */
.profile-container {
  padding: 0;
}

.page-card {
  border: none;
  border-radius: 8px;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.05);
  min-height: calc(100vh - 120px);
}

/* 顶部标题栏 */
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 32px;
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

.header-actions {
  display: flex;
  gap: 12px;
}

/* 身份展示区 */
.user-identity {
  display: flex;
  align-items: center;
  padding: 10px 20px;
}

.user-avatar {
  background: linear-gradient(135deg, #165DFF 0%, #0F43CA 100%);
  font-size: 32px;
  font-weight: bold;
  box-shadow: 0 4px 12px rgba(22, 93, 255, 0.2);
  flex-shrink: 0;
}

.user-greeting {
  margin-left: 24px;
}

.name-row {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 8px;
}

.name-row h2 {
  margin: 0;
  font-size: 24px;
  color: #1D2129;
  font-weight: 600;
}

.role-tag {
  transform: translateY(-1px);
}

.user-subtitle {
  margin: 0;
  color: #86909C;
  font-size: 14px;
  display: flex;
  align-items: center;
}

.custom-divider {
  margin: 32px 0;
  border-color: #E5E6EB;
}

/* 子模块标题 */
.section-title {
  font-size: 16px;
  font-weight: 600;
  color: #1D2129;
  margin-bottom: 20px;
  padding-left: 20px;
}

/* 详情列表美化 */
.info-view-section {
  padding: 0 20px;
}

:deep(.modern-descriptions .el-descriptions__label) {
  background-color: #F7F8FA !important;
  color: #4E5969;
  font-weight: 500;
  width: 140px;
}

:deep(.modern-descriptions .el-descriptions__content) {
  color: #1D2129;
  padding: 16px 20px !important;
}

/* 表单区域 */
.info-edit-section {
  padding: 0 20px;
}

.form-wrapper {
  max-width: 480px;
  background: #F7F8FA;
  padding: 32px 32px 16px 16px;
  border-radius: 8px;
  border: 1px solid #E5E6EB;
}

.form-actions {
  margin-top: 32px;
  margin-bottom: 0;
}

/* 弹窗文本 */
.dialog-desc {
  color: #86909C;
  font-size: 13px;
  margin-bottom: 24px;
  padding: 10px 16px;
  background: #F2F3F5;
  border-radius: 6px;
  line-height: 1.5;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}

/* 统一输入框获取焦点的动效 */
:deep(.el-input__wrapper.is-focus),
:deep(.el-select .el-input.is-focus .el-input__wrapper) {
  box-shadow: 0 0 0 1px #165DFF inset !important;
}

/* =======================================
   移动端响应式适配
   ======================================= */
@media screen and (max-width: 768px) {
  .page-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 16px;
    margin-bottom: 24px;
  }

  .header-actions {
    width: 100%;
    justify-content: space-between;
  }
  
  .header-actions .el-button {
    flex: 1;
    margin-left: 0 !important;
  }

  /* 身份展示区居中竖排 */
  .user-identity {
    flex-direction: column;
    text-align: center;
    padding: 10px 0;
    gap: 16px;
  }

  .user-greeting {
    margin-left: 0;
    display: flex;
    flex-direction: column;
    align-items: center;
  }

  .name-row h2 {
    font-size: 20px;
  }

  .user-subtitle {
    flex-direction: column;
    gap: 8px;
    font-size: 13px;
  }

  /* 调整详情区块的内边距 */
  .info-view-section, .info-edit-section {
    padding: 0;
  }

  .section-title {
    padding-left: 0;
  }

  /* 表单包裹区去边框去背景，彻底融入卡片 */
  .form-wrapper {
    background: transparent;
    padding: 0;
    border: none;
    max-width: 100%;
  }

  .form-actions {
    display: flex;
    justify-content: space-between;
  }
  
  .form-actions :deep(.el-form-item__content) {
    display: flex;
    justify-content: space-between;
    width: 100%;
    gap: 12px;
  }
  
  .action-btn {
    flex: 1;
    margin-left: 0 !important;
  }

  /* 移除弹窗在手机上的 margin，彻底融入全屏 */
  :deep(.modern-dialog) {
    margin: 0 !important;
  }
  
  :deep(.modern-dialog .el-dialog__body) {
    padding: 10px 15px 20px;
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