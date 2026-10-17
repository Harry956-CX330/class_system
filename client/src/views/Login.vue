<template>
  <div class="login-container">
    <div class="login-box">
      <div class="login-left">
        <div class="left-content">
          <div class="brand-subtitle">数科2441班</div>
          <h1 class="brand-title">智能班务系统</h1>
          <p class="brand-desc">高效、智能、便捷的班级数据管理平台</p>
        </div>
        <div class="decoration-circle"></div>
        <div class="decoration-circle-small"></div>
      </div>

      <div class="login-right">
        <div class="form-wrapper">
          <div class="form-header">
            <h2 class="form-title">欢迎登录</h2>
            <p class="form-subtitle">请输入您的姓名和密码</p>
          </div>

          <el-form 
            ref="formRef" 
            :model="form" 
            :rules="rules" 
            label-width="0"
            size="large"
          >
            <el-form-item prop="username">
              <el-input 
                v-model="form.username" 
                placeholder="姓名" 
                clearable
                class="modern-input"
              >
                <template #prefix>
                  <el-icon><User /></el-icon>
                </template>
              </el-input>
            </el-form-item>

            <el-form-item prop="password" style="margin-top: 24px;">
              <el-input 
                v-model="form.password" 
                type="password" 
                placeholder="密码" 
                show-password
                @keyup.enter="handleLogin"
                class="modern-input"
              >
                <template #prefix>
                  <el-icon><Lock /></el-icon>
                </template>
              </el-input>
            </el-form-item>

            <el-form-item style="margin-top: 36px;">
              <el-button 
                type="primary" 
                :loading="loading" 
                class="submit-btn" 
                @click="handleLogin"
              >
                登 录
              </el-button>
            </el-form-item>
          </el-form>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { User, Lock } from '@element-plus/icons-vue'
import api from '../api'
import { useAuthStore } from '../stores/auth'

const router = useRouter()
const authStore = useAuthStore()
const formRef = ref(null)
const loading = ref(false)

const form = reactive({
  username: '',
  password: '',
})

