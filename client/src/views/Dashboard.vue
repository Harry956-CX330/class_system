<template>
  <el-container class="admin-layout">
    <div 
      v-if="isMobile && isSidebarOpen" 
      class="mobile-overlay" 
      @click="isSidebarOpen = false"
    ></div>

    <el-aside 
      width="240px" 
      class="sidebar" 
      :class="{ 'is-mobile': isMobile, 'is-open': isSidebarOpen }"
    >
      <div class="logo-container">
        <div class="logo-text">
          <div class="logo-line1">sk2441班务</div>
          <div class="logo-line2">班级事务，有序进行</div>
          <div class="build-version" :title="'构建版本 ' + buildRevision">v{{ appVersion }} · {{ buildRevision }}</div>
        </div>
      </div>
      <el-menu
        :default-active="activeMenu"
        class="admin-menu"
        background-color="#1D1E26"
        text-color="#A9B1C0"
        active-text-color="#FFFFFF"
        router
        @select="handleMenuSelect"
      >
        <el-menu-item index="/dashboard">
          <el-icon><DataAnalysis /></el-icon>
          <span>首页统计</span>
        </el-menu-item>
        <el-menu-item index="/notices">
          <el-icon><Bell /></el-icon>
          <span>通知公告</span>
        </el-menu-item>

        <!-- 用户端菜单 -->
        <template v-if="currentView !== 'admin'">
          <el-menu-item index="/grades">
            <el-icon><Document /></el-icon>
            <span>成绩管理</span>
          </el-menu-item>
          <el-menu-item index="/certificates">
            <el-icon><Medal /></el-icon>
            <span>奖状管理</span>
          </el-menu-item>
          <el-menu-item index="/social-practice">
            <el-icon><Stamp /></el-icon>
            <span>社会实践</span>
          </el-menu-item>
          <el-menu-item index="/file-tasks">
            <el-icon><FolderOpened /></el-icon>
            <span>文件任务</span>
          </el-menu-item>
          <el-menu-item index="/textbook-order">
            <el-icon><Reading /></el-icon>
            <span>教材订购</span>
          </el-menu-item>
          <el-menu-item index="/surveys">
            <el-icon><EditPen /></el-icon>
            <span>调查问卷</span>
          </el-menu-item>
          <el-menu-item index="/class-meetings">
            <el-icon><Calendar /></el-icon>
            <span>班会管理</span>
          </el-menu-item>
          <el-menu-item index="/resources">
            <el-icon><Files /></el-icon>
            <span>资料下载</span>
          </el-menu-item>
          <el-menu-item index="/groups">
            <el-icon><UserFilled /></el-icon>
            <span>分组管理</span>
          </el-menu-item>
          <el-menu-item index="/activities">
            <el-icon><Trophy /></el-icon>
            <span>活动管理</span>
          </el-menu-item>
          <el-menu-item index="/qr-checkin">
            <el-icon><Aim /></el-icon>
            <span>扫码签到</span>
          </el-menu-item>
          <el-menu-item index="/sheet">
            <el-icon><Collection /></el-icon>
            <span>协作表格</span>
          </el-menu-item>
        </template>

        <!-- 管理端菜单 -->
        <template v-if="currentView === 'admin'">
          <el-menu-item index="/appearance"><el-icon><Picture /></el-icon><span>登录页外观</span></el-menu-item>
          <el-menu-item index="/grades">
            <el-icon><Document /></el-icon>
            <span>成绩管理</span>
          </el-menu-item>
          <el-menu-item index="/certificates">
            <el-icon><Medal /></el-icon>
            <span>奖状管理</span>
          </el-menu-item>
          <el-menu-item index="/social-practice">
            <el-icon><Stamp /></el-icon>
            <span>社会实践</span>
          </el-menu-item>
          <el-menu-item index="/file-tasks">
            <el-icon><FolderOpened /></el-icon>
            <span>文件任务</span>
          </el-menu-item>
          <el-menu-item index="/users">
            <el-icon><UserFilled /></el-icon>
            <span>用户管理</span>
          </el-menu-item>
          <el-menu-item index="/resources/manage">
            <el-icon><FolderAdd /></el-icon>
            <span>资料管理</span>
          </el-menu-item>
          <el-menu-item index="/groups">
            <el-icon><UserFilled /></el-icon>
            <span>分组管理</span>
          </el-menu-item>
          <el-menu-item index="/surveys">
            <el-icon><EditPen /></el-icon>
            <span>调查问卷</span>
          </el-menu-item>
          <el-menu-item index="/class-meetings">
            <el-icon><Calendar /></el-icon>
            <span>班会管理</span>
          </el-menu-item>
          <el-menu-item index="/survey-editor">
            <el-icon><EditPen /></el-icon>
            <span>问卷编辑</span>
          </el-menu-item>
          <el-menu-item index="/activities">
            <el-icon><Trophy /></el-icon>
            <span>活动管理</span>
          </el-menu-item>
          <el-menu-item index="/qr-checkin/manage">
            <el-icon><Aim /></el-icon>
            <span>扫码签到</span>
          </el-menu-item>
          <el-menu-item index="/textbook-order">
            <el-icon><Reading /></el-icon>
            <span>教材订购</span>
          </el-menu-item>
          <el-menu-item index="/sheet">
            <el-icon><Collection /></el-icon>
            <span>协作表格</span>
          </el-menu-item>
          <el-menu-item index="/email-settings">
            <el-icon><Message /></el-icon>
            <span>邮件设置</span>
          </el-menu-item>
          <el-menu-item index="/qq-settings">
            <el-icon><ChatDotSquare /></el-icon>
            <span>QQ提醒</span>
          </el-menu-item>
          <el-menu-item index="/class-committee">
            <el-icon><User /></el-icon>
            <span>班委通讯录</span>
          </el-menu-item>
        </template>
      </el-menu>
    </el-aside>

    <el-container class="main-container">
      <el-header class="admin-header">
        <div class="header-left">
          <el-icon 
            v-if="isMobile" 
            class="menu-toggle-btn" 
            @click="isSidebarOpen = !isSidebarOpen"
          >
            <Fold v-if="!isSidebarOpen" />
            <Expand v-else />
          </el-icon>
          <span class="page-title hide-on-tiny">{{ pageTitle }}</span>
        </div>
        
        <div class="header-right">
          <ThemeSwitch />
          <el-tag 
            size="small" 
            :type="currentView === 'admin' ? 'danger' : authStore.isClassLeader ? 'warning' : 'primary'" 
            effect="light"
            class="role-tag"
          >
            {{ currentView === 'admin' ? '管理端' : authStore.isClassLeader ? '班干(用户端)' : '学生' }}
          </el-tag>

          <el-button 
            v-if="authStore.isClassLeader"
            type="primary" 
            size="small" 
            plain
            class="switch-view-btn"
            :aria-label="currentView === 'admin' ? '切换用户端' : '切换管理端'"
            @click="switchView"
          >
            <el-icon><Switch /></el-icon>
            <span class="switch-view-label">{{ currentView === 'admin' ? '切换用户端' : '切换管理端' }}</span><span class="switch-view-short">切换</span>
          </el-button>
          
          <InstallApp />
          <el-dropdown trigger="click" @command="handleCommand">
            <div class="user-dropdown">
              <el-avatar :size="32" style="background-color: #165DFF">
                {{ (authStore.user?.real_name || authStore.user?.username)?.charAt(0) || 'U' }}
              </el-avatar>
              <span class="username hide-on-mobile">{{ authStore.user?.real_name || authStore.user?.username }}</span>
              <el-icon class="hide-on-mobile"><CaretBottom /></el-icon>
            </div>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="profile">
                  <el-icon><User /></el-icon>个人信息
                </el-dropdown-item>
                <el-dropdown-item divided command="logout" style="color: #F56C6C">
                  <el-icon><SwitchButton /></el-icon>退出登录
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </el-header>

      <el-main class="admin-main">
        <div v-if="route.path === '/dashboard'" class="dashboard-page">
          <div class="welcome-card">
            <div class="welcome-info">
              <h2>欢迎进入智能班务系统</h2>
              <p>你好，{{ authStore.user?.real_name || authStore.user?.username }}！今天是高效管理班级事务的一天。</p>
              <div class="welcome-stats">
                <div class="welcome-stat-item">
                  <span class="stat-num">{{ usageStats.total_users || 0 }}</span>
                  <span class="stat-label">班级成员</span>
                </div>
                <div class="welcome-stat-divider"></div>
                <div class="welcome-stat-item">
                  <span class="stat-num">{{ usageStats.total_visits || 0 }}</span>
                  <span class="stat-label">累计访次</span>
                </div>
                <div class="welcome-stat-divider"></div>
                <div class="welcome-stat-item">
                  <span class="stat-num">{{ usageStats.total_pv || 0 }}</span>
                  <span class="stat-label">累计点击</span>
                </div>
              </div>
            </div>
            <img v-if="!isMobile" src="/icons/crest.webp" alt="sk2441班徽" class="welcome-img"/>
          </div>

          <div class="section-title">获奖统计</div>
          <el-row :gutter="isMobile ? 12 : 20">
            <el-col :xs="12" :sm="12" :md="6" class="data-col">
              <el-card class="data-card" shadow="never">
                <div class="card-content">
                  <div class="card-info">
                    <div class="card-title">获奖总数</div>
                    <div class="card-value">{{ certStats.total }}</div>
                  </div>
                  <div class="card-icon icon-primary">
                    <el-icon><Trophy /></el-icon>
                  </div>
                </div>
              </el-card>
            </el-col>
            <el-col :xs="12" :sm="12" :md="6" class="data-col">
              <el-card class="data-card" shadow="never">
                <div class="card-content">
                  <div class="card-info">
                    <div class="card-title">国家级奖项</div>
                    <div class="card-value">{{ certStats.national_count }}</div>
                  </div>
                  <div class="card-icon icon-warning">
                    <el-icon><Star /></el-icon>
                  </div>
                </div>
              </el-card>
            </el-col>
            <el-col :xs="12" :sm="12" :md="6" class="data-col">
              <el-card class="data-card" shadow="never">
                <div class="card-content">
                  <div class="card-info">
                    <div class="card-title">省级奖项</div>
                    <div class="card-value">{{ certStats.provincial_count }}</div>
                  </div>
                  <div class="card-icon icon-success">
                    <el-icon><Medal /></el-icon>
                  </div>
                </div>
              </el-card>
            </el-col>
            <el-col :xs="12" :sm="12" :md="6" class="data-col">
              <el-card class="data-card" shadow="never">
                <div class="card-content">
                  <div class="card-info">
                    <div class="card-title">校级奖项</div>
                    <div class="card-value">{{ certStats.school_count }}</div>
                  </div>
                  <div class="card-icon icon-info">
                    <el-icon><School /></el-icon>
                  </div>
                </div>
              </el-card>
            </el-col>
          </el-row>

          <div class="section-title">班级活跃度统计</div>
          <el-row :gutter="isMobile ? 12 : 20">
            <el-col :xs="12" :sm="12" :md="8" class="data-col">
              <el-card class="data-card" shadow="never">
                <div class="card-content">
                  <div class="card-info">
                    <div class="card-title">累计获奖人数</div>
                    <div class="card-value">{{ certStats.student_count }}</div>
                  </div>
                  <div class="card-icon icon-purple hide-on-tiny-icon">
                    <el-icon><User /></el-icon>
                  </div>
                </div>
              </el-card>
            </el-col>
            <el-col :xs="12" :sm="12" :md="8" class="data-col">
              <el-card class="data-card" shadow="never">
                <div class="card-content">
                  <div class="card-info">
                    <div class="card-title">社会实践总次</div>
                    <div class="card-value">{{ spStats.total }}</div>
                  </div>
                  <div class="card-icon icon-warning hide-on-tiny-icon">
                    <el-icon><Compass /></el-icon>
                  </div>
                </div>
              </el-card>
            </el-col>
            <el-col :xs="24" :sm="12" :md="8" class="data-col">
              <el-card class="data-card" shadow="never">
                <div class="card-content">
                  <div class="card-info">
                    <div class="card-title">实践参与人数</div>
                    <div class="card-value">{{ spStats.student_count }}</div>
                  </div>
                  <div class="card-icon icon-primary hide-on-tiny-icon">
                    <el-icon><UserFilled /></el-icon>
                  </div>
                </div>
              </el-card>
            </el-col>
          </el-row>

          <div class="section-title">政治面貌统计</div>
          <el-row :gutter="isMobile ? 12 : 20">
            <el-col :xs="12" :sm="12" :md="6" class="data-col">
              <el-card class="data-card" shadow="never">
                <div class="card-content">
                  <div class="card-info">
                    <div class="card-title">正式党员</div>
                    <div class="card-value">{{ politicalStats.party_member }}</div>
                  </div>
                  <div class="card-icon icon-danger hide-on-tiny-icon">
                    <el-icon><Star /></el-icon>
                  </div>
                </div>
              </el-card>
            </el-col>
            <el-col :xs="12" :sm="12" :md="6" class="data-col">
              <el-card class="data-card" shadow="never">
                <div class="card-content">
                  <div class="card-info">
                    <div class="card-title">预备党员</div>
                    <div class="card-value">{{ politicalStats.probationary }}</div>
                  </div>
                  <div class="card-icon icon-warning hide-on-tiny-icon">
                    <el-icon><Sunny /></el-icon>
                  </div>
                </div>
              </el-card>
            </el-col>
            <el-col :xs="12" :sm="12" :md="6" class="data-col">
              <el-card class="data-card" shadow="never">
                <div class="card-content">
                  <div class="card-info">
                    <div class="card-title">共青团员</div>
                    <div class="card-value">{{ politicalStats.league_member + politicalStats.party_member + politicalStats.probationary }}</div>
                  </div>
                  <div class="card-icon icon-primary hide-on-tiny-icon">
                    <el-icon><Stamp /></el-icon>
                  </div>
                </div>
              </el-card>
            </el-col>
            <el-col :xs="12" :sm="12" :md="6" class="data-col">
              <el-card class="data-card" shadow="never">
                <div class="card-content">
                  <div class="card-info">
                    <div class="card-title">群众 / 其他</div>
                    <div class="card-value">{{ politicalStats.masses + politicalStats.other }}</div>
                  </div>
                  <div class="card-icon icon-info hide-on-tiny-icon">
                    <el-icon><User /></el-icon>
                  </div>
                </div>
              </el-card>
            </el-col>
          </el-row>

          <div class="notice-section">
            <div class="section-header">
              <div class="section-title" style="margin-top: 0; margin-bottom: 0;">最新通知</div>
              <el-button v-if="recentNotices.length >= 5" type="primary" link @click="router.push('/notices')">
                查看更多 <el-icon class="el-icon--right"><ArrowRight /></el-icon>
              </el-button>
            </div>
            
            <el-card class="table-card" shadow="never" :body-style="isMobile ? { padding: '0' } : {}">
              <!-- PC 端表格视图 -->
              <el-table 
                v-if="!isMobile"
                :data="recentNotices" 
                v-loading="noticeLoading" 
                style="width: 100%"
                :header-cell-style="{ background: '#F7F8FA', color: '#4E5969', fontWeight: '500' }"
              >
                <el-table-column prop="title" label="公告标题" min-width="150" show-overflow-tooltip>
                  <template #default="{ row }">
                    <span class="notice-title">{{ row.title }}</span>
                  </template>
                </el-table-column>
                <el-table-column prop="author_name" label="发布人" width="100" />
                <el-table-column prop="created_at" label="发布时间" width="160">
                  <template #default="{ row }">
                    <span class="notice-time">{{ new Date(row.created_at).toLocaleString('zh-CN', { hour12: false }) }}</span>
                  </template>
                </el-table-column>
                <el-table-column type="expand">
                  <template #default="{ row }">
                    <RichContent class="notice-content" :content="row.content" />
                  </template>
                </el-table-column>
              </el-table>

              <!-- 移动端原生列表视图 -->
              <div v-else class="mobile-notice-list" v-loading="noticeLoading">
                <div 
                  v-for="row in recentNotices" 
                  :key="row.id" 
                  class="mobile-notice-item"
                  @click="router.push('/notices')"
                >
                  <div class="mn-header">
                    <span class="mn-title">{{ row.title }}</span>
                    <span class="mn-author">{{ row.author_name }}</span>
                  </div>
                  <RichContent class="mn-content" :content="row.content" />
                </div>
                <el-empty v-if="!recentNotices.length" description="暂无最新通知" :image-size="60" />
              </div>
            </el-card>
          </div>
        </div>
        
        <div class="page-container" v-else>
          <router-view />
        </div>
      </el-main>
      <nav class="mobile-dock" aria-label="快捷导航"><router-link to="/dashboard">首页</router-link><router-link to="/notices">公告</router-link><router-link to="/file-tasks">文件任务</router-link><router-link to="/surveys">问卷</router-link></nav>
  </el-container>

    <!-- 班委通讯录悬浮按钮 -->
    <div
      class="floating-help-btn"
    >
      <button class="help-toggle" aria-label="班委联系方式" :aria-expanded="showCommittee" @click.stop="showCommittee=!showCommittee" @keydown.esc="showCommittee=false"><el-icon :size="22"><QuestionFilled /></el-icon></button>
      <Transition name="committee-pop">
        <div v-if="showCommittee" class="committee-popup" role="region" aria-label="班委联系信息" tabindex="0" @keydown.esc="showCommittee=false">
          <button class="help-close" aria-label="关闭联系方式" @click.stop="showCommittee=false">关闭 ×</button>
          <template v-if="counselorInfo && (counselorInfo.name || counselorInfo.phone || counselorInfo.qq_number)">
            <div class="popup-title counselor-title">
              辅导员
              <span class="counselor-name" v-if="counselorInfo.name">{{ counselorInfo.name }}</span>
            </div>
            <div class="popup-contact counselor-contact">
              <span v-if="counselorInfo.office">办公室: {{ counselorInfo.office }}</span>
              <span v-if="counselorInfo.phone">手机: {{ counselorInfo.phone }}</span>
              <span v-if="counselorInfo.qq_number">QQ: {{ counselorInfo.qq_number }}</span>
            </div>
            <div class="popup-divider"></div>
          </template>
          <div class="popup-title">班委联系方式</div>
          <div class="popup-list">
            <div v-for="c in committeeList" :key="c.id" class="popup-item">
              <div class="popup-item-header">
                <span class="popup-name">{{ c.real_name }}</span>
                <span class="popup-position" v-if="c.class_position">{{ c.class_position }}</span>
              </div>
              <div class="popup-contact">
                <span v-if="c.dorm">宿舍: {{ c.dorm }}</span>
                <span v-if="c.phone">手机: {{ c.phone }}</span>
              </div>
              <div class="popup-contact" v-if="c.qq_number" style="margin-top: 2px;">
                <span>QQ: {{ c.qq_number }}</span>
              </div>
            </div>
          </div>
          <el-empty v-if="!committeeList.length && !(counselorInfo && counselorInfo.name)" description="暂无联系信息" :image-size="60" />
        </div>
      </Transition>
    </div>

    <!-- 紧急通知弹窗 -->
    <el-dialog
      v-model="urgentDialogVisible"
      :title="'[紧急通知] ' + urgentNotice.title"
      :width="isMobile ? '100%' : '560px'"
      :fullscreen="isMobile"
      :close-on-click-modal="false"
      :close-on-press-escape="false"
      :show-close="false"
      class="urgent-notice-dialog"
    >
      <RichContent class="urgent-content" :content="urgentNotice.content" />
      <div class="urgent-meta">
        <span>发布人：{{ urgentNotice.author_name || '管理员' }}</span>
        <span>{{ formatUrgentTime(urgentNotice.created_at) }}</span>
      </div>
      <template #footer>
        <div class="urgent-footer">
          <div v-if="urgentCountdown > 0" class="countdown-text">
            请仔细阅读，{{ urgentCountdown }} 秒后可关闭
          </div>
          <el-button 
            type="primary" 
            :disabled="urgentCountdown > 0" 
            @click="urgentDialogVisible = false"
            class="urgent-btn"
          >
            {{ urgentCountdown > 0 ? `请等待 ${urgentCountdown}s` : '我已阅读，关闭' }}
          </el-button>
        </div>
      </template>
    </el-dialog>
  </el-container>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onUnmounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessageBox } from 'element-plus'
