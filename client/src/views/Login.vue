<template>
  <main class="login-page">
    <header class="login-top"><span>sk2441 班务</span><ThemeSwitch /></header>
    <div class="login-card">
      <section class="login-story" aria-label="班级风采">
        <div class="story-title"><span>SHU KE · 2441</span><h1>欢迎使用数科2441智能班务系统</h1><p>每一份成长，都在这里相遇。</p></div>
        <div class="photo-frame" @mouseenter="paused=true" @mouseleave="paused=false" @focusin="paused=true" @focusout="paused=false">
          <img v-if="slides.length" :src="slides[current % slides.length].url" :alt="slides[current % slides.length].caption" fetchpriority="high" decoding="async" />
          <div class="photo-caption">{{ slides[current % slides.length]?.caption }}</div>
          <div class="slide-dots"><button v-for="(slide,i) in slides" :key="slide.url" :aria-label="`查看第 ${i+1} 张照片`" :aria-pressed="current===i" @click="current=i"></button><button class="pause-slide" :aria-label="autoPlay ? '暂停轮播' : '播放轮播'" @click="autoPlay=!autoPlay">{{autoPlay?'Ⅱ':'▶'}}</button></div>
        </div>
      </section>
      <section class="login-form-wrap">
        <img class="login-crest" src="/icons/crest.webp" alt="班徽" width="64" height="64" />
        <span class="login-eyebrow">让班级事务，井然有序</span>
        <h2>欢迎回来</h2><p class="login-muted">使用学号或姓名，登录你的班级空间</p>
        <el-form ref="formRef" :model="form" :rules="rules" size="large" autocomplete="on" method="post" @submit.prevent="handleLogin">
          <el-form-item prop="username"><el-input v-model="form.username" name="username" autocomplete="username" aria-label="学号或姓名" placeholder="学号 / 姓名 / 系统账号" clearable /></el-form-item>
          <el-form-item prop="password"><el-input v-model="form.password" name="password" :autocomplete="remember ? 'current-password' : 'off'" aria-label="密码" type="password" placeholder="请输入密码" show-password /></el-form-item>
          <div class="login-options"><el-checkbox v-model="remember">保存密码</el-checkbox><el-button link type="primary" @click="resetVisible=true">忘记密码？</el-button></div>
          <p class="password-hint">密码由浏览器密码管理器保存，本系统不在本机明文存储密码。</p>
          <el-button type="primary" native-type="submit" :loading="loading" class="login-submit">登 录</el-button>
        </el-form>
        <p class="login-footnote">数科2441 · 一起学习，共同成长</p>
      </section>
    </div>
    <el-dialog v-model="resetVisible" title="重置密码" width="440px" :close-on-click-modal="false" @closed="reset.password='';reset.confirm='';reset.code=''">
      <p>请联系系统管理员，在「用户管理」获取 8 位验证码。验证码 10 分钟内有效，仅可使用一次；姓名重复时请填写学号。</p>
      <el-form label-position="top" @submit.prevent="submitReset">
        <el-form-item label="学号或姓名"><el-input v-model="reset.username" autocomplete="username" /></el-form-item>
        <el-form-item label="管理员验证码"><el-input v-model="reset.code" inputmode="numeric" maxlength="8" autocomplete="one-time-code" /></el-form-item>
        <el-form-item label="新密码（至少 8 位）"><el-input v-model="reset.password" type="password" autocomplete="new-password" show-password /></el-form-item>
        <el-form-item label="确认新密码"><el-input v-model="reset.confirm" type="password" autocomplete="new-password" show-password /></el-form-item>
        <el-button type="primary" native-type="submit" :loading="resetBusy">重置并返回登录</el-button>
      </el-form>
    </el-dialog>
  </main>
