<template>
  <div class="online-sheet-container">
    <el-card class="page-card" shadow="never">
      <div class="page-header">
        <div class="header-left">
          <div class="title-indicator"></div>
          <h3 class="page-title">在线协作表格</h3>
        </div>
        <div class="header-right">
          <el-button :icon="Refresh" :loading="loading" @click="reloadIframe" class="action-btn">
            刷新表格
          </el-button>
          <el-button 
            v-if="authStore.isAdmin" 
            :icon="EditPen" 
            type="primary" 
            plain
            @click="settingsVisible = true"
            class="action-btn"
          >
            设置链接
          </el-button>
        </div>
      </div>

      <div v-if="sheetUrl" class="iframe-wrapper">
        <iframe 
          :key="iframeKey"
          :src="sheetUrl" 
          frameborder="0"
          scrolling="auto"
          class="kdocs-iframe"
          @load="loading = false"
        />
      </div>
      <div v-else class="empty-state">
        <el-empty description="尚未配置金山文档链接">
          <el-button v-if="authStore.isAdmin" type="primary" @click="settingsVisible = true">去设置</el-button>
        </el-empty>
      </div>

      <div class="footer-hint">
        <el-icon><InfoFilled /></el-icon>
        数据由金山文档实时同步，如有问题请联系管理员。
      </div>
    </el-card>

    <el-dialog 
      v-model="settingsVisible" 
      title="金山文档链接设置" 
      width="95%" 
      style="max-width: 500px"
      destroy-on-close
    >
      <el-form label-position="top">
        <el-form-item label="金山文档在线表格分享链接">
          <el-input 
            v-model="urlInput" 
            placeholder="https://kdocs.cn/l/xxxxxxxxx" 
            size="large"
          />
        </el-form-item>
        <el-alert 
          title="获取方法" 
          type="info" 
          :closable="false"
          class="info-alert"
        >
          在金山文档中打开所需表格 → 右上角「分享」→ 「所有人可编辑」→ 复制链接
        </el-alert>
      </el-form>
      <template #footer>
        <div class="dialog-footer">
          <el-button @click="settingsVisible = false" class="dialog-btn">取消</el-button>
          <el-button type="primary" :loading="saving" @click="saveUrl" class="dialog-btn">保存</el-button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Refresh, EditPen, InfoFilled } from '@element-plus/icons-vue'
import { useAuthStore } from '../stores/auth'
import api from '../api'

const authStore = useAuthStore()

const sheetUrl = ref('')
const iframeKey = ref(0)
const loading = ref(false)
const settingsVisible = ref(false)
const urlInput = ref('')
const saving = ref(false)

function reloadIframe() {
  loading.value = true
  iframeKey.value++
}

async function loadUrl() {
  try {
    const res = await api.get('/api/config/kdocs-url-public')
    sheetUrl.value = res.data.url
    urlInput.value = res.data.url
  } catch {}
}

async function saveUrl() {
  saving.value = true
  try {
    await api.put('/api/config/kdocs-url', { url: urlInput.value })
    sheetUrl.value = urlInput.value
    settingsVisible.value = false
    iframeKey.value++
    ElMessage.success('链接已保存')
  } catch (err) {
    ElMessage.error(err.response?.data?.detail || '保存失败')
  } finally {
    saving.value = false
  }
}

onMounted(loadUrl)
</script>

<style scoped>
.online-sheet-container {
  padding: 0;
}

.page-card {
  border: none;
  border-radius: 8px;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.05);
  min-height: calc(100vh - 120px);
  display: flex;
  flex-direction: column;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.header-left {
  display: flex;
  align-items: center;
}

.header-right {
  display: flex;
  gap: 12px;
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

.iframe-wrapper {
  border: 1px solid #E5E6EB;
  border-radius: 4px;
  overflow: hidden;
  margin-bottom: 20px;
  flex-grow: 1; /* 让 iframe 容器自动填充剩余高度 */
  display: flex;
}

.kdocs-iframe {
  width: 100%;
  height: 65vh; /* 桌面端默认高度 */
  display: block;
  border: none;
}

.empty-state {
  padding: 60px 0;
  flex-grow: 1;
}

.footer-hint {
  display: flex;
  align-items: center;
  gap: 6px;
  color: #86909C;
  font-size: 13px;
  padding: 12px 0 0 0;
  border-top: 1px solid #F2F3F5;
}

.info-alert {
  margin-bottom: 16px;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}

/* =======================================
   移动端响应式适配 (Media Queries)
   ======================================= */
@media screen and (max-width: 768px) {
  .page-card {
    min-height: calc(100vh - 100px); /* 适应移动端底部高度 */
  }

  .page-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 16px;
  }

  .header-right {
    width: 100%;
    justify-content: space-between;
  }

  .action-btn {
    flex: 1;
    margin-left: 0 !important; /* 覆盖默认组件间隔 */
  }

  .kdocs-iframe {
    height: calc(100vh - 260px); /* 在移动端利用 vh 动态计算高度，最大化表格显示区域 */
  }

  .dialog-footer {
    justify-content: space-between;
  }
 
  .dialog-btn {
    flex: 1;
    margin-left: 0 !important;
  }

  .info-alert {
    line-height: 1.5; /* 防止提示信息拥挤 */
  }
}
</style>