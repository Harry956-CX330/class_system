<template>
  <div class="role-select-container">
    <div class="role-select-card">
      <div class="welcome-section">
        <div class="avatar">
          {{ (authStore.user?.real_name || authStore.user?.username)?.charAt(0) || 'U' }}
        </div>
        <h2 class="greeting">你好，{{ authStore.user?.real_name || authStore.user?.username }}</h2>
        <p class="hint">检测到您拥有管理员权限，请选择要进入的端</p>
      </div>

      <div class="roles">
        <div class="role-card user-role" @click="selectView('user')">
          <div class="role-icon user-icon">
            <el-icon class="icon-svg"><UserFilled /></el-icon>
          </div>
          <div class="role-text">
            <h3 class="role-title">用户端</h3>
            <p class="role-desc">查看通知、成绩、证书等班级信息</p>
          </div>
        </div>

        <div class="role-card admin-role" @click="selectView('admin')">
          <div class="role-icon admin-icon">
            <el-icon class="icon-svg"><Setting /></el-icon>
          </div>
          <div class="role-text">
            <h3 class="role-title">管理端</h3>
            <p class="role-desc">管理用户、发布通知、系统设置等</p>
          </div>
        </div>
      </div>

      <div class="actions">
        <el-button type="danger" link @click="handleLogout">退出登录</el-button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { useRouter } from 'vue-router'
import { ElMessageBox } from 'element-plus'
import { UserFilled, Setting } from '@element-plus/icons-vue'
import { useAuthStore } from '../stores/auth'

const router = useRouter()
const authStore = useAuthStore()

function selectView(view) {
  authStore.setView(view)
  router.push('/dashboard')
}

function handleLogout() {
  ElMessageBox.confirm('确定要退出登录吗？', '系统提示', {
    confirmButtonText: '确定退出',
    cancelButtonText: '取消',
    type: 'warning',
  }).then(() => {
    authStore.logout()
    router.push('/login')
  }).catch(() => {})
}
</script>

<style scoped>
/* 基础容器布局 */
.role-select-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 100vh;
  background-color: #F2F3F5;
  padding: 20px;
  box-sizing: border-box;
}

.role-select-card {
  background: #fff;
  border-radius: 16px;
  box-shadow: 0 8px 24px rgba(29, 33, 41, 0.08);
  padding: 48px;
  max-width: 600px;
  width: 100%;
  text-align: center;
}

/* 欢迎区域 */
.welcome-section {
  margin-bottom: 40px;
}

.avatar {
  width: 64px;
  height: 64px;
  border-radius: 50%;
  background: linear-gradient(135deg, #165DFF 0%, #0F43CA 100%);
  color: #fff;
  font-size: 28px;
  font-weight: 600;
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto 16px;
}

.greeting {
  font-size: 22px;
  font-weight: 600;
  color: #1D2129;
  margin: 0 0 8px 0;
}

.hint {
  font-size: 14px;
  color: #86909C;
  margin: 0;
}

/* 角色选择区域 (PC端默认网格排版) */
.roles {
  display: flex;
  gap: 20px;
  margin-bottom: 32px;
}

.role-card {
  flex: 1;
  padding: 32px 20px;
  border-radius: 12px;
  border: 2px solid #E5E6EB;
  cursor: pointer;
  transition: all 0.3s;
  
  /* 添加点击反馈，对移动端特别重要 */
  user-select: none;
  -webkit-tap-highlight-color: transparent;
}

/* 仅在支持鼠标 Hover 的设备上生效，避免移动端点击后样式粘滞 */
@media (hover: hover) {
  .role-card:hover {
    transform: translateY(-4px);
  }
  .user-role:hover {
    border-color: #165DFF;
    box-shadow: 0 4px 16px rgba(22, 93, 255, 0.15);
    background: #F7F8FF;
  }
  .admin-role:hover {
    border-color: #F53F3F;
    box-shadow: 0 4px 16px rgba(245, 63, 63, 0.15);
    background: #FFF7F7;
  }
}

/* 点击时的按下效果 */
.role-card:active {
  transform: scale(0.98);
  border-color: #C9CDD4;
}

.role-icon {
  width: 72px;
  height: 72px;
  border-radius: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto 16px;
}

.icon-svg {
  font-size: 40px;
}

.user-icon {
  background: #E8F3FF;
  color: #165DFF;
}

.admin-icon {
  background: #FFECE8;
  color: #F53F3F;
}

.role-title {
  font-size: 18px;
  font-weight: 600;
  color: #1D2129;
  margin: 0 0 8px 0;
}

.role-desc {
  font-size: 13px;
  color: #86909C;
  margin: 0;
  line-height: 1.5;
}

/* 底部操作 */
.actions {
  padding-top: 16px;
  border-top: 1px solid #E5E6EB;
}

/* ================= 移动端响应式适配 ================= */
@media screen and (max-width: 768px) {
  .role-select-card {
    padding: 32px 20px;
  }

  .welcome-section {
    margin-bottom: 28px;
  }

  .greeting {
    font-size: 20px;
  }

  .roles {
    flex-direction: column;
    gap: 16px;
  }

  /* 移动端转换为：左侧图标 + 右侧文字 的横向列表布局 */
  .role-card {
    display: flex;
    align-items: center;
    padding: 16px;
    text-align: left;
  }

  .role-icon {
    width: 56px;
    height: 56px;
    margin: 0 16px 0 0;
    flex-shrink: 0;
    border-radius: 12px;
  }

  .icon-svg {
    font-size: 32px;
  }

  .role-text {
    flex: 1;
  }

  .role-title {
    font-size: 16px;
    margin: 0 0 4px 0;
  }

  .role-desc {
    font-size: 12px;
  }
}
</style>