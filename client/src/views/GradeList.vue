<template>
  <div>
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; flex-wrap: wrap; gap: 10px">
      <h3 style="margin: 0">成绩管理</h3>
      <div style="display: flex; gap: 10px; flex-wrap: wrap">
        <el-select v-model="filterSemester" placeholder="选择学期" clearable style="width: 160px" @change="loadGrades">
          <el-option v-for="s in semesters" :key="s" :label="s" :value="s" />
        </el-select>
        <el-select v-model="filterYear" placeholder="选择学年" clearable style="width: 160px" @change="loadGrades">
          <el-option v-for="y in years" :key="y" :label="y" :value="y" />
        </el-select>
        <el-button v-if="authStore.canViewAllData" type="primary" @click="openCreateDialog">录入成绩</el-button>
        <el-upload v-if="authStore.canViewAllData" ref="gradeUploadRef" :auto-upload="false" :limit="1"
          accept=".xlsx,.xls,.csv" :on-change="handleGradeFileChange" :on-remove="handleGradeFileRemove" style="display: inline-block">
          <el-button>导入文件</el-button>
        </el-upload>
        <el-button v-if="authStore.canViewAllData" @click="downloadGradeTemplate">下载模板</el-button>
        <el-button v-if="authStore.canViewAllData && gradeFile" type="success" :loading="importLoading" @click="handleGradeImport">提交导入</el-button>
        <el-button v-if="!authStore.canViewAllData" type="warning" @click="openChangeRequestDialog()">申请修改/新增成绩</el-button>
      </div>
    </div>

    <!-- 免责声明 -->
    <div class="disclaimer-bar">
      <el-icon><InfoFilled /></el-icon>
      <span>该成绩仅供参考，一切以喜鹊儿系统为准。若有误差请自行申请修改维护成绩，待管理员审批后生效。</span>
    </div>

    <!-- 绩点总结 & 2.0 警告 -->
    <div v-if="grades.length > 0 && overallGpa !== null" class="gpa-summary" :class="{ 'gpa-warning': overallGpa < 2.0 }">
      <div class="gpa-main">
        <span class="gpa-label">{{ authStore.canViewAllData ? '' : '我的' }}总平均绩点</span>
        <span class="gpa-value" :class="{ 'gpa-danger': overallGpa < 2.0 }">{{ overallGpa.toFixed(2) }}</span>
        <span class="gpa-total">（{{ grades.length }} 条记录）</span>
      </div>
      <div v-if="overallGpa < 2.0" class="gpa-alert">
        <el-icon><WarningFilled /></el-icon>
        <span>绩点低于 2.0 及格线，请注意！</span>
      </div>
      <div v-else class="gpa-pass">
        <el-icon><CircleCheck /></el-icon>
        <span>绩点达标（≥ 2.0）</span>
      </div>
    </div>

    <!-- 管理端：各学生整体绩点汇总 -->
    <div v-if="authStore.canViewAllData && studentGpaList.length > 0" class="admin-gpa-section">
      <h4 style="margin: 0 0 12px 0; color: var(--el-text-color-primary);">学生整体绩点汇总</h4>
      <div class="gpa-student-grid">
        <div v-for="s in studentGpaList" :key="s.student_id" class="gpa-student-card" :class="{ 'gpa-student-danger': s.avgGpa < 2.0 }">
          <div class="gpa-student-name">{{ s.student_name }}</div>
          <div class="gpa-student-id">{{ s.student_student_id }}</div>
          <div class="gpa-student-value" :class="{ 'gpa-danger': s.avgGpa < 2.0 }">
            {{ s.avgGpa.toFixed(2) }}
          </div>
          <div v-if="s.avgGpa < 2.0" class="gpa-student-warn">
            <el-icon><WarningFilled /></el-icon> 低于及格线
          </div>
        </div>
      </div>
    </div>

    <!-- 管理端：待审批的成绩修改申请 -->
    <div v-if="authStore.canViewAllData && pendingRequests.length > 0" class="admin-gpa-section" style="border-color: #FFB74D; background: #FFF8E1;">
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
        <h4 style="margin: 0; color: #E65100;">待审批成绩修改（{{ pendingRequests.length }}）</h4>
      </div>
      <div v-for="r in pendingRequests" :key="r.id" class="change-request-item">
        <div class="cr-info">
          <strong>{{ r.student_name }}</strong>（{{ r.student_student_id }}）
          <template v-if="r.grade_id">修改</template>
          <template v-else>新增</template>
          ：{{ r.proposed_semester }} / {{ r.proposed_academic_year }}
        </div>
        <div class="cr-values">
          成绩：<strong>{{ r.proposed_score }}</strong>
          绩点：<strong>{{ r.proposed_gpa }}</strong>
        </div>
        <div class="cr-actions">
          <el-button type="success" size="small" @click="approveRequest(r.id)">通过</el-button>
          <el-button type="danger" size="small" @click="rejectRequest(r.id)">驳回</el-button>
        </div>
      </div>
    </div>

    <!-- 学生端：我的修改申请 -->
    <div v-if="!authStore.canViewAllData && myRequests.length > 0" style="margin-bottom: 16px;">
      <h4 style="margin: 0 0 8px 0; color: var(--el-text-color-primary);">我的成绩修改申请</h4>
      <div v-for="r in myRequests" :key="r.id" class="my-req-item" :class="'req-' + r.status">
        <div class="req-status">
          <el-tag v-if="r.status === 'pending'" type="warning" size="small">待审批</el-tag>
          <el-tag v-else-if="r.status === 'approved'" type="success" size="small">已通过</el-tag>
          <el-tag v-else type="danger" size="small">已驳回</el-tag>
        </div>
        <div class="req-detail">
          <template v-if="r.grade_id">修改</template>
          <template v-else>新增</template>
          ：{{ r.proposed_semester }} / {{ r.proposed_academic_year }}
          ｜ 成绩：{{ r.proposed_score }} ｜ 绩点：{{ r.proposed_gpa }}
        </div>
        <div v-if="r.admin_comment" class="req-comment">批注：{{ r.admin_comment }}</div>
      </div>
    </div>

    <el-table :data="grades" border stripe v-loading="loading">
      <el-table-column v-if="authStore.canViewAllData" prop="student_name" label="学生姓名" width="120" />
      <el-table-column v-if="authStore.canViewAllData" prop="student_student_id" label="学号" width="120" />
      <el-table-column prop="score" label="成绩" width="100" />
      <el-table-column prop="gpa" label="绩点" width="100">
        <template #default="{ row }">
          <span :style="{ color: row.gpa < 2.0 ? '#F53F3F' : '', fontWeight: row.gpa < 2.0 ? 'bold' : '' }">{{ row.gpa }}</span>
        </template>
      </el-table-column>
      <el-table-column label="班级排名" width="120">
        <template #default="{ row }">
          {{ row.class_rank }}/{{ row.total_students }}
        </template>
      </el-table-column>
      <el-table-column prop="semester" label="学期" width="140" />
      <el-table-column prop="academic_year" label="学年" width="120" />
      <el-table-column label="操作" :width="authStore.canViewAllData ? 200 : 80" fixed="right">
        <template #default="{ row }">
          <el-button v-if="authStore.canViewAllData" size="small" @click="openEditDialog(row)">编辑</el-button>
          <el-button v-if="authStore.canViewAllData" size="small" type="danger" @click="handleDelete(row)">删除</el-button>
          <el-button v-if="!authStore.canViewAllData" size="small" type="warning" @click="openChangeRequestDialog(row)">修改</el-button>
        </template>
      </el-table-column>
    </el-table>

    <div v-if="!authStore.canViewAllData && groupedGrades.length" style="margin-top: 20px">
      <h3>按学年分类汇总</h3>
      <div v-for="group in groupedGrades" :key="group.year" style="margin-bottom: 16px">
        <el-card>
          <template #header>
            <span style="font-weight: bold">{{ group.year }} 学年</span>
            <span style="margin-left: 16px" :style="{ color: group.avgGpa < 2.0 ? '#F53F3F' : '#666' }">
              平均绩点: <strong>{{ group.avgGpa.toFixed(2) }}</strong>
              <el-tag v-if="group.avgGpa < 2.0" type="danger" size="small" style="margin-left: 6px">未达标</el-tag>
            </span>
          </template>
          <el-table :data="group.items" border size="small">
            <el-table-column prop="semester" label="学期" />
            <el-table-column prop="score" label="成绩" />
            <el-table-column prop="gpa" label="绩点">
              <template #default="{ row }">
                <span :style="{ color: row.gpa < 2.0 ? '#F53F3F' : '', fontWeight: row.gpa < 2.0 ? 'bold' : '' }">{{ row.gpa }}</span>
              </template>
            </el-table-column>
            <el-table-column label="排名">
              <template #default="{ row }">
                {{ row.class_rank }}/{{ row.total_students }}
              </template>
            </el-table-column>
            <el-table-column label="操作" width="80">
              <template #default="{ row }">
                <el-button size="small" type="warning" link @click="openChangeRequestDialog(row)">修改</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </div>
    </div>

    <!-- 管理端录入/编辑弹窗 -->
    <el-dialog v-model="dialogVisible" :title="isEdit ? '编辑成绩' : '录入成绩'" width="500px">
      <el-form :model="gradeForm" label-width="80px">
        <el-form-item v-if="authStore.canViewAllData" label="学生">
          <el-select v-model="gradeForm.student_id" filterable placeholder="选择学生" style="width: 100%">
            <el-option v-for="s in students" :key="s.id" :label="`${s.real_name} (${s.student_id})`" :value="s.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="成绩">
          <el-input-number v-model="gradeForm.score" :min="0" :max="100" :precision="1" style="width: 100%" />
        </el-form-item>
        <el-form-item label="绩点">
          <el-input-number v-model="gradeForm.gpa" :min="0" :max="5" :precision="2" :step="0.1" style="width: 100%" />
        </el-form-item>
        <el-form-item label="班级排名">
          <el-input-number v-model="gradeForm.class_rank" :min="1" style="width: 100%" />
        </el-form-item>
        <el-form-item label="班级总人数">
          <el-input-number v-model="gradeForm.total_students" :min="1" style="width: 100%" />
        </el-form-item>
        <el-form-item label="学期">
          <el-input v-model="gradeForm.semester" placeholder="如 2024-2025-1" />
        </el-form-item>
        <el-form-item label="学年">
          <el-input v-model="gradeForm.academic_year" placeholder="如 2024-2025" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSubmit">{{ isEdit ? '保存' : '录入' }}</el-button>
      </template>
    </el-dialog>

    <!-- 学生端：申请修改成绩弹窗 -->
    <el-dialog v-model="changeDialogVisible" :title="changeGradeId ? '申请修改成绩' : '申请新增成绩'" width="480px">
      <div class="disclaimer-bar" style="margin-bottom: 16px;">
        <el-icon><InfoFilled /></el-icon>
        <span>修改申请需经管理员审批后生效。请如实填写。</span>
      </div>
      <el-form :model="changeForm" label-width="80px">
        <el-form-item label="成绩">
          <el-input-number v-model="changeForm.proposed_score" :min="0" :max="100" :precision="1" style="width: 100%" />
        </el-form-item>
        <el-form-item label="绩点">
          <el-input-number v-model="changeForm.proposed_gpa" :min="0" :max="5" :precision="2" :step="0.1" style="width: 100%" />
        </el-form-item>
        <el-form-item label="班级排名">
          <el-input-number v-model="changeForm.proposed_class_rank" :min="1" style="width: 100%" />
        </el-form-item>
        <el-form-item label="班级总人数">
          <el-input-number v-model="changeForm.proposed_total_students" :min="1" style="width: 100%" />
        </el-form-item>
        <el-form-item label="学期">
          <el-input v-model="changeForm.proposed_semester" placeholder="如 2024-2025-1" />
        </el-form-item>
        <el-form-item label="学年">
          <el-input v-model="changeForm.proposed_academic_year" placeholder="如 2024-2025" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="changeDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submittingChange" @click="submitChangeRequest">提交申请</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { WarningFilled, CircleCheck, InfoFilled } from '@element-plus/icons-vue'