import { useAuthStore } from '../stores/auth'
import api from '../api'
import InstallApp from '../components/InstallApp.vue'
import ThemeSwitch from '../components/ThemeSwitch.vue'
const appVersion = __APP_VERSION__
const buildRevision = __APP_REVISION__

import { 
  DataAnalysis, Bell, Document, Medal, Stamp, FolderOpened, 
  EditPen, Calendar, Files, FolderAdd, UserFilled, CaretBottom, User, 
  SwitchButton, Trophy, Star, School, Compass, ArrowRight, Sunny, Message, Collection,
  Fold, Expand, Reading, ChatDotSquare, Switch, QuestionFilled, Picture, Aim
} from '@element-plus/icons-vue'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()

// 视图模式：超管固定管理端，班干按选择，学生固定用户端
const currentView = computed(() => {
  if (authStore.user?.role === 'admin') return 'admin'
  return authStore.currentView || 'user'
})

// 响应式状态管理
const isMobile = ref(false)
const isSidebarOpen = ref(false)

const checkDevice = () => {
  isMobile.value = window.innerWidth <= 1024
  if (!isMobile.value) {
    isSidebarOpen.value = true // 电脑端默认展开
  } else {
    isSidebarOpen.value = false // 移动端默认收起
  }
}

const activeMenu = computed(() => {
  const path = route.path
  if (path === '/' || path === '/dashboard') return '/dashboard'
  return '/' + path.split('/')[1]
})

