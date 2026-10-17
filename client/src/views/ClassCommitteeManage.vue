<template>
  <div class="committee-manage-container">
    <el-card class="page-card" shadow="never">
      <div class="page-header">
        <div class="header-left">
          <div class="title-indicator"></div>
          <h3 class="page-title">班委通讯录管理</h3>
        </div>
        <span class="header-tip">勾选"展示"后，该班委信息将出现在首页悬浮问号中</span>
      </div>

      <el-table
        :data="committees"
        style="width: 100%"
        v-loading="loading"
        class="custom-table"
        :header-cell-style="{ background: '#F7F8FA', color: '#4E5969', fontWeight: '500' }"
      >
        <el-table-column prop="real_name" label="姓名" min-width="100" />
        <el-table-column prop="class_position" label="职位" min-width="140">
          <template #default="{ row }">
            <el-input
              v-model="row.class_position"
              placeholder="如：班长、团支书"
              size="small"
              @blur="handleSave(row)"
            />
          </template>
        </el-table-column>
        <el-table-column label="手机号" min-width="150">
          <template #default="{ row }">
            <el-input
              v-model="row.phone"
              placeholder="请输入手机号"
              size="small"
              @blur="handleSave(row)"
            />
          </template>
        </el-table-column>
        <el-table-column label="QQ号" min-width="150">
          <template #default="{ row }">
            <el-input
              v-model="row.qq_number"
              placeholder="请输入QQ号"
              size="small"
              @blur="handleSave(row)"
            />
          </template>
        </el-table-column>
        <el-table-column label="宿舍" min-width="130">
          <template #default="{ row }">
            <el-input
              v-model="row.dorm"
              placeholder="如：3栋201"
              size="small"
              @blur="handleSave(row)"
            />
          </template>
        </el-table-column>
        <el-table-column label="展示" width="70" align="center">
          <template #default="{ row }">
            <el-switch
              v-model="row.show_in_committee"
              @change="handleSave(row)"
              size="small"
            />
          </template>
        </el-table-column>
        <el-table-column label="排序" width="100" align="center">
          <template #default="{ row, $index }">
            <div class="sort-buttons">
              <el-button
                :disabled="$index === 0"
                size="small"
                :icon="Top"
                circle
                @click="moveUp(row, $index)"
                title="上移"
              />
              <el-button
                :disabled="$index === committees.length - 1"
                size="small"
                :icon="Bottom"
                circle
                @click="moveDown(row, $index)"
                title="下移"
              />
            </div>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="80" fixed="right">
          <template #default="{ row }">
            <el-button size="small" type="primary" link @click="handleSave(row)">保存</el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-empty v-if="!loading && committees.length === 0" description="暂无班委成员，请先在用户管理中设置班委" :image-size="120" />
    </el-card>

    <!-- 辅导员信息 -->
    <el-card class="page-card counselor-card" shadow="never" style="margin-top: 20px;">
      <div class="page-header">
        <div class="header-left">
          <div class="title-indicator"></div>
          <h3 class="page-title">辅导员信息</h3>
        </div>
      </div>
      <el-form :model="counselor" label-width="80px" class="counselor-form">
        <el-row :gutter="20">
          <el-col :span="12" :xs="24">
            <el-form-item label="姓名">
              <el-input v-model="counselor.name" placeholder="辅导员姓名" />
            </el-form-item>
          </el-col>
          <el-col :span="12" :xs="24">
            <el-form-item label="办公室">
              <el-input v-model="counselor.office" placeholder="办公室地址" />
            </el-form-item>
          </el-col>
          <el-col :span="12" :xs="24">
            <el-form-item label="手机号">
              <el-input v-model="counselor.phone" placeholder="手机号码" />
            </el-form-item>
          </el-col>
          <el-col :span="12" :xs="24">
            <el-form-item label="QQ号">
              <el-input v-model="counselor.qq_number" placeholder="QQ号码" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item>
          <el-button type="primary" @click="handleSaveCounselor" :loading="counselorSaving">保存辅导员信息</el-button>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Top, Bottom } from '@element-plus/icons-vue'
import api from '../api'

const committees = ref([])
const loading = ref(false)
const counselor = ref({ name: '', office: '', phone: '', qq_number: '' })
const counselorSaving = ref(false)

async function loadCommittees() {
  loading.value = true
  try {
    const res = await api.get('/api/class-committee/all')
    committees.value = res.data
  } catch {
    ElMessage.error('加载班委信息失败')
  } finally {
    loading.value = false
  }
}

async function loadCounselor() {
  try {
    const res = await api.get('/api/counselor')
    counselor.value = res.data
  } catch {
    // 静默失败
  }
}

async function handleSave(row) {
  try {
    await api.put(`/api/class-committee/${row.id}`, {
      class_position: row.class_position,
      phone: row.phone,
      qq_number: row.qq_number,
      dorm: row.dorm,
      show_in_committee: row.show_in_committee,
    })
    ElMessage.success('保存成功')
  } catch (err) {
    ElMessage.error(err.response?.data?.detail || '保存失败')
  }
}

async function handleSaveCounselor() {
  counselorSaving.value = true
  try {
    await api.put('/api/counselor', { ...counselor.value })
    ElMessage.success('辅导员信息已保存')
  } catch (err) {
    ElMessage.error(err.response?.data?.detail || '保存失败')
  } finally {
    counselorSaving.value = false
  }
}

async function moveUp(row, index) {
  if (index <= 0) return
  const prev = committees.value[index - 1]
  const prevOrder = prev.sort_order ?? 0
  const curOrder = row.sort_order ?? 0
  try {
    await api.put(`/api/class-committee/${row.id}`, { sort_order: prevOrder })
    await api.put(`/api/class-committee/${prev.id}`, { sort_order: curOrder })
    ElMessage.success('排序已更新')
    await loadCommittees()
  } catch (err) {
    ElMessage.error(err.response?.data?.detail || '排序失败')
  }
}

async function moveDown(row, index) {
  if (index >= committees.value.length - 1) return
  const next = committees.value[index + 1]
  const nextOrder = next.sort_order ?? 0
  const curOrder = row.sort_order ?? 0
  try {
    await api.put(`/api/class-committee/${row.id}`, { sort_order: nextOrder })
    await api.put(`/api/class-committee/${next.id}`, { sort_order: curOrder })
    ElMessage.success('排序已更新')
    await loadCommittees()
  } catch (err) {
    ElMessage.error(err.response?.data?.detail || '排序失败')
  }
}

onMounted(() => {
  loadCommittees()
  loadCounselor()
})
</script>

<style scoped>
.committee-manage-container {
  padding: 0;
}

.page-card {
  border: none;
  border-radius: 8px;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.05);
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

.header-tip {
  color: #86909C;
  font-size: 13px;
}

:deep(.custom-table::before) {
  display: none;
}

.counselor-form {
  margin-top: 8px;
}

.sort-buttons {
  display: flex;
  justify-content: center;
  gap: 4px;
}
</style>