import { useAuthStore } from '../stores/auth'
import api from '../api'

const authStore = useAuthStore()
const grades = ref([])
const students = ref([])
const loading = ref(false)
const dialogVisible = ref(false)
const isEdit = ref(false)
const editId = ref(null)
const filterSemester = ref('')
const filterYear = ref('')
const gradeUploadRef = ref(null)
const gradeFile = ref(null)
const importLoading = ref(false)

const gradeForm = reactive({
  student_id: null,
  score: 0,
  gpa: 0,
  class_rank: 0,
  total_students: 0,
  semester: '',
  academic_year: '',
})

// 成绩修改申请
const changeDialogVisible = ref(false)
const changeGradeId = ref(null)
const submittingChange = ref(false)
const changeForm = reactive({
  proposed_score: 0,
  proposed_gpa: 0,
  proposed_semester: '',
  proposed_academic_year: '',
  proposed_class_rank: 0,
  proposed_total_students: 0,
})
const pendingRequests = ref([])
const myRequests = ref([])

const semesters = computed(() => [...new Set(grades.value.map(g => g.semester))].sort().reverse())
const years = computed(() => [...new Set(grades.value.map(g => g.academic_year))].sort().reverse())

const groupedGrades = computed(() => {
  const groups = {}
  grades.value.forEach(g => {
    const y = g.academic_year || '未知'
    if (!groups[y]) groups[y] = { year: y, items: [], totalGpa: 0 }
    groups[y].items.push(g)
    groups[y].totalGpa += g.gpa
  })
  return Object.values(groups).map(g => ({
    ...g,
    avgGpa: g.items.length ? g.totalGpa / g.items.length : 0,
  }))
})