const pageTitle = computed(() => {
  const map = {
    '/dashboard': '首页统计', '/notices': '通知公告', '/grades': '成绩管理',
    '/certificates': '奖状管理', '/social-practice': '社会实践',
    '/file-tasks': '文件任务', '/textbook-order': '教材订购', '/surveys': '调查问卷',
    '/groups': '分组管理',
    '/class-meetings': '班会管理', '/resources/manage': '资料管理', '/resources': '资料下载',
    '/activities': '活动管理',
    '/qr-checkin': '扫码签到', '/qr-checkin/manage': '扫码签到管理',
    '/sheet': '在线协作表格',
    '/email-settings': '邮件设置',
    '/qq-settings': 'QQ提醒', '/class-committee': '班委通讯录',
    '/users': '用户管理', '/profile': '个人信息',
  }
  return map[route.path] || route.meta?.title || '工作台'
})

const certStats = ref({ total: 0, national_count: 0, provincial_count: 0, school_count: 0, student_count: 0 })
const spStats = ref({ total: 0, student_count: 0, estimated_hours: 0 })
const politicalStats = ref({ party_member: 0, probationary: 0, league_member: 0, masses: 0, other: 0, total: 0 })
const usageStats = ref({ total_users: 0, total_visits: 0, total_pv: 0 })
const recentNotices = ref([])
const noticeLoading = ref(false)
const showCommittee = ref(false)
const committeeList = ref([])
const counselorInfo = ref(null)

async function fetchStats() {
  try {
    const [certRes, spRes, polRes] = await Promise.allSettled([
      api.get('/api/certificates/stats'),
      api.get('/api/social-practices/stats'),
      api.get('/api/dashboard/political-stats'),
    ])
    if (certRes.status === 'fulfilled') certStats.value = certRes.value.data
    if (spRes.status === 'fulfilled') spStats.value = spRes.value.data
    if (polRes.status === 'fulfilled') politicalStats.value = polRes.value.data
  } catch {}

  fetchUsageStats()
}

async function fetchUsageStats() {
  try {
    const [statsRes] = await Promise.allSettled([
      api.get('/api/dashboard/usage-stats'),
    ])
    if (statsRes.status === 'fulfilled') usageStats.value = statsRes.value.data
    // 标记一次页面访问
    await api.post('/api/dashboard/ping').catch(() => {})
    // 重新获取以得到最新的PV
    const res = await api.get('/api/dashboard/usage-stats')
    usageStats.value = res.data
  } catch {}
}

async function fetchNotices() {
  noticeLoading.value = true
  try {
    const res = await api.get('/api/notices')
    recentNotices.value = res.data.slice(0, 5)
  } catch {} finally {
    noticeLoading.value = false
  }
}

// 紧急通知
const urgentNotice = reactive({ title: '', content: '', author_name: '', created_at: '' })
const urgentDialogVisible = ref(false)
const urgentCountdown = ref(5)
let urgentTimer = null