</template>
<script setup>
import { ref, reactive, onMounted, onBeforeUnmount } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import api from '../api'
import { useAuthStore } from '../stores/auth'
import ThemeSwitch from '../components/ThemeSwitch.vue'
const router=useRouter(),authStore=useAuthStore(),formRef=ref(),loading=ref(false)
const remember=ref(localStorage.getItem('remember-login')==='true')
const form=reactive({username:remember.value ? localStorage.getItem('login-identifier')||'' : '',password:''})
const rules={username:[{required:true,message:'请输入学号或姓名',trigger:'blur'}],password:[{required:true,message:'请输入密码',trigger:'blur'}]}
const slides=ref([{url:'/login-slides/1.webp',caption:'一起成长，记录班级的每一份精彩'}]),current=ref(0),paused=ref(false),autoPlay=ref(!matchMedia('(prefers-reduced-motion: reduce)').matches)
const resetVisible=ref(false),resetBusy=ref(false),reset=reactive({username:'',code:'',password:'',confirm:''})
let timer
onMounted(async()=>{timer=setInterval(()=>{if(!document.hidden&&!paused.value&&autoPlay.value)current.value=(current.value+1)%slides.value.length},6500);try{slides.value=(await api.get('/api/branding')).data.slides}catch{}})
onBeforeUnmount(()=>clearInterval(timer))
async function handleLogin(){
  if(loading.value||!await formRef.value.validate().catch(()=>false))return
  loading.value=true
  try{
    const {data}=await api.post('/api/login',form)
    localStorage.setItem('remember-login',String(remember.value))
    if(remember.value)localStorage.setItem('login-identifier',form.username);else localStorage.removeItem('login-identifier')
    if(remember.value&&window.isSecureContext&&window.PasswordCredential&&navigator.credentials?.store){
      navigator.credentials.store(new PasswordCredential({id:form.username,password:form.password,name:data.user.real_name||form.username})).catch(()=>{})
    }
    authStore.login(data.access_token,data.user)
    form.password=''
    if(data.user.role==='admin'){authStore.setView('admin');router.push('/dashboard')}
    else router.push(data.user.is_class_leader?'/role-select':'/dashboard')
  }catch(err){ElMessage.error(err.response?.data?.detail||'登录失败')}finally{loading.value=false}
}
async function submitReset(){
  if(resetBusy.value)return
  if(reset.password.length<8||reset.password!==reset.confirm||!/^\d{8}$/.test(reset.code)||!reset.username.trim())return ElMessage.warning('请填写账号、8 位验证码及一致的新密码（至少 8 位）')
  resetBusy.value=true
  try{await api.post('/api/password-reset',{username:reset.username,code:reset.code,password:reset.password});form.username=reset.username;form.password='';resetVisible.value=false;ElMessage.success('密码已重置，请使用新密码登录')}catch(err){ElMessage.error(err.response?.data?.detail||'重置失败')}finally{resetBusy.value=false}
}
</script>
<style scoped>
.login-page{min-height:100dvh;padding:calc(24px + var(--safe-top)) max(24px,max(env(safe-area-inset-right),var(--safe-area-inset-right,0px))) calc(30px + max(env(safe-area-inset-bottom),var(--safe-area-inset-bottom,0px))) max(24px,max(env(safe-area-inset-left),var(--safe-area-inset-left,0px)));background:radial-gradient(ellipse at 12% 15%,var(--login-glow),transparent 65%),var(--el-bg-color-page);color:var(--el-text-color-primary)}
.login-top{display:flex;justify-content:space-between;align-items:center;max-width:1160px;margin:0 auto 30px;font-weight:750;color:var(--el-color-primary);letter-spacing:1px}.login-card{display:grid;grid-template-columns:1.25fr 1fr;max-width:1160px;margin:auto;background:var(--el-bg-color);border:1px solid var(--el-border-color);border-radius:28px;overflow:hidden;box-shadow:0 24px 80px #153b8514}.login-story{padding:38px;background:linear-gradient(150deg,#154bb8,#0c2c6a);color:white;min-width:0}.story-title>span{font-size:12px;letter-spacing:3px;color:#a9cfff}.story-title h1{max-width:450px;font-size:clamp(24px,2.6vw,36px);line-height:1.4;margin:18px 0 12px;letter-spacing:1px}.story-title p{color:#c7dcff;font-size:14px;margin-bottom:24px}.photo-frame{position:relative;background:#092451;border:1px solid #ffffff30;border-radius:16px;overflow:hidden}.photo-frame img{width:100%;aspect-ratio:4/3;display:block;object-fit:contain}.photo-caption{font-size:13px;padding:12px 16px 0;color:#d4e4ff}.slide-dots{display:flex;align-items:center;justify-content:center;gap:8px;padding:12px}.slide-dots button{width:9px;height:9px;padding:0;background:#ffffff55;border:0;border-radius:8px;cursor:pointer}.slide-dots button[aria-pressed=true]{width:24px;background:white}.slide-dots .pause-slide{height:24px;width:28px;color:white;background:transparent;font-size:14px}.login-form-wrap{padding:48px;display:flex;flex-direction:column;justify-content:center;min-width:0}.login-crest{margin-bottom:22px;object-fit:contain}.login-eyebrow{font-size:12px;letter-spacing:2px;color:var(--el-color-primary)}h2{font-size:30px;margin:12px 0}.login-muted{font-size:14px;color:var(--el-text-color-secondary);line-height:1.7;margin:0 0 30px}.login-options{display:flex;justify-content:space-between;align-items:center}.password-hint{font-size:12px;color:var(--el-text-color-secondary);line-height:1.7;margin:2px 0 22px}.login-submit{width:100%;height:46px}.login-footnote{margin:28px 0 0;color:var(--el-text-color-secondary);font-size:12px;text-align:center}
@media(max-width:900px){.login-story{padding:28px}.login-form-wrap{padding:30px}.login-card{grid-template-columns:1fr 1fr}}
@media(max-width:600px){.login-page{padding-left:16px;padding-right:16px}.login-top{margin-bottom:20px}.login-card{grid-template-columns:1fr;border-radius:20px}.login-story{padding:24px}.story-title h1{font-size:25px;margin:12px 0}.story-title p{margin-bottom:18px}.photo-frame img{aspect-ratio:16/9;max-height:220px}.login-form-wrap{padding:28px 24px}.login-crest{display:none}.login-muted{margin-bottom:22px}.login-footnote{margin-top:20px}}
</style>