const overallGpa = computed(() => {
  if (grades.value.length === 0) return null
  const sum = grades.value.reduce((s, g) => s + g.gpa, 0)
  return sum / grades.value.length
})

const studentGpaList = computed(() => {
  const map = {}
  grades.value.forEach(g => {
    const sid = g.student_id
    if (!map[sid]) map[sid] = { student_id: sid, student_name: g.student_name, student_student_id: g.student_student_id, totalGpa: 0, count: 0 }
    map[sid].totalGpa += g.gpa
    map[sid].count++
  })
  return Object.values(map).map(s => ({
    ...s,
    avgGpa: s.count ? s.totalGpa / s.count : 0,
  })).sort((a, b) => a.avgGpa - b.avgGpa)
})

async function loadGrades() {
  loading.value = true
  try {
    const params = {}
    if (filterSemester.value) params.semester = filterSemester.value
    if (filterYear.value) params.academic_year = filterYear.value
    const res = await api.get('/api/grades', { params })
    grades.value = res.data
  } catch {
    ElMessage.error('加载成绩失败')
  } finally {
    loading.value = false
  }
}

async function loadStudents() {
  try {
    const res = await api.get('/api/users', { params: { role: 'student' } })
    students.value = res.data
  } catch {}
}

async function loadChangeRequests() {
  try {
    const res = await api.get('/api/grades/change-requests')
    if (authStore.canViewAllData) {
      pendingRequests.value = (res.data || []).filter(r => r.status === 'pending')
    } else {
      myRequests.value = res.data || []
    }
  } catch {}
}

function openCreateDialog() {
  isEdit.value = false
  editId.value = null
  gradeForm.student_id = null
  gradeForm.score = 0
  gradeForm.gpa = 0
  gradeForm.class_rank = 0
  gradeForm.total_students = 0
  gradeForm.semester = ''
  gradeForm.academic_year = ''
  dialogVisible.value = true
}

function openEditDialog(row) {
  isEdit.value = true
  editId.value = row.id
  gradeForm.student_id = row.student_id
  gradeForm.score = row.score
  gradeForm.gpa = row.gpa
  gradeForm.class_rank = row.class_rank
  gradeForm.total_students = row.total_students
  gradeForm.semester = row.semester
  gradeForm.academic_year = row.academic_year
  dialogVisible.value = true
}

async function handleSubmit() {
  try {
    if (isEdit.value) {
      await api.put(`/api/grades/${editId.value}`, gradeForm)
      ElMessage.success('修改成功')
    } else {
      await api.post('/api/grades', gradeForm)
      ElMessage.success('录入成功')
    }
    dialogVisible.value = false
    loadGrades()
  } catch (err) {
    ElMessage.error(err.response?.data?.detail || '操作失败')
  }
}

async function handleDelete(row) {
  try {
    await ElMessageBox.confirm('确定要删除该成绩吗？', '提示', { type: 'warning' })
    await api.delete(`/api/grades/${row.id}`)
    ElMessage.success('删除成功')
    loadGrades()
  } catch {}
}

function openChangeRequestDialog(row) {
  changeGradeId.value = row ? row.id : null
  if (row) {
    changeForm.proposed_score = row.score
    changeForm.proposed_gpa = row.gpa
    changeForm.proposed_semester = row.semester
    changeForm.proposed_academic_year = row.academic_year
    changeForm.proposed_class_rank = row.class_rank
    changeForm.proposed_total_students = row.total_students
  } else {
    changeForm.proposed_score = 0
    changeForm.proposed_gpa = 0
    changeForm.proposed_semester = ''
    changeForm.proposed_academic_year = ''
    changeForm.proposed_class_rank = 0
    changeForm.proposed_total_students = 0
  }
  changeDialogVisible.value = true
}

async function submitChangeRequest() {
  submittingChange.value = true
  try {
    await api.post('/api/grades/change-request', {
      grade_id: changeGradeId.value || null,
      ...changeForm,
    })
    ElMessage.success('修改申请已提交，等待管理员审批')
    changeDialogVisible.value = false
    loadChangeRequests()
  } catch (err) {
    ElMessage.error(err.response?.data?.detail || '提交失败')
  } finally { submittingChange.value = false }
}

async function approveRequest(reqId) {
  try {
    await api.put(`/api/grades/change-requests/${reqId}/approve`, { comment: '' })
    ElMessage.success('已通过')
    loadGrades()
    loadChangeRequests()
  } catch (err) {
    ElMessage.error(err.response?.data?.detail || '操作失败')
  }
}

async function rejectRequest(reqId) {
  try {
    await ElMessageBox.prompt('驳回理由（可选）', '驳回申请', { inputType: 'textarea' })
      .then(async ({ value }) => {
        await api.put(`/api/grades/change-requests/${reqId}/reject`, { comment: value || '' })
        ElMessage.success('已驳回')
        loadChangeRequests()
      })
  } catch {}
}

function handleGradeFileChange(file) { gradeFile.value = file }
function handleGradeFileRemove() { gradeFile.value = null }