function formatUrgentTime(t) {
  if (!t) return ''
  return new Date(t).toLocaleString('zh-CN', { hour12: false })
}

async function fetchUrgentNotice() {
  try {
    const res = await api.get('/api/notices/urgent')
    const n = res.data
    if (!n || !n.title) return
    urgentNotice.title = n.title || ''
    urgentNotice.content = n.content || ''
    urgentNotice.author_name = n.author_name || ''
    urgentNotice.created_at = n.created_at || ''
    urgentDialogVisible.value = true
    urgentCountdown.value = 5
    urgentTimer = setInterval(() => {
      if (urgentCountdown.value > 0) {
        urgentCountdown.value--
      } else {
        clearInterval(urgentTimer)
        urgentTimer = null
      }
    }, 1000)
  } catch {
    // 没有紧急通知，正常跳过
  }
}

function handleMenuSelect() {
  if (isMobile.value) {
    isSidebarOpen.value = false
  }
}

function handleCommand(command) {
  if (command === 'logout') {
    handleLogout()
  } else if (command === 'profile') {
    router.push('/profile')
  }
}

function switchView() {
  const newView = currentView.value === 'admin' ? 'user' : 'admin'
  authStore.setView(newView)
  router.push('/dashboard')
}

function handleLogout() {
  ElMessageBox.confirm('确定要退出登录吗？', '系统提示', { 
    confirmButtonText: '确定退出',
    cancelButtonText: '取消',
    type: 'warning' 
  }).then(() => {
    authStore.logout()
    router.push('/login')
  }).catch(() => {})
}

async function fetchCommittee() {
  try {
    const res = await api.get('/api/class-committee')
    committeeList.value = res.data
  } catch {
    // 静默失败
  }
}

async function fetchCounselor() {
  try {
    const res = await api.get('/api/counselor')
    counselorInfo.value = res.data
  } catch {
    // 静默失败
  }
}

onMounted(() => {
  checkDevice()
  window.addEventListener('resize', checkDevice)
  fetchStats()
  fetchNotices()
  fetchUrgentNotice()
  fetchCommittee()
  fetchCounselor()
})

onUnmounted(() => {
  window.removeEventListener('resize', checkDevice)
  if (urgentTimer) clearInterval(urgentTimer)
})
</script>

<style scoped>
/* 全局布局配置 */
.admin-layout {
  min-height: 100vh;
  background-color: var(--el-bg-color-page);
  overflow-x: hidden;
}

/* ================= 侧边栏及响应式处理 ================= */
.sidebar {
  background-color: #1D1E26;
  box-shadow: 2px 0 8px 0 rgba(29, 35, 41, 0.05);
  z-index: 1001; 
  transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  display: flex;
  flex-direction: column;
  height: 100vh; 
  height: 100dvh; 
}

.sidebar.is-mobile {
  position: fixed;
  top: 0;
  bottom: 0;
  left: 0;
  transform: translateX(-100%);
}

.sidebar.is-mobile.is-open {
  transform: translateX(0);
}

.mobile-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(0, 0, 0, 0.5);
  z-index: 1000;
}

.logo-container {
  height: 60px;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: #1D1E26;
  color: #fff;
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
}

.logo-text {
  text-align: center;
}

.logo-line1 {
  font-size: 16px;
  font-weight: 600;
  letter-spacing: 1px;
}

.logo-line2 {
  font-size: 12px;
  color: #A9B1C0;
  margin-top: 4px;
}

.admin-menu {
  border-right: none;
  flex: 1; 
  overflow-y: auto;
  overflow-x: hidden;
  padding-bottom: 30px; 
}

.admin-menu::-webkit-scrollbar {
  width: 4px;
}
.admin-menu::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, 0.2);
  border-radius: 4px;
}

.admin-menu :deep(.el-menu-item) {
  margin: 4px 12px;
  border-radius: 8px;
  height: 48px;
  line-height: 48px;
}

.admin-menu :deep(.el-menu-item.is-active) {
  background-color: #165DFF !important;
  color: #fff !important;
  font-weight: 500;
}

/* ================= 顶部导航 ================= */
.admin-header {
  background: var(--surface);
  box-shadow: 0 1px 4px rgba(0, 21, 41, 0.08);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  height: 60px;
  z-index: 999;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 16px;
}

.menu-toggle-btn {
  font-size: 20px;
  cursor: pointer;
  color: var(--el-text-color-regular);
  transition: color 0.3s;
}

.menu-toggle-btn:hover {
  color: var(--el-color-primary);
}

.page-title {
  font-size: 18px;
  font-weight: 600;
  color: var(--el-text-color-primary);
}

.header-right {
  display: flex;
  align-items: center;
}

.role-tag {
  margin-right: 8px;
  border-radius: 4px;
}

.switch-view-btn {
  margin-right: 16px;
}

.user-dropdown {
  display: flex;
  align-items: center;
  cursor: pointer;
  padding: 4px 8px;
  border-radius: 6px;
  transition: background 0.3s;
}

.user-dropdown:hover {
  background: var(--el-bg-color-page);
}