const rules = {
  username: [{ required: true, message: '请输入学号/姓名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
}

async function handleLogin() {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return
  loading.value = true
  try {
    const res = await api.post('/api/login', form)
    authStore.login(res.data.access_token, res.data.user)
    ElMessage.success('登录成功')
    // 管理员直接进入系统，班干跳转角色选择页，普通用户直接进入
    if (res.data.user?.role === 'admin') {
      authStore.setView('admin')
      router.push('/dashboard')
    } else if (res.data.user?.is_class_leader) {
      router.push('/role-select')
    } else {
      router.push('/dashboard')
    }
  } catch (err) {
    ElMessage.error(err.response?.data?.detail || '登录失败')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
/* 页面背景容器，统一采用后台的高级灰 */
.login-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 100vh;
  background-color: #F2F3F5;
  background-image: radial-gradient(circle at 50% 0%, #FFFFFF 0%, #F2F3F5 80%);
  padding: 20px; /* 增加整体内边距，防止在小屏幕上贴边 */
  box-sizing: border-box;
}

/* 核心登录卡片：响应式基础设置 */
.login-box {
  display: flex;
  width: 100%;
  max-width: 900px; /* 限制最大宽度 */
  min-height: 500px;
  background: #fff;
  border-radius: 16px;
  box-shadow: 0 8px 24px rgba(29, 33, 41, 0.08);
  overflow: hidden;
}

/* 左侧品牌展示区 */
.login-left {
  flex: 5;
  background: linear-gradient(135deg, #165DFF 0%, #0F43CA 100%);
  padding: 50px;
  display: flex;
  flex-direction: column;
  position: relative;
  overflow: hidden;
  color: #fff;
}

.left-content {
  position: relative;
  z-index: 2;
  margin-top: 40px;
}

.brand-subtitle {
  font-size: 16px;
  font-weight: 500;
  letter-spacing: 2px;
  margin-bottom: 12px;
  opacity: 0.8;
}

.brand-title {
  font-size: 36px;
  font-weight: 700;
  margin: 0 0 20px 0;
  letter-spacing: 1px;
}

.brand-desc {
  font-size: 15px;
  line-height: 1.6;
  opacity: 0.7;
}

/* 左侧背景装饰几何图形 */
.decoration-circle {
  position: absolute;
  bottom: -100px;
  right: -50px;
  width: 300px;
  height: 300px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.1);
  z-index: 1;
}

.decoration-circle-small {
  position: absolute;
  bottom: 80px;
  right: 180px;
  width: 100px;
  height: 100px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.05);
  z-index: 1;
}

/* 右侧表单区 */
.login-right {
  flex: 6;
  padding: 48px 64px;
  display: flex;
  flex-direction: column;
  justify-content: center;
  background: #fff;
}

.form-wrapper {
  width: 100%;
  max-width: 340px;
  margin: 0 auto;
}

.form-header {
  margin-bottom: 40px;
}

.form-title {
  font-size: 28px;
  font-weight: 600;
  color: #1D2129;
  margin: 0 0 8px 0;
}

.form-subtitle {
  font-size: 14px;
  color: #86909C;
  margin: 0;
}

/* 输入框定制美化 */
:deep(.modern-input .el-input__wrapper) {
  background-color: #F7F8FA;
  box-shadow: none !important;
  border: 1px solid transparent;
  border-radius: 8px;
  padding: 0 16px;
  transition: all 0.3s;
}

:deep(.modern-input .el-input__wrapper:hover) {
  background-color: #F2F3F5;
}

:deep(.modern-input .el-input__wrapper.is-focus) {
  background-color: #fff;
  border-color: #165DFF;
  box-shadow: 0 0 0 2px rgba(22, 93, 255, 0.2) !important;
}

:deep(.modern-input .el-input__inner) {
  height: 48px;
  font-size: 15px;
}

:deep(.modern-input .el-input__prefix-inner) {
  color: #86909C;
  font-size: 18px;
}

/* 按钮美化 */
.submit-btn {
  width: 100%;
  height: 48px;
  font-size: 16px;
  border-radius: 8px;
  background-color: #165DFF;
  border-color: #165DFF;
  font-weight: 500;
  transition: all 0.3s;
}

.submit-btn:hover {
  background-color: #4080FF;
  border-color: #4080FF;
  box-shadow: 0 4px 12px rgba(22, 93, 255, 0.3);
  transform: translateY(-1px);
}

/* =========================================
   响应式适配 (移动端 & 小屏幕)
   ========================================= */
@media screen and (max-width: 768px) {
  .login-box {
    flex-direction: column; /* 手机端改为上下堆叠布局 */
    max-width: 400px; /* 移动端限制最大宽度，像一张卡片 */
    min-height: auto;
  }

  .login-left {
    padding: 32px 24px;
    flex: unset;
  }

  .left-content {
    margin-top: 0; /* 移除顶部外边距 */
  }

  .brand-title {
    font-size: 26px; /* 缩小标题字体 */
    margin-bottom: 8px;
  }

  .brand-desc {
    font-size: 13px;
  }

  .decoration-circle {
    width: 200px;
    height: 200px;
    bottom: -60px;
    right: -30px;
  }

  .decoration-circle-small {
    width: 80px;
    height: 80px;
    bottom: 20px;
    right: 80px;
  }

  .login-right {
    padding: 32px 24px; /* 减小内边距 */
    flex: unset;
  }

  .form-header {
    margin-bottom: 24px; /* 减小间距 */
  }

  .form-title {
    font-size: 24px;
  }

  :deep(.modern-input .el-input__inner) {
    height: 44px; /* 移动端稍微减小输入框高度 */
  }

  .submit-btn {
    height: 44px;
  }
}
</style>