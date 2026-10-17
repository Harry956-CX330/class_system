<template>
  <div class="textbook-container">
    <!-- 公告通知关联展示 -->
    <div v-if="noticeContent" class="notice-banner">
      <div class="notice-icon"><el-icon><Bell /></el-icon></div>
      <div class="notice-text">{{ noticeContent }}</div>
    </div>

    <!-- 截止时间倒计时 -->
    <div v-if="config.deadline" class="deadline-bar" :class="{ 'deadline-over': isDead }">
      <el-icon><Clock /></el-icon>
      <span v-if="isDead">订购已截止（截止时间：{{ formatTime(config.deadline) }}）</span>
      <span v-else>订购截止时间：{{ formatTime(config.deadline) }}（剩余 {{ countdown }}）</span>
    </div>

    <!-- 联系班干 -->
    <div v-if="contactPerson && !authStore.canViewAllData" class="contact-bar">
      <el-icon><UserFilled /></el-icon>
      <span>教材订购联系人：<strong>{{ contactPerson.real_name }}</strong>
        <template v-if="contactPerson.qq_number">（QQ: {{ contactPerson.qq_number }}）</template>
      </span>
    </div>

    <el-card class="page-card" shadow="never">
      <div class="page-header">
        <div class="header-left">
          <div class="title-indicator"></div>
          <h3 class="page-title">教材订购</h3>
        </div>
        <div class="header-actions">
          <template v-if="!authStore.canViewAllData">
            <el-select v-model="courseFilter" placeholder="全部类型" size="default" style="width: 110px;" @change="loadData">
              <el-option label="全部" value="" />
              <el-option label="必修" value="必修" />
              <el-option label="选修" value="选修" />
            </el-select>
          </template>
          <el-button v-if="authStore.canViewAllData" type="primary" :icon="Plus" @click="openCreateDialog">新增教材</el-button>
          <el-dropdown v-if="authStore.canViewAllData" style="margin-left: 0;">
            <el-button type="success" :icon="Download">
              导出明细<el-icon class="el-icon--right"><ArrowDown /></el-icon>
            </el-button>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item @click="exportOrders">导出Excel（全部）</el-dropdown-item>
                <el-dropdown-item @click="exportByDormExcel">导出Excel（按宿舍）</el-dropdown-item>
                <el-dropdown-item @click="exportByStudentId">导出Excel（按学号）</el-dropdown-item>
                <el-dropdown-item @click="exportByDormWord">导出Word（按宿舍）</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
          <el-button v-if="authStore.canViewAllData" type="warning" :icon="Message" @click="sendOrderEmails" :loading="sendingEmails">发送订购邮件</el-button>
          <el-button v-if="authStore.canViewAllData" type="info" :icon="Message" @click="sendDormEmails" :loading="sendingDormEmails">发送宿舍邮件</el-button>
        </div>
      </div>

      <!-- 学生端：已订购汇总 -->
      <div v-if="!authStore.canViewAllData && myOrders.length > 0" class="my-orders-summary">
        <div class="summary-header">
          <el-icon><Check /></el-icon>
          <span>你已订购 {{ myOrders.length }} 本教材</span>
          <el-button v-if="!isDead" type="danger" link size="small" style="margin-left: auto;" @click="clearAllOrders">全部取消</el-button>
        </div>
        <div class="summary-items">
          <div v-for="o in myOrders" :key="o.id" class="summary-item">
            <span class="si-name">{{ o.textbook_name }}</span>
            <span class="si-course" v-if="o.course_name">{{ o.course_name }}</span>
            <el-tag :type="o.course_type === '必修' ? 'danger' : 'info'" size="small">{{ o.course_type }}</el-tag>
            <span class="si-price">¥{{ o.discounted_price }}</span>
            <el-button v-if="!isDead" type="danger" link size="small" @click="cancelMyOrderItem(o.id)">取消</el-button>
          </div>
        </div>
        <div class="summary-totals">
          <span>原价合计：<strong>¥{{ myTotalOriginal }}</strong></span>
          <span class="total-divider">|</span>
          <span>折后合计：<strong class="price-discount">¥{{ myTotalDiscounted }}</strong></span>
        </div>
      </div>

      <!-- 学生端未订购提示 -->
      <div v-if="!authStore.canViewAllData && myOrders.length === 0 && !isDead" class="no-order-hint">
        <template v-if="noOrderConfirmed">
          <el-icon><CircleCheck /></el-icon>
          <span>你已确认无需订购教材。</span>
          <el-button type="warning" link size="small" @click="cancelNoOrder">我要订购</el-button>
        </template>
        <template v-else>
          <el-icon><InfoFilled /></el-icon>
          <span>请在下方教材列表中点击「订购」按钮选择你需要购买的教材，选好后点击底部「提交订购」完成选购</span>
        </template>
      </div>

      <!-- PC 端表格 -->
      <el-table
        v-if="!isMobile"
        :data="filteredTextbooks"
        v-loading="loading"
        stripe
        class="textbook-table"
        :header-cell-style="{ background: '#F7F8FA' }"
      >
        <el-table-column prop="course_name" label="课程名称" min-width="130" show-overflow-tooltip />
        <el-table-column prop="name" label="教材名称" min-width="160" show-overflow-tooltip />
        <el-table-column prop="isbn" label="ISBN" width="120" show-overflow-tooltip />
        <el-table-column prop="publisher" label="出版社" min-width="110" show-overflow-tooltip />
        <el-table-column prop="author" label="作者" width="80" show-overflow-tooltip />
        <el-table-column prop="course_type" label="选修/必修" width="90">
          <template #default="{ row }">
            <el-tag :type="row.course_type === '必修' ? 'danger' : 'info'" size="small">{{ row.course_type }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="original_price" label="单价" width="75">
          <template #default="{ row }">¥{{ row.original_price }}</template>
        </el-table-column>
        <el-table-column prop="discounted_price" label="折后单价" width="85">
          <template #default="{ row }">
            <span :class="{ 'price-discount': row.discounted_price < row.original_price }">¥{{ row.discounted_price }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="notes" label="备注" min-width="100"><template #default="{ row }"><RichContent :content="row.notes" /></template></el-table-column>
        <el-table-column v-if="!authStore.canViewAllData" label="操作" width="85" align="center" fixed="right">
          <template #default="{ row }">
            <el-button
              v-if="myOrderIds.includes(row.id)"
              type="danger" plain size="small"
              :disabled="isDead"
              @click="cancelBook(row)"
            >已订</el-button>
            <el-button
              v-else-if="selectedIds.includes(row.id)"
              type="warning" plain size="small"
              :disabled="isDead"
              @click="deselectBook(row)"
            >已选</el-button>
            <el-button
              v-else
              type="primary" plain size="small"
              :disabled="isDead"
              @click="selectBook(row)"
            >订购</el-button>
          </template>
        </el-table-column>
        <el-table-column v-if="authStore.canViewAllData" label="操作" width="160" align="center" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link size="small" :icon="Edit" @click="openEditDialog(row)">编辑</el-button>
            <el-button type="danger" link size="small" :icon="Delete" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- 学生端：提交栏 -->
      <div v-if="!authStore.canViewAllData && pickBooks.length > 0 && !isMobile" class="submit-bar">
        <div class="submit-info">
          <span>已选 <strong>{{ pickBooks.length }}</strong> 本</span>
          <span class="sb-divider">|</span>
          <span>原价：<strong>¥{{ pickOriginal }}</strong></span>
          <span class="sb-divider">|</span>
          <span>折后：<strong class="price-discount">¥{{ pickDiscounted }}</strong></span>
          <span v-if="pickBooks.length < filteredTextbooks.length" class="sb-hint">（还需选择其他教材请继续点击订购）</span>
        </div>
        <el-button type="primary" size="large" :disabled="isDead" @click="openConfirmDialog">提交订购</el-button>
      </div>

      <!-- 学生端：确认无需订购栏 -->
      <div v-if="!authStore.canViewAllData && !isDead && pickBooks.length === 0 && myOrders.length === 0" class="no-order-bar">
        <span>如果不需要订购任何教材，请点击确认：</span>
        <el-button v-if="!noOrderConfirmed" type="default" @click="openNoOrderConfirm" :loading="confirmingNoOrder">确认无需订购</el-button>
        <el-button v-else type="success" plain disabled>已确认无需订购 <el-icon><CircleCheck /></el-icon></el-button>
      </div>

      <!-- 移动端列表 -->
      <div v-if="isMobile" class="mobile-list" v-loading="loading">
        <el-card v-for="row in filteredTextbooks" :key="row.id" class="mobile-card" shadow="sm"
          :class="getMobileCardClass(row)"
        >
          <div class="card-header">
            <span class="card-title">{{ row.name }}</span>
            <el-tag :type="row.course_type === '必修' ? 'danger' : 'info'" size="small">{{ row.course_type }}</el-tag>
          </div>
          <div class="card-body">
            <div class="info-row" v-if="row.course_name"><span class="label">课程：</span><span class="value">{{ row.course_name }}</span></div>
            <div class="info-row" v-if="row.isbn"><span class="label">ISBN：</span><span class="value">{{ row.isbn }}</span></div>
            <div class="info-row" v-if="row.publisher"><span class="label">出版社：</span><span class="value">{{ row.publisher }}</span></div>
            <div class="info-row" v-if="row.author"><span class="label">作者：</span><span class="value">{{ row.author }}</span></div>
            <div class="info-row">
              <span class="label">价格：</span>
              <span class="value">
                <strong class="price-discount">¥{{ row.discounted_price }}</strong>
                <span v-if="row.discounted_price < row.original_price" class="price-crossed">¥{{ row.original_price }}</span>
              </span>
            </div>
            <div v-if="row.notes" class="info-row"><span class="label">备注：</span><RichContent class="value notes-text" :content="row.notes" /></div>
          </div>
          <div class="card-footer" v-if="!authStore.canViewAllData">
            <el-button
              v-if="myOrderIds.includes(row.id)"
              type="danger" plain size="small" :disabled="isDead"
              @click="cancelBook(row)" style="flex:1;"
            >已订(取消)</el-button>
            <el-button
              v-else-if="selectedIds.includes(row.id)"
              type="warning" plain size="small" :disabled="isDead"
              @click="deselectBook(row)" style="flex:1;"
            >已选(取消)</el-button>
            <el-button
              v-else
              type="primary" size="small" :disabled="isDead"
              @click="selectBook(row)" style="flex:1;"
            >订购</el-button>
          </div>
          <div class="card-footer" v-if="authStore.canViewAllData">
            <el-button type="primary" plain size="small" :icon="Edit" @click="openEditDialog(row)">编辑</el-button>
            <el-button type="danger" plain size="small" :icon="Delete" @click="handleDelete(row)">删除</el-button>
          </div>
        </el-card>
        <el-empty v-if="!loading && filteredTextbooks.length === 0" description="暂无教材" />

        <!-- 移动端提交 -->
        <div v-if="!authStore.canViewAllData && pickBooks.length > 0" class="mobile-submit-bar">
          <div class="mobile-submit-info">
            <span>已选 {{ pickBooks.length }} 本</span>
            <span>原价 ¥{{ pickOriginal }}</span>
            <span>折后 <strong class="price-discount">¥{{ pickDiscounted }}</strong></span>
          </div>
          <el-button type="primary" :disabled="isDead" @click="openConfirmDialog">提交订购</el-button>
        </div>
      </div>
    </el-card>

    <!-- 管理端：订购设置 & 联系班干 -->
    <el-card v-if="authStore.canViewAllData" class="page-card config-card" shadow="never">
      <div class="section-header">
        <span class="section-title">订购设置</span>
        <el-button type="primary" size="small" @click="saveConfig" :loading="savingConfig">保存设置</el-button>
      </div>
      <el-row :gutter="20" v-if="!isMobile">
        <el-col :span="6">
          <el-form-item label="订购截止时间">
            <el-date-picker
              v-model="configForm.deadline"
              type="datetime"
              placeholder="不设置则不限时"
              format="YYYY-MM-DD HH:mm"
              value-format="YYYY-MM-DD HH:mm:ss"
              style="width: 100%;"
            />
          </el-form-item>
        </el-col>
        <el-col :span="6">
          <el-form-item label="关联通知公告">
            <el-select v-model="configForm.notice_id" placeholder="选择通知" clearable style="width: 100%;" filterable>
              <el-option v-for="n in notices" :key="n.id" :label="n.title" :value="n.id" />
            </el-select>
          </el-form-item>
        </el-col>
        <el-col :span="6">
          <el-form-item label="联系班干">
            <el-select v-model="configForm.contact_user_id" placeholder="选择班干" clearable style="width: 100%;" filterable>
              <el-option v-for="u in classLeaders" :key="u.id" :label="u.real_name" :value="u.id">
                <span>{{ u.real_name }}（{{ u.student_id }}）</span>
              </el-option>
            </el-select>
          </el-form-item>
        </el-col>
      </el-row>
      <div v-else class="mobile-config">
        <el-form-item label="订购截止时间" style="margin-bottom: 14px;">
          <el-date-picker v-model="configForm.deadline" type="datetime" placeholder="不设置则不限时" format="YYYY-MM-DD HH:mm" value-format="YYYY-MM-DD HH:mm:ss" style="width: 100%;" />
        </el-form-item>
        <el-form-item label="关联通知公告" style="margin-bottom: 14px;">
          <el-select v-model="configForm.notice_id" placeholder="选择通知" clearable style="width: 100%;">
            <el-option v-for="n in notices" :key="n.id" :label="n.title" :value="n.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="联系班干">
          <el-select v-model="configForm.contact_user_id" placeholder="选择班干" clearable style="width: 100%;">
            <el-option v-for="u in classLeaders" :key="u.id" :label="u.real_name" :value="u.id" />
          </el-select>
        </el-form-item>
      </div>
    </el-card>

    <!-- 管理端：教材订购统计 -->
    <el-card v-if="authStore.canViewAllData" class="page-card stats-card" shadow="never">
      <div class="section-header">
        <span class="section-title">教材订购统计</span>
      </div>
      <div class="stats-grid">
        <div v-for="s in textbookStats" :key="s.id" class="stat-item-card">
          <div class="stat-book-name">{{ s.name }}</div>
          <div class="stat-book-meta">
            <el-tag :type="s.course_type === '必修' ? 'danger' : 'info'" size="small">{{ s.course_type }}</el-tag>
            <span v-if="s.course_name" class="stat-course">{{ s.course_name }}</span>
          </div>
          <div class="stat-count">
            <span class="stat-num">{{ s.order_count }}</span>
            <span class="stat-label">已订购</span>
          </div>
        </div>
      </div>
    </el-card>

    <!-- 管理端：未订购名单 -->
    <el-card v-if="authStore.canViewAllData" class="page-card unordered-card" shadow="never">
      <div class="section-header">
        <span class="section-title">
          未订购学生
          <span class="unordered-count">{{ unorderedList.length }} / {{ unorderedTotal }}</span>
        </span>
        <div class="header-actions">
          <el-button type="warning" size="small" :icon="ChatDotSquare" :loading="qqReminding" @click="qqRemindUnordered">QQ私信提醒</el-button>
          <el-button type="primary" size="small" :icon="Message" :loading="qqEmailing" @click="qqEmailUnordered">QQ邮件提醒</el-button>
        </div>
      </div>
      <div v-if="unorderedList.length > 0" class="unordered-list">
        <el-tag v-for="s in unorderedList" :key="s.id" type="info" class="unordered-tag">
          {{ s.real_name }}（{{ s.student_id }}）
        </el-tag>
      </div>
      <div v-if="confirmedList.length > 0" style="margin-top: 12px;">
        <div style="font-size: 13px; color: var(--el-text-color-regular); margin-bottom: 8px;">
          <el-icon style="color: #2E7D32;"><CircleCheck /></el-icon>
          已确认无需订购（{{ confirmedList.length }} 人）：
        </div>
        <div class="unordered-list">
          <el-tag v-for="s in confirmedList" :key="s.id" type="success" class="unordered-tag">
            {{ s.real_name }}（{{ s.student_id }}）
          </el-tag>
        </div>
      </div>
      <el-empty v-if="unorderedList.length === 0 && confirmedList.length === 0" description="全部学生已订购" :image-size="60" />
      <div v-if="unorderedList.length > 0" class="unordered-hint">
        <el-icon><InfoFilled /></el-icon>
        <span>QQ提醒发送给这些未订购学生，提醒他们尽快完成教材选购</span>
      </div>
    </el-card>

    <!-- 管理端：订购记录（按学生分组） -->
    <el-card v-if="authStore.canViewAllData" class="page-card order-list-card" shadow="never">
      <div class="section-header">
        <span class="section-title">订购记录</span>
        <div class="stats-row">
          <span class="stat-item">已订人数：<strong>{{ groupedOrders.length }}</strong></span>
          <span class="stat-item">总本数：<strong>{{ totalBookCount }}</strong></span>
          <span class="stat-item">原价总额：<strong>¥{{ totalOriginal }}</strong></span>
          <span class="stat-item">折后总额：<strong class="price-discount">¥{{ totalDiscounted }}</strong></span>
        </div>
      </div>

      <!-- PC 端：按学生分组的卡片 -->
      <div v-if="!isMobile" v-loading="orderLoading" class="grouped-order-list">
        <div v-if="groupedOrders.length === 0" class="empty-hint">
          <el-empty description="暂无订购记录" :image-size="60" />
        </div>
        <div v-for="g in groupedOrders" :key="g.student_id" class="student-order-card">
          <div class="soc-header">
            <div class="soc-student">
              <el-avatar :size="32">{{ g.student_name[0] }}</el-avatar>
              <div>
                <strong>{{ g.student_name }}</strong>
                <span class="soc-sid">{{ g.student_student_id }}</span>
              </div>
            </div>
            <div class="soc-totals">
              <span>共 {{ g.items.length }} 本</span>
              <span class="soc-divider">|</span>
              <span>原价：<strong>¥{{ g.total_original }}</strong></span>
              <span class="soc-divider">|</span>
              <span>折后：<strong class="price-discount">¥{{ g.total_discounted }}</strong></span>
            </div>
            <div class="soc-actions">
              <el-button
                type="primary" link size="small"
                @click="toggleExpand(g.student_id)"
              >
                {{ expandedIds.includes(g.student_id) ? '收起' : '展开' }}
                <el-icon><component :is="expandedIds.includes(g.student_id) ? 'ArrowUp' : 'ArrowDown'" /></el-icon>
              </el-button>
              <el-popconfirm title="确定删除该学生全部订购？" @confirm="deleteStudentOrders(g.student_id)">
                <template #reference>
                  <el-button type="danger" link size="small" :icon="Delete">删除</el-button>
                </template>
              </el-popconfirm>
            </div>
          </div>
          <div v-if="expandedIds.includes(g.student_id)" class="soc-detail">
            <table class="soc-table">
              <thead>
                <tr>
                  <th>课程名称</th>
                  <th>教材名称</th>
                  <th>ISBN</th>
                  <th>作者</th>
                  <th>类型</th>
                  <th>单价</th>
                  <th>折后价</th>
                  <th>操作</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="item in g.items" :key="item.id">
                  <td>{{ item.course_name || '-' }}</td>
                  <td>{{ item.textbook_name }}</td>
                  <td>{{ item.isbn || '-' }}</td>
                  <td>{{ item.author || '-' }}</td>
                  <td>
                    <el-tag :type="item.course_type === '必修' ? 'danger' : 'info'" size="small">{{ item.course_type }}</el-tag>
                  </td>
                  <td>¥{{ item.original_price }}</td>
                  <td><strong class="price-discount">¥{{ item.discounted_price }}</strong></td>
                  <td>
                    <el-button type="danger" link size="small" :icon="Delete" @click="handleDeleteOrderItem(item.id)">删除</el-button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>

      <!-- 移动端订单 -->
      <div v-else class="mobile-list" v-loading="orderLoading">
        <el-card v-for="g in groupedOrders" :key="g.student_id" class="mobile-card" shadow="sm">
          <div class="card-header">
            <span class="card-title">{{ g.student_name }} <span style="color: var(--el-text-color-secondary); font-size: 13px;">({{ g.student_student_id }})</span></span>
            <el-popconfirm title="确定删除？" @confirm="deleteStudentOrders(g.student_id)">
              <template #reference>
                <el-button type="danger" link size="small" :icon="Delete" />
              </template>
            </el-popconfirm>
          </div>
          <div class="card-body">
            <div v-for="item in g.items" :key="item.id" class="m-order-item">
              <span>{{ item.textbook_name }}</span>
              <span class="price-discount">¥{{ item.discounted_price }}</span>
            </div>
            <div class="info-row" style="margin-top: 6px;">
              <span class="label">合计：</span>
              <span class="value">{{ g.items.length }} 本，原价 ¥{{ g.total_original }}，折后 <strong class="price-discount">¥{{ g.total_discounted }}</strong></span>
            </div>
          </div>
        </el-card>
        <el-empty v-if="!orderLoading && groupedOrders.length === 0" description="暂无订购记录" />
      </div>
    </el-card>

    <!-- 管理员：新增/编辑教材弹窗 -->
    <el-dialog
      v-model="dialogVisible"
      :title="editingId ? '编辑教材' : '新增教材'"
      :width="isMobile ? '100%' : '500px'"
      :fullscreen="isMobile"
      class="modern-dialog"
      destroy-on-close
    >
      <el-form :model="form" label-width="80px" label-position="top">
        <el-form-item label="课程名称">
          <el-input v-model="form.course_name" placeholder="请输入课程名称" />
        </el-form-item>
        <el-form-item label="教材名称">
          <el-input v-model="form.name" placeholder="请输入教材名称" />
        </el-form-item>
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="ISBN">
              <el-input v-model="form.isbn" placeholder="请输入ISBN" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="作者">
              <el-input v-model="form.author" placeholder="请输入作者" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="出版社">
          <el-input v-model="form.publisher" placeholder="请输入出版社" />
        </el-form-item>
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="课程类型">
              <el-select v-model="form.course_type" style="width: 100%;">
                <el-option label="必修" value="必修" />
                <el-option label="选修" value="选修" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="单价">
              <el-input-number v-model="form.original_price" :min="0" :precision="2" style="width: 100%;" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="折后单价">
              <el-input-number v-model="form.discounted_price" :min="0" :precision="2" style="width: 100%;" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="备注">
          <RichEditor v-model="form.notes" />
        </el-form-item>
      </el-form>
      <template #footer>
        <div class="dialog-footer">
          <el-button @click="dialogVisible = false">取消</el-button>
          <el-button type="primary" :loading="saving" @click="handleSave">{{ editingId ? '保存' : '新增' }}</el-button>
        </div>
      </template>
    </el-dialog>

    <!-- 学生端：签字确认弹窗 -->
    <el-dialog
      v-model="confirmVisible"
      title="确认教材订购"
      :width="isMobile ? '100%' : '520px'"
      :fullscreen="isMobile"
      class="modern-dialog"
      destroy-on-close
    >
      <div class="confirm-content">
        <div class="confirm-books">
          <div v-for="b in pickBooks" :key="b.id" class="confirm-book-item">
            <span class="cbi-name">{{ b.name }}</span>
            <span class="cbi-course" v-if="b.course_name">{{ b.course_name }}</span>
            <span class="cbi-price">¥{{ b.discounted_price }}</span>
          </div>
        </div>
        <div class="confirm-totals">
          <div class="confirm-total-row">共 <strong>{{ pickBooks.length }}</strong> 本教材</div>
          <div class="confirm-total-row">原价合计：<strong>¥{{ pickOriginal }}</strong></div>
          <div class="confirm-total-row">折后合计：<strong class="price-discount" style="font-size: 20px;">¥{{ pickDiscounted }}</strong></div>
        </div>
        <el-divider />
        <div class="confirm-signature">
          <div class="signature-label">签字确认</div>
          <p class="signature-desc">请输入你的姓名以确认以上教材订购信息无误。<br/>订购后如需修改，可在截止时间前重新提交。</p>
          <el-input v-model="signatureName" :placeholder="'请输入姓名（' + (authStore.user?.real_name || '') + '）'" />
          <div class="signature-hint" v-if="signatureName && signatureName !== (authStore.user?.real_name || '')">
            <el-icon><WarningFilled /></el-icon> 签字与真实姓名不一致
          </div>
        </div>
        <el-divider />
        <div class="payment-info">
          <div class="payment-title">付款说明</div>
          <p>订购提交后，请关注班级群通知，按班委发布的收款方式完成付款。如有疑问请联系{{ contactPerson ? contactPerson.real_name + '（QQ:' + (contactPerson.qq_number || '未填') + '）' : '班委' }}。</p>
        </div>
      </div>
      <template #footer>
        <div class="dialog-footer">
          <el-button @click="confirmVisible = false">取消</el-button>
          <el-button type="primary" :disabled="!signatureName" :loading="submitting" @click="submitOrder">确认订购</el-button>
        </div>
      </template>
    </el-dialog>

    <!-- 学生端：确认无需订购签字弹窗 -->
    <el-dialog
      v-model="noOrderVisible"
      title="确认无需订购教材"
      :width="isMobile ? '100%' : '480px'"
      :fullscreen="isMobile"
      class="modern-dialog"
      destroy-on-close
    >
      <div class="confirm-content">
        <div class="no-order-msg">
          <el-icon style="font-size: 24px; color: #E6A23C;"><WarningFilled /></el-icon>
          <p style="margin: 12px 0 0; color: var(--el-text-color-regular); font-size: 14px; line-height: 1.8;">
            确认后表示你<strong>不需要订购任何教材</strong>。<br/>
            之后仍可在截止时间前取消确认并重新选购。
          </p>
        </div>
        <el-divider />
        <div class="confirm-signature">
          <div class="signature-label">签字确认</div>
          <p class="signature-desc">请输入你的姓名以确认无需订购教材。</p>
          <el-input v-model="noOrderSig" :placeholder="'请输入姓名（' + (authStore.user?.real_name || '') + '）'" />
          <div class="signature-hint" v-if="noOrderSig && noOrderSig !== (authStore.user?.real_name || '')">
            <el-icon><WarningFilled /></el-icon> 签字与真实姓名不一致
          </div>
        </div>
      </div>
      <template #footer>
        <div class="dialog-footer">
          <el-button @click="noOrderVisible = false">取消</el-button>
          <el-button type="warning" :disabled="!noOrderSig" :loading="confirmingNoOrder" @click="submitNoOrder">确认无需订购</el-button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onUnmounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Edit, Delete, Download, Check, Message, Clock, Bell, InfoFilled, UserFilled, ChatDotSquare, WarningFilled, ArrowDown, ArrowUp, CircleCheck } from '@element-plus/icons-vue'
import { useAuthStore } from '../stores/auth'
import api from '../api'

const authStore = useAuthStore()

const isMobile = ref(false)
const checkDevice = () => { isMobile.value = window.innerWidth <= 768 }

const textbooks = ref([])
const loading = ref(false)

// 筛选
const courseFilter = ref('')
const filteredTextbooks = computed(() => {
  let list = textbooks.value
  if (courseFilter.value) {
    list = list.filter(t => t.course_type === courseFilter.value)
  }
  // 必修排在前面
  return [...list].sort((a, b) => {
    if (a.course_type === '必修' && b.course_type !== '必修') return -1
    if (a.course_type !== '必修' && b.course_type === '必修') return 1
    return 0
  })
})

const groupedOrders = ref([])
const orderLoading = ref(false)

const myOrders = ref([])
const myTotalOriginal = ref(0)
const myTotalDiscounted = ref(0)
const myOrderIds = ref([])

// 本地选择（未提交的）
const selectedIds = ref([])
const pickBooks = computed(() => {
  const set = new Set([...selectedIds.value, ...myOrderIds.value])
  return textbooks.value.filter(t => set.has(t.id) && !myOrderIds.value.includes(t.id))
})
const pickOriginal = computed(() => pickBooks.value.reduce((s, b) => s + (b.original_price || 0), 0).toFixed(2))
const pickDiscounted = computed(() => pickBooks.value.reduce((s, b) => s + (b.discounted_price || 0), 0).toFixed(2))

// 配置
const config = ref({ deadline: null, notice_id: null, contact_user_id: null })
const configForm = reactive({ deadline: null, notice_id: null, contact_user_id: null })
const noticeContent = ref('')
const contactPerson = ref(null)
const notices = ref([])
const classLeaders = ref([])
const isDead = ref(false)
const countdown = ref('')
let countdownTimer = null

// 未订购
const unorderedList = ref([])
const unorderedTotal = ref(0)
const confirmedList = ref([])

// 统计
const textbookStats = ref([])

// 无需订购
const noOrderConfirmed = ref(false)
const confirmingNoOrder = ref(false)
const noOrderVisible = ref(false)
const noOrderSig = ref('')

// 展开/收起
const expandedIds = ref([])
function toggleExpand(id) {
  const idx = expandedIds.value.indexOf(id)
  if (idx >= 0) expandedIds.value.splice(idx, 1)
  else expandedIds.value.push(id)
}

// 确认弹窗
const confirmVisible = ref(false)
const signatureName = ref('')
const submitting = ref(false)

// 管理端弹窗
const dialogVisible = ref(false)
const editingId = ref(null)
const saving = ref(false)
const savingConfig = ref(false)
const sendingEmails = ref(false)
const sendingDormEmails = ref(false)
const qqReminding = ref(false)
const qqEmailing = ref(false)
const form = reactive({
  course_name: '', name: '', isbn: '', publisher: '', author: '',
  course_type: '必修', original_price: 0, discounted_price: 0, notes: ''
})

function getMobileCardClass(row) {
  if (myOrderIds.value.includes(row.id)) return 'is-ordered'
  if (selectedIds.value.includes(row.id)) return 'is-selected'
  return ''
}

const totalOriginal = computed(() => groupedOrders.value.reduce((s, g) => s + g.total_original, 0).toFixed(2))
const totalDiscounted = computed(() => groupedOrders.value.reduce((s, g) => s + g.total_discounted, 0).toFixed(2))
const totalBookCount = computed(() => groupedOrders.value.reduce((s, g) => s + g.items.length, 0))

function formatTime(t) {
  if (!t) return ''
  return String(t).replace('T', ' ').substring(0, 19)
}

function calcCountdown() {
  if (!config.value.deadline) { countdown.value = ''; isDead.value = false; return }
  const now = Date.now()
  const end = new Date(config.value.deadline).getTime()
  const diff = end - now
  if (diff <= 0) { countdown.value = '已截止'; isDead.value = true; return }
  isDead.value = false
  const d = Math.floor(diff / 86400000)
  const h = Math.floor((diff % 86400000) / 3600000)
  const m = Math.floor((diff % 3600000) / 60000)
  countdown.value = d > 0 ? `${d}天${h}小时${m}分钟` : `${h}小时${m}分钟`
}

// ─── 数据加载 ───

async function loadConfig() {
  try {
    const res = await api.get('/api/textbooks/config')
    config.value = { deadline: res.data.deadline, notice_id: res.data.notice_id, contact_user_id: res.data.contact_user_id }
    configForm.deadline = res.data.deadline
    configForm.notice_id = res.data.notice_id
    configForm.contact_user_id = res.data.contact_user_id
    calcCountdown()
    if (res.data.notice_id) loadNotice(res.data.notice_id)
    if (res.data.contact_user_id) loadContactPerson(res.data.contact_user_id)
  } catch {}
}

async function loadNotice(nid) {
  try {
    const res = await api.get('/api/notices')
    const n = (res.data || []).find(x => x.id === nid)
    if (n) noticeContent.value = n.content || n.title || ''
  } catch {}
}

async function loadContactPerson(uid) {
  try {
    const res = await api.get('/api/users')
    const u = (res.data || []).find(x => x.id === uid)
    if (u) contactPerson.value = u
  } catch {}
}

async function loadTextbooks() {
  loading.value = true
  try {
    const res = await api.get('/api/textbooks')
    textbooks.value = res.data
  } catch { ElMessage.error('加载教材列表失败') }
  finally { loading.value = false }
}

async function loadGroupedOrders() {
  if (!authStore.canViewAllData) return
  orderLoading.value = true
  try {
    const res = await api.get('/api/textbooks/orders/grouped')
    groupedOrders.value = res.data || []
  } catch {}
  finally { orderLoading.value = false }
}

async function loadMyOrders() {
  if (authStore.canViewAllData) return
  try {
    const res = await api.get('/api/textbooks/my-orders')
    myOrders.value = res.data.orders || []
    myTotalOriginal.value = res.data.total_original || 0
    myTotalDiscounted.value = res.data.total_discounted || 0
    myOrderIds.value = myOrders.value.map(o => o.textbook_id)
    selectedIds.value = [] // 清除本地选择
    noOrderConfirmed.value = !!res.data.no_order_confirmed
  } catch {}
}

async function loadUnordered() {
  if (!authStore.canViewAllData) return
  try {
    const res = await api.get('/api/textbooks/unordered')
    unorderedList.value = res.data.unordered || []
    unorderedTotal.value = res.data.total || 0
    confirmedList.value = res.data.confirmed || []
  } catch {}
}

async function loadNoOrderStatus() {
  if (authStore.canViewAllData) return
  // 通过 my-orders 判断：如果返回空且 we check if confirmed
  try {
    const res = await api.get('/api/textbooks/unordered')
    // For student, check if current user is in confirmed list
    noOrderConfirmed.value = myOrders.value.length === 0 && selectedIds.value.length === 0
  } catch { noOrderConfirmed.value = false }
}

function openNoOrderConfirm() {
  noOrderSig.value = ''
  noOrderVisible.value = true
}

async function submitNoOrder() {
  if (!noOrderSig.value) return ElMessage.warning('请签字确认')
  confirmingNoOrder.value = true
  try {
    await api.post('/api/textbooks/confirm-no-order')
    noOrderConfirmed.value = true
    noOrderVisible.value = false
    myOrders.value = []
    myOrderIds.value = []
    selectedIds.value = []
    loadGroupedOrders()
    loadUnordered()
    ElMessage.success('已确认无需订购')
  } catch (err) { ElMessage.error(err.response?.data?.detail || '操作失败') }
  finally { confirmingNoOrder.value = false }
}

async function cancelNoOrder() {
  try { await api.delete('/api/textbooks/confirm-no-order') } catch {}
  noOrderConfirmed.value = false
  ElMessage.success('已取消，请选择需要订购的教材')
}

async function loadStats() {
  if (!authStore.canViewAllData) return
  try {
    const res = await api.get('/api/textbooks/stats')
    textbookStats.value = res.data || []
  } catch {}
}

async function loadNotices() {
  if (!authStore.canViewAllData) return
  try {
    const res = await api.get('/api/notices')
    notices.value = res.data || []
  } catch {}
}

async function loadClassLeaders() {
  if (!authStore.canViewAllData) return
  try {
    const res = await api.get('/api/users')
    classLeaders.value = (res.data || []).filter(u => u.role === 'class_leader' || u.is_class_leader)
  } catch {}
}

// ─── 学生操作 ───

function selectBook(row) {
  if (myOrderIds.value.includes(row.id)) return
  if (!selectedIds.value.includes(row.id)) {
    selectedIds.value.push(row.id)
  }
}

function deselectBook(row) {
  selectedIds.value = selectedIds.value.filter(id => id !== row.id)
}

function openConfirmDialog() {
  const all = [...myOrderIds.value, ...selectedIds.value]
  if (all.length === 0) return ElMessage.warning('请先选择教材')
  signatureName.value = ''
  confirmVisible.value = true
}

async function submitOrder() {
  if (!signatureName.value) return ElMessage.warning('请签字确认')
  submitting.value = true
  try {
    const allIds = [...myOrderIds.value, ...selectedIds.value]
    await api.post('/api/textbooks/order-batch', { textbook_ids: allIds })
    ElMessage.success('订购成功')
    confirmVisible.value = false
    selectedIds.value = []
    loadMyOrders()
    loadGroupedOrders()
  } catch (err) {
    ElMessage.error(err.response?.data?.detail || '订购失败')
  } finally { submitting.value = false }
}

async function cancelBook(row) {
  if (isDead.value) return ElMessage.warning('订购已截止')
  const order = myOrders.value.find(o => o.textbook_id === row.id)
  if (!order) return
  try {
    await ElMessageBox.confirm(`确定取消《${row.name}》的订购吗？`, '确认取消', { type: 'warning' })
  } catch { return }
  try {
    await api.delete(`/api/textbooks/my-orders/${order.id}`)
    ElMessage.success('已取消')
    loadMyOrders()
    loadGroupedOrders()
  } catch (err) {
    ElMessage.error(err.response?.data?.detail || '取消失败')
  }
}

async function cancelMyOrderItem(orderId) {
  const o = myOrders.value.find(x => x.id === orderId)
  if (!o) return
  try {
    await ElMessageBox.confirm(`确定取消《${o.textbook_name}》的订购吗？`, '确认取消', { type: 'warning' })
  } catch { return }
  try {
    await api.delete(`/api/textbooks/my-orders/${orderId}`)
    ElMessage.success('已取消')
    loadMyOrders()
    loadGroupedOrders()
  } catch (err) {
    ElMessage.error(err.response?.data?.detail || '取消失败')
  }
}

async function clearAllOrders() {
  try {
    await ElMessageBox.confirm('确定取消所有已订购的教材吗？', '全部取消', { type: 'warning' })
  } catch { return }
  for (const o of myOrders.value) {
    try { await api.delete(`/api/textbooks/my-orders/${o.id}`) } catch {}
  }
  ElMessage.success('已全部取消')
  loadMyOrders()
  loadGroupedOrders()
}

// ─── 管理员操作 ───

async function saveConfig() {
  savingConfig.value = true
  try {
    const payload = {
      deadline: configForm.deadline || null,
      notice_id: configForm.notice_id || null,
      contact_user_id: configForm.contact_user_id || null
    }
    await api.put('/api/textbooks/config', payload)
    ElMessage.success('设置已保存')
    loadConfig()
    if (configForm.notice_id) {
      loadNotice(configForm.notice_id)
    } else { noticeContent.value = '' }
    if (configForm.contact_user_id) {
      loadContactPerson(configForm.contact_user_id)
    } else { contactPerson.value = null }
  } catch (err) {
    ElMessage.error(err.response?.data?.detail || '保存失败')
  } finally { savingConfig.value = false }
}

function openCreateDialog() {
  editingId.value = null
  form.course_name = ''; form.name = ''; form.isbn = ''; form.publisher = ''; form.author = ''
  form.course_type = '必修'; form.original_price = 0; form.discounted_price = 0; form.notes = ''
  dialogVisible.value = true
}

function openEditDialog(row) {
  editingId.value = row.id
  form.course_name = row.course_name || ''; form.name = row.name
  form.isbn = row.isbn || ''; form.publisher = row.publisher || ''; form.author = row.author || ''
  form.course_type = row.course_type; form.original_price = row.original_price
  form.discounted_price = row.discounted_price; form.notes = row.notes
  dialogVisible.value = true
}

async function handleSave() {
  if (!form.name) return ElMessage.warning('请输入教材名称')
  saving.value = true
  try {
    if (editingId.value) {
      await api.put(`/api/textbooks/${editingId.value}`, form)
      ElMessage.success('修改成功')
    } else {
      await api.post('/api/textbooks', form)
      ElMessage.success('新增成功')
    }
    dialogVisible.value = false
    loadTextbooks()
  } catch (err) {
    ElMessage.error(err.response?.data?.detail || '操作失败')
  } finally { saving.value = false }
}

async function handleDelete(row) {
  try { await ElMessageBox.confirm(`确定删除「${row.name}」吗？`, '确认删除', { type: 'warning' }) } catch { return }
  try {
    await api.delete(`/api/textbooks/${row.id}`)
    ElMessage.success('删除成功')
    loadTextbooks()
    loadGroupedOrders()
  } catch (err) { ElMessage.error(err.response?.data?.detail || '删除失败') }
}

async function exportOrders() {
  await downloadExportFile('', '教材订购明细.xlsx')
}

async function exportByDormExcel() {
  await downloadExportFile('export-by-dorm-excel', '教材订购明细_按宿舍.xlsx')
}

async function exportByStudentId() {
  await downloadExportFile('export-by-student-id', '教材订购明细_按学号.xlsx')
}

async function exportByDormWord() {
  try {
    const res = await api.get('/api/textbooks/orders/export-by-dorm-word', { responseType: 'blob' })
    const url = window.URL.createObjectURL(new Blob([res.data]))
    const link = document.createElement('a'); link.href = url
    link.download = '教材订购明细_按宿舍.docx'
    document.body.appendChild(link); link.click(); document.body.removeChild(link)
    window.URL.revokeObjectURL(url)
    ElMessage.success('导出成功')
  } catch (err) {
    showBlobError(err, '导出失败')
  }
}

async function downloadExportFile(suffix, filename) {
  const url = suffix ? `/api/textbooks/orders/${suffix}` : '/api/textbooks/orders/export'
  try {
    const res = await api.get(url, { responseType: 'blob' })
    const blobUrl = window.URL.createObjectURL(new Blob([res.data]))
    const link = document.createElement('a'); link.href = blobUrl
    link.download = filename
    document.body.appendChild(link); link.click(); document.body.removeChild(link)
    window.URL.revokeObjectURL(blobUrl)
    ElMessage.success('导出成功')
  } catch (err) {
    showBlobError(err, '导出失败')
  }
}

function showBlobError(err, defaultMsg) {
  if (err.response?.data instanceof Blob) {
    try { err.response.data.text().then(t => ElMessage.error(JSON.parse(t).detail || defaultMsg)) } catch { ElMessage.error(defaultMsg) }
  } else {
    ElMessage.error(defaultMsg)
  }
}

async function sendOrderEmails() {
  try { await ElMessageBox.confirm('将向每位已订购的学生发送教材明细邮件，确认发送？', '发送邮件', { type: 'info' }) } catch { return }
  sendingEmails.value = true
  try {
    const res = await api.post('/api/textbooks/orders/send-emails')
    ElMessage.success(res.data.message || '发送完成')
  } catch (err) { ElMessage.error(err.response?.data?.detail || '发送失败') }
  finally { sendingEmails.value = false }
}

async function sendDormEmails() {
  try { await ElMessageBox.confirm('将向各宿舍长发送宿舍订购明细邮件，确认发送？', '发送宿舍邮件', { type: 'info' }) } catch { return }
  sendingDormEmails.value = true
  try {
    const res = await api.post('/api/textbooks/orders/send-dorm-emails')
    ElMessage.success(res.data.message || '发送完成')
  } catch (err) { ElMessage.error(err.response?.data?.detail || '发送失败') }
  finally { sendingDormEmails.value = false }
}

async function handleDeleteOrderItem(orderId) {
  try { await api.delete(`/api/textbooks/orders/${orderId}`) } catch {}
  loadGroupedOrders()
  loadUnordered()
}

async function deleteStudentOrders(studentId) {
  const g = groupedOrders.value.find(x => x.student_id === studentId)
  if (!g) return
  for (const item of g.items) {
    try { await api.delete(`/api/textbooks/orders/${item.id}`) } catch {}
  }
  ElMessage.success('已删除该学生的全部订购')
  loadGroupedOrders()
  loadUnordered()
}

async function qqRemindUnordered() {
  try { await ElMessageBox.confirm('将向所有未订购学生发送QQ私聊提醒，确认？', 'QQ提醒', { type: 'info' }) } catch { return }
  qqReminding.value = true
  try {
    const res = await api.post('/api/textbooks/qq-remind-unordered')
    ElMessage.success(res.data.message || '已发送')
  } catch (err) { ElMessage.error(err.response?.data?.detail || '发送失败') }
  finally { qqReminding.value = false }
}

async function qqEmailUnordered() {
  try { await ElMessageBox.confirm('将向所有未订购学生发送QQ邮件提醒，确认？', '邮件提醒', { type: 'info' }) } catch { return }
  qqEmailing.value = true
  try {
    const res = await api.post('/api/textbooks/qq-remind-unordered-email')
    ElMessage.success(res.data.message || '已发送')
  } catch (err) { ElMessage.error(err.response?.data?.detail || '发送失败') }
  finally { qqEmailing.value = false }
}

onMounted(() => {
  checkDevice()
  window.addEventListener('resize', checkDevice)
  countdownTimer = setInterval(calcCountdown, 30000)
  loadConfig()
  loadTextbooks()
  loadMyOrders()
  loadGroupedOrders()
  loadUnordered()
  loadStats()
  loadNotices()
  loadClassLeaders()
})

onUnmounted(() => {
  window.removeEventListener('resize', checkDevice)
  if (countdownTimer) clearInterval(countdownTimer)
})
</script>

<style scoped>
.textbook-container { padding: 0; }
.page-card { border: none; border-radius: 8px; box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.05); margin-bottom: 16px; }

.notice-banner {
  display: flex; align-items: flex-start; gap: 10px;
  background: #E8F5E9; border: 1px solid #A5D6A7; border-radius: 8px;
  padding: 12px 16px; margin-bottom: 12px;
}
.notice-icon { color: #2E7D32; font-size: 18px; margin-top: 1px; }
.notice-text { color: #1B5E20; font-size: 14px; line-height: 1.6; white-space: pre-wrap; }

.deadline-bar {
  display: flex; align-items: center; gap: 8px;
  background: #FFF3E0; border: 1px solid #FFB74D; border-radius: 8px;
  padding: 10px 16px; margin-bottom: 12px;
  color: #E65100; font-size: 14px; font-weight: 500;
}
.deadline-bar.deadline-over { background: #FFEBEE; border-color: #EF9A9A; color: #C62828; }

.contact-bar {
  display: flex; align-items: center; gap: 8px;
  background: #E3F2FD; border: 1px solid #90CAF9; border-radius: 8px;
  padding: 10px 16px; margin-bottom: 12px;
  color: #1565C0; font-size: 14px;
}

.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; flex-wrap: wrap; gap: 12px; }
.header-left { display: flex; align-items: center; }
.title-indicator { width: 4px; height: 18px; background-color: #165DFF; border-radius: 2px; margin-right: 12px; }
.page-title { margin: 0; font-size: 18px; font-weight: 600; color: var(--el-text-color-primary); }
.header-actions { display: flex; gap: 10px; flex-wrap: wrap; }
.price-discount { color: #F53F3F; }

.my-orders-summary {
  background: linear-gradient(135deg, #E8F5E9 0%, #F1F8E9 100%);
  border: 1px solid #C8E6C9; border-radius: 8px;
  padding: 16px 20px; margin-bottom: 20px;
}
.summary-header { display: flex; align-items: center; gap: 6px; color: #2E7D32; font-weight: 600; font-size: 14px; margin-bottom: 10px; }
.summary-items { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 10px; }
.summary-item { display: flex; align-items: center; gap: 8px; background: var(--surface); border-radius: 6px; padding: 6px 12px; font-size: 13px; }
.si-name { font-weight: 600; }
.si-course { color: var(--el-text-color-secondary); }
.si-price { color: #F53F3F; font-weight: 600; }
.summary-totals { display: flex; align-items: center; gap: 12px; font-size: 14px; color: var(--el-text-color-regular); }
.total-divider { color: #C9CDD4; }

.no-order-hint {
  display: flex; align-items: center; gap: 8px;
  background: #F0F5FF; border: 1px solid #D6E4FF; border-radius: 8px;
  padding: 12px 16px; margin-bottom: 16px;
  color: var(--el-color-primary); font-size: 14px;
}

.no-order-bar {
  display: flex; justify-content: space-between; align-items: center;
  padding: 16px 20px; margin-top: 16px;
  background: #FFF8E1; border: 1px solid #FFE082; border-radius: 8px;
  color: #F57F17; font-size: 14px;
}

.submit-bar {
  display: flex; justify-content: space-between; align-items: center;
  padding: 16px 20px; margin-top: 16px;
  background: #F0F5FF; border: 1px solid #D6E4FF; border-radius: 8px;
}
.submit-info { display: flex; align-items: center; gap: 8px; color: var(--el-text-color-regular); font-size: 14px; flex-wrap: wrap; }
.sb-divider { color: #C9CDD4; }
.sb-hint { color: var(--el-text-color-secondary); font-size: 12px; }

.textbook-table, .order-table { width: 100%; }
.order-list-card { margin-bottom: 0; }
.section-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; flex-wrap: wrap; gap: 12px; }
.section-title { font-size: 15px; font-weight: 600; color: var(--el-text-color-primary); }
.stats-row { display: flex; gap: 20px; color: var(--el-text-color-regular); font-size: 14px; }

/* 分组订单卡片 */
.grouped-order-list { display: flex; flex-direction: column; gap: 12px; }
.empty-hint { text-align: center; padding: 20px 0; }
.student-order-card {
  background: var(--surface); border: 1px solid #E5E6EB; border-radius: 8px; padding: 14px 18px;
  transition: box-shadow 0.2s;
}
.student-order-card:hover { box-shadow: 0 2px 8px rgba(0,0,0,0.06); }
.soc-header { display: flex; align-items: center; gap: 20px; }
.soc-student { display: flex; align-items: center; gap: 10px; flex: 1; min-width: 0; }
.soc-sid { color: var(--el-text-color-secondary); font-size: 12px; margin-left: 6px; }
.soc-totals { display: flex; align-items: center; gap: 10px; font-size: 13px; color: var(--el-text-color-regular); white-space: nowrap; flex-shrink: 0; }
.soc-actions { display: flex; align-items: center; gap: 2px; flex-shrink: 0; }
.soc-divider { color: #C9CDD4; }
.soc-detail { margin-top: 12px; border-top: 1px solid #E5E6EB; padding-top: 12px; }
.soc-table {
  width: 100%; border-collapse: collapse; font-size: 13px;
  table-layout: fixed;
}
.soc-table th {
  background: var(--surface-soft); color: var(--el-text-color-regular); font-weight: 500;
  padding: 8px 12px; text-align: left; white-space: nowrap;
  border-bottom: 1px solid #E5E6EB;
}
.soc-table th:nth-child(1) { width: 14%; }
.soc-table th:nth-child(2) { width: 24%; }
.soc-table th:nth-child(3) { width: 13%; }
.soc-table th:nth-child(4) { width: 7%; }
.soc-table th:nth-child(5) { width: 7%; }
.soc-table th:nth-child(6) { width: 8%; }
.soc-table th:nth-child(7) { width: 9%; }
.soc-table th:nth-child(8) { width: 8%; }
.soc-table td {
  padding: 8px 12px; color: var(--el-text-color-primary);
  border-bottom: 1px solid #F2F3F5;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.soc-table tbody tr:hover { background: #FAFBFC; }

/* 未订购 */
.unordered-card { margin-bottom: 16px; }
.unordered-count { color: #F53F3F; font-size: 13px; margin-left: 8px; font-weight: 500; }
.unordered-list { display: flex; flex-wrap: wrap; gap: 8px; }
.unordered-tag { cursor: default; }
.unordered-hint { display: flex; align-items: center; gap: 6px; color: var(--el-text-color-secondary); font-size: 12px; margin-top: 12px; }

/* 统计 */
.stats-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 12px; }
.stat-item-card {
  background: #FAFBFC; border: 1px solid #E5E6EB; border-radius: 8px;
  padding: 14px 16px; display: flex; flex-direction: column; gap: 6px;
}
.stat-book-name { font-weight: 600; font-size: 14px; color: var(--el-text-color-primary); }
.stat-book-meta { display: flex; align-items: center; gap: 6px; }
.stat-course { color: var(--el-text-color-secondary); font-size: 12px; }
.stat-count { display: flex; align-items: baseline; gap: 6px; margin-top: 4px; }
.stat-num { font-size: 24px; font-weight: 700; color: var(--el-color-primary); }
.stat-label { color: var(--el-text-color-secondary); font-size: 13px; }

/* 确认弹窗 */
.confirm-content { padding: 0 8px; }
.confirm-books { display: flex; flex-direction: column; gap: 8px; margin-bottom: 16px; }
.confirm-book-item { display: flex; align-items: center; gap: 12px; padding: 8px 12px; background: var(--surface-soft); border-radius: 6px; font-size: 14px; }
.cbi-name { font-weight: 600; flex: 1; }
.cbi-course { color: var(--el-text-color-secondary); }
.cbi-price { color: #F53F3F; font-weight: 600; }
.confirm-totals { text-align: right; font-size: 14px; display: flex; flex-direction: column; gap: 4px; }
.confirm-total-row { color: var(--el-text-color-regular); }
.signature-label { font-size: 15px; font-weight: 600; margin-bottom: 8px; }
.signature-desc { color: var(--el-text-color-secondary); font-size: 13px; margin-bottom: 12px; line-height: 1.6; }
.signature-hint { color: #F53F3F; font-size: 12px; margin-top: 4px; display: flex; align-items: center; gap: 4px; }
.payment-title { font-size: 15px; font-weight: 600; margin-bottom: 8px; }
.payment-info p { color: var(--el-text-color-secondary); font-size: 13px; line-height: 1.6; margin: 0; }

/* 移动端 */
.mobile-list { display: flex; flex-direction: column; gap: 12px; }
.mobile-card { border-radius: 8px; border: 1px solid #E5E6EB; transition: border-color 0.2s; }
.mobile-card.is-ordered { border-color: #2E7D32; background: #F1F8E9; }
.mobile-card.is-selected { border-color: #E6A23C; background: #FDF6EC; }
.card-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 12px; padding-bottom: 8px; border-bottom: 1px solid #F2F3F5; }
.card-title { font-weight: 600; font-size: 15px; color: var(--el-text-color-primary); line-height: 1.4; flex: 1; margin-right: 12px; }
.card-body { display: flex; flex-direction: column; gap: 6px; }
.info-row { display: flex; align-items: flex-start; font-size: 13px; line-height: 1.5; }
.info-row .label { color: var(--el-text-color-secondary); min-width: 50px; flex-shrink: 0; }
.info-row .value { color: var(--el-text-color-regular); word-break: break-all; }
.info-row .price-crossed { text-decoration: line-through; color: var(--el-text-color-secondary); font-size: 12px; margin-left: 6px; }
.notes-text { color: var(--el-text-color-primary) !important; }
.m-order-item { display: flex; justify-content: space-between; font-size: 13px; padding: 3px 0; }
.card-footer { margin-top: 12px; padding-top: 12px; border-top: 1px solid #F2F3F5; display: flex; gap: 8px; }
.card-footer .el-button { margin-left: 0 !important; flex: 1; }

.mobile-submit-bar {
  display: flex; justify-content: space-between; align-items: center;
  padding: 14px 16px; margin-top: 4px;
  background: #F0F5FF; border: 1px solid #D6E4FF; border-radius: 8px;
  position: sticky; bottom: 0;
}
.mobile-submit-info { display: flex; flex-direction: column; font-size: 12px; color: var(--el-text-color-regular); gap: 2px; }

.config-card { margin-bottom: 16px; }
.mobile-config { display: flex; flex-direction: column; }

@media screen and (max-width: 768px) {
  .page-header { flex-direction: column; align-items: flex-start; }
  .header-actions { width: 100%; }
  .header-actions .el-button { flex: 1; margin-left: 0 !important; }
  .section-header { flex-direction: column; align-items: flex-start; }
  .stats-row { flex-direction: column; gap: 6px; width: 100%; background: var(--surface-soft); padding: 12px; border-radius: 6px; }
  .stat-item { display: flex; justify-content: space-between; }
  .my-orders-summary { padding: 12px 16px; }
  .submit-bar { flex-direction: column; gap: 12px; }
  .soc-header { flex-direction: column; align-items: flex-start; gap: 8px; }
  .soc-totals { flex-wrap: wrap; }
  :deep(.modern-dialog) { margin: 0 !important; }
  :deep(.modern-dialog .el-dialog__body) { padding: 15px !important; }
  .dialog-footer { display: flex; justify-content: space-between; gap: 12px; }
  .dialog-footer .el-button { flex: 1; margin-left: 0 !important; }
}
</style>