.username {
  margin: 0 8px;
  font-size: 14px;
  color: var(--el-text-color-regular);
  font-weight: 500;
}

/* ================= 主内容区域 ================= */
.admin-main {
  padding: 24px;
  height: calc(100vh - 60px);
  overflow-y: auto;
  box-sizing: border-box;
}

.page-container {
  background: var(--surface);
  border-radius: 8px;
  padding: 24px;
  min-height: calc(100vh - 108px);
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.05);
}

.welcome-card {
  background: var(--surface);
  border-radius: 8px;
  padding: 24px 32px;
  margin-bottom: 24px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  box-shadow: 0 2px 8px 0 rgba(0, 0, 0, 0.04);
  border-left: 6px solid #165DFF;
}

.welcome-info h2 {
  margin: 0 0 12px 0;
  font-size: 24px;
  color: var(--el-text-color-primary);
  font-weight: 600;
}

.welcome-info p {
  margin: 0;
  font-size: 14px;
  color: var(--el-text-color-secondary);
  line-height: 1.5;
}

.welcome-stats {
  display: flex;
  align-items: center;
  margin-top: 16px;
  gap: 0;
}

.welcome-stat-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  min-width: 80px;
}

.welcome-stat-item .stat-num {
  font-size: 22px;
  font-weight: 700;
  color: var(--el-color-primary);
  line-height: 1.2;
}

.welcome-stat-item .stat-label {
  font-size: 12px;
  color: var(--el-text-color-secondary);
  margin-top: 2px;
}

.welcome-stat-divider {
  width: 1px;
  height: 32px;
  background: #E5E6EB;
  margin: 0 24px;
}

.welcome-img {
  height: 80px;
  opacity: 0.9;
}

.section-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--el-text-color-primary);
  margin-bottom: 16px;
  margin-top: 8px;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 16px;
  margin-bottom: 16px;
}

.data-col {
  margin-bottom: 20px;
}

.data-card {
  border: none;
  border-radius: 8px;
  box-shadow: 0 2px 8px 0 rgba(0, 0, 0, 0.04);
  transition: all 0.3s;
  height: 100%;
}

.data-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 16px 0 rgba(0, 0, 0, 0.08);
}

.card-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 4px;
}