async function handleGradeImport() {
  if (!gradeFile.value) return ElMessage.warning('请选择文件')
  importLoading.value = true
  const fd = new FormData()
  fd.append('file', gradeFile.value.raw)
  try {
    const res = await api.post('/api/grades/import-file', fd, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    ElMessage.success(`导入完成: 成功 ${res.data.created} 个`)
    if (res.data.errors.length) ElMessage.warning(`失败: ${res.data.errors.join(', ')}`)
    gradeUploadRef.value.clearFiles()
    gradeFile.value = null
    loadGrades()
  } catch (err) {
    ElMessage.error(err.response?.data?.detail || '导入失败')
  } finally { importLoading.value = false }
}

function downloadGradeTemplate() {
  window.open('/api/grades/template', '_blank')
}

onMounted(() => {
  loadGrades()
  if (authStore.canViewAllData) loadStudents()
  loadChangeRequests()
})
</script>

<style scoped>
.disclaimer-bar {
  display: flex; align-items: center; gap: 8px;
  background: #FFF8E1; border: 1px solid #FFE082; border-radius: 8px;
  padding: 10px 16px; margin-bottom: 16px;
  color: #F57F17; font-size: 13px; line-height: 1.6;
}

.gpa-summary {
  display: flex; justify-content: space-between; align-items: center;
  padding: 16px 20px; margin-bottom: 16px;
  border-radius: 8px; border: 1px solid #E5E6EB;
  background: var(--surface-soft); flex-wrap: wrap; gap: 12px;
}
.gpa-summary.gpa-warning {
  background: #FFF1F0; border-color: #FFA39E;
}
.gpa-main { display: flex; align-items: baseline; gap: 8px; }
.gpa-label { color: var(--el-text-color-regular); font-size: 14px; }
.gpa-value { font-size: 28px; font-weight: 700; color: var(--el-color-primary); }
.gpa-value.gpa-danger { color: #F53F3F; }
.gpa-total { color: var(--el-text-color-secondary); font-size: 13px; }
.gpa-alert {
  display: flex; align-items: center; gap: 6px;
  color: #F53F3F; font-size: 14px; font-weight: 600;
}
.gpa-pass {
  display: flex; align-items: center; gap: 6px;
  color: #2E7D32; font-size: 14px; font-weight: 500;
}

.admin-gpa-section {
  margin-bottom: 16px; padding: 16px;
  background: #FAFBFC; border: 1px solid #E5E6EB; border-radius: 8px;
}
.gpa-student-grid {
  display: grid; grid-template-columns: repeat(auto-fill, minmax(160px, 1fr)); gap: 10px;
}
.gpa-student-card {
  background: var(--surface); border: 1px solid #E5E6EB; border-radius: 8px;
  padding: 12px; text-align: center; transition: border-color 0.2s;
}
.gpa-student-card.gpa-student-danger {
  border-color: #FFA39E; background: #FFF1F0;
}
.gpa-student-name { font-weight: 600; font-size: 14px; color: var(--el-text-color-primary); }
.gpa-student-id { font-size: 12px; color: var(--el-text-color-secondary); margin-bottom: 6px; }
.gpa-student-value { font-size: 24px; font-weight: 700; color: var(--el-color-primary); }
.gpa-student-value.gpa-danger { color: #F53F3F; }
.gpa-student-warn {
  margin-top: 4px; font-size: 12px; color: #F53F3F;
  display: flex; align-items: center; justify-content: center; gap: 4px;
}

/* 修改申请 */
.change-request-item {
  display: flex; align-items: center; gap: 16px;
  padding: 10px 14px; background: var(--surface); border: 1px solid #FFE082;
  border-radius: 6px; margin-bottom: 8px; flex-wrap: wrap;
}
.cr-info { flex: 1; min-width: 200px; font-size: 13px; color: var(--el-text-color-regular); }
.cr-values { font-size: 13px; color: #E65100; white-space: nowrap; }
.cr-actions { display: flex; gap: 6px; flex-shrink: 0; }

.my-req-item {
  display: flex; align-items: center; gap: 12px;
  padding: 8px 14px; border-radius: 6px; margin-bottom: 6px;
  font-size: 13px; flex-wrap: wrap;
}
.my-req-item.req-pending { background: #FFF8E1; border: 1px solid #FFE082; }
.my-req-item.req-approved { background: #E8F5E9; border: 1px solid #A5D6A7; }
.my-req-item.req-rejected { background: #FFEBEE; border: 1px solid #EF9A9A; }
.req-detail { flex: 1; color: var(--el-text-color-regular); }
.req-comment { color: var(--el-text-color-secondary); font-size: 12px; width: 100%; margin-top: 4px; }

@media screen and (max-width: 768px) {
  .gpa-summary { flex-direction: column; align-items: flex-start; }
  .gpa-student-grid { grid-template-columns: repeat(auto-fill, minmax(130px, 1fr)); }
}
</style>