.card-title {
  font-size: 14px;
  color: var(--el-text-color-secondary);
  margin-bottom: 4px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.card-value {
  font-size: 28px;
  font-weight: 700;
  color: var(--el-text-color-primary);
  font-family: 'DIN Alternate', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
  overflow: hidden;
  text-overflow: ellipsis;
}

.card-icon {
  width: 52px;
  height: 52px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
  flex-shrink: 0;
}

.icon-primary { background: var(--el-color-primary-light-9); color: var(--el-color-primary); }
.icon-success { background: #E8FFEA; color: #00B42A; }
.icon-warning { background: #FFF7E8; color: #FF7D00; }
.icon-info { background: var(--el-bg-color-page); color: var(--el-text-color-regular); }
.icon-purple { background: #F2E8FF; color: #722ED1; }
.icon-danger { background: #FFECE8; color: #F53F3F; }

.table-card {
  border: none;
  border-radius: 8px;
  box-shadow: 0 2px 8px 0 rgba(0, 0, 0, 0.04);
}

.notice-title {
  font-weight: 500;
  color: var(--el-text-color-primary);
}

.notice-time {
  color: var(--el-text-color-secondary);
  font-size: 13px;
}

.notice-content {
  padding: 16px 24px;
  background-color: var(--surface-soft);
  border-radius: 6px;
  margin: 0 12px;
  white-space: pre-wrap;
  line-height: 1.8;
  color: var(--el-text-color-regular);
}

:deep(.el-table::before) {
  display: none;
}

/* ================= 移动端原生列表卡片视图 ================= */
.mobile-notice-list {
  display: flex;
  flex-direction: column;
}

.mobile-notice-item {
  padding: 16px;
  border-bottom: 1px solid #F2F3F5;
  cursor: pointer;
  transition: background-color 0.2s;
}

.mobile-notice-item:active {
  background-color: var(--surface-soft);
}

.mobile-notice-item:last-child {
  border-bottom: none;
}

.mn-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 8px;
}

.mn-title {
  font-weight: 600;
  color: var(--el-text-color-primary);
  font-size: 15px;
  flex: 1;
  padding-right: 12px;
  line-height: 1.4;
}

.mn-author {
  font-size: 12px;
  color: var(--el-text-color-secondary);
  white-space: nowrap;
}

.mn-content {
  font-size: 13px;
  color: var(--el-text-color-regular);
  line-height: 1.6;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  word-break: break-all;
}

/* 紧急通知弹窗 */
:deep(.urgent-notice-dialog) {
  border-radius: 12px;
}

:deep(.urgent-notice-dialog .el-dialog__header) {
  background: linear-gradient(135deg, #F53F3F 0%, #E03030 100%);
  color: #fff;
  padding: 16px 24px;
  border-radius: 12px 12px 0 0;
  margin-right: 0;
}

:deep(.urgent-notice-dialog .el-dialog__title) {
  color: #fff;
  font-size: 17px;
  font-weight: 600;
}

.urgent-content {
  white-space: pre-wrap;
  line-height: 1.9;
  color: var(--el-text-color-primary);
  font-size: 15px;
  padding: 8px 0;
  min-height: 80px;
}

.urgent-meta {
  display: flex;
  justify-content: space-between;
  color: var(--el-text-color-secondary);
  font-size: 13px;
  margin-top: 16px;
  padding-top: 12px;
  border-top: 1px solid #F2F3F5;
}

.urgent-footer {
  display: flex;
  justify-content: flex-end;
  align-items: center;
  gap: 16px;
}

.countdown-text {
  color: #F53F3F;
  font-size: 14px;
  font-weight: 600;
}

/* ================= 移动端细节微调 ================= */
@media screen and (max-width: 768px) {
  .admin-header {
    padding: 0 16px;
  }
  
  .header-left {
    gap: 10px;
  }
  
  .switch-view-btn {
    margin-right: 8px;
  }
  
  .admin-main {
    padding: 16px;
  }
  
  .welcome-card {
    padding: 20px;
    border-left-width: 4px;
  }
  
  .welcome-info h2 {
    font-size: 18px;
  }
  
  .hide-on-mobile {
    display: none;
  }
  
  /* 在极小屏幕下隐藏页面标题，防止和右侧按钮挤压 */
  @media screen and (max-width: 400px) {
    .hide-on-tiny {
      display: none;
    }
    
    /* 缩小卡片内边距，隐藏部分图标以节省空间 */
    :deep(.el-card__body) {
      padding: 16px;
    }
    .card-title {
      font-size: 13px;
    }
    .card-value {
      font-size: 22px;
    }
    .hide-on-tiny-icon {
      display: none;
    }
  }

  .page-container {
    padding: 16px;
  }

  /* 修复全屏紧急通知的圆角 */
  :deep(.urgent-notice-dialog.is-fullscreen) {
    border-radius: 0;
  }
  :deep(.urgent-notice-dialog.is-fullscreen .el-dialog__header) {
    border-radius: 0;
  }
  
  /* 移动端底部按钮垂直排布更适合点击 */
  .urgent-footer {
    flex-direction: column;
    align-items: stretch;
    gap: 12px;
  }
  .countdown-text {
    text-align: center;
  }
  .urgent-btn {
    margin-left: 0 !important;
  }
}

/* 悬浮帮助按钮 */
.floating-help-btn {
  position: fixed;
  right: 24px;
  bottom: 40px;
  z-index: 1000;
  width: 48px;
  height: 48px;
  border-radius: 50%;
  background: #165DFF;
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  box-shadow: 0 4px 16px rgba(22, 93, 255, 0.35);
  transition: all 0.3s;
  user-select: none;
}

.floating-help-btn:hover {
  transform: scale(1.1);
  box-shadow: 0 6px 24px rgba(22, 93, 255, 0.5);
}

.committee-popup {
  position: absolute;
  right: 56px;
  bottom: 0;
  width: 260px;
  max-height: 360px;
  overflow-y: auto;
  background: var(--surface);
  border-radius: 12px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.12);
  padding: 16px;
}

.popup-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--el-text-color-primary);
  margin-bottom: 12px;
  padding-bottom: 8px;
  border-bottom: 1px solid #E5E6EB;
}

.popup-item {
  padding: 10px 0;
  border-bottom: 1px solid #F2F3F5;
}

.popup-item:last-child {
  border-bottom: none;
}

.popup-item-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
}

.popup-name {
  font-weight: 600;
  color: var(--el-text-color-primary);
  font-size: 14px;
}

.popup-position {
  font-size: 12px;
  color: var(--el-color-primary);
  background: var(--el-color-primary-light-9);
  padding: 2px 8px;
  border-radius: 4px;
}

.popup-contact {
  font-size: 12px;
  color: var(--el-text-color-secondary);
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

.popup-divider {
  height: 1px;
  background: #E5E6EB;
  margin: 12px 0;
}

.counselor-title {
  border-bottom: none;
  margin-bottom: 8px;
  padding-bottom: 0;
}

.counselor-name {
  font-weight: 400;
  font-size: 13px;
  color: var(--el-text-color-regular);
}

.counselor-contact {
  flex-direction: column;
  gap: 4px;
}

/* 弹出动画 */
.committee-pop-enter-active {
  transition: all 0.25s ease;
}
.committee-pop-leave-active {
  transition: all 0.15s ease;
}
.committee-pop-enter-from {
  opacity: 0;
  transform: translateX(10px);
}
.committee-pop-leave-to {
  opacity: 0;
  transform: translateX(10px);
}

@media screen and (max-width: 768px) {
  .floating-help-btn {
    right: 12px;
    bottom: 24px;
    width: 44px;
    height: 44px;
  }
  .committee-popup {
    right: 50px;
    width: 240px;
    max-height: 300px;
  }
}
</style>
