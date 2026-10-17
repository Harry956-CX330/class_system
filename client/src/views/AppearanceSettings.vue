<template>
  <el-card class="page-card" shadow="never">
    <div class="page-header"><h2 class="page-title">登录页轮播图</h2><el-button type="primary" :loading="saving" :disabled="uploading" @click="save">保存设置</el-button></div>
    <p>登录页公开展示这些照片，请勿上传私人资料。最多 6 张，每张不超过 5 MiB，系统自动压缩；默认照片可随时恢复。</p>
    <div class="branding-actions"><label class="upload-label">{{uploading?'正在压缩上传…':'添加图片'}}<input type="file" accept="image/jpeg,image/png,image/webp" :disabled="uploading||slides.length>=6" @change="upload" /></label><el-button @click="restore">恢复默认照片</el-button></div>
    <div class="branding-list"><div v-for="(slide,i) in slides" :key="slide.url" class="branding-item"><img :src="slide.url" :alt="slide.caption" loading="lazy" /><el-input v-model="slide.caption" maxlength="60" :aria-label="`第 ${i+1} 张图片说明`" /><div><el-button :disabled="i===0" @click="move(i,-1)">上移</el-button><el-button :disabled="i===slides.length-1" @click="move(i,1)">下移</el-button><el-button type="danger" :disabled="slides.length===1" @click="slides.splice(i,1)">移除</el-button></div></div></div>
  </el-card>
</template>
<script setup>
import { ref,onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import api from '../api'
const slides=ref([]),saving=ref(false),uploading=ref(false)
onMounted(async()=>{try{slides.value=(await api.get('/api/branding')).data.slides}catch{ElMessage.error('加载失败')}})
function move(i,d){[slides.value[i],slides.value[i+d]]=[slides.value[i+d],slides.value[i]]}
function restore(){slides.value=['一起成长，记录班级的每一份精彩','同心协力，共享荣誉','青春同行，向阳而生'].map((caption,i)=>({url:`/login-slides/${i+1}.webp`,caption}))}
async function upload(event){const file=event.target.files[0];if(!file)return;event.target.value='';if(file.size>5*1024*1024)return ElMessage.warning('图片不能超过 5 MiB');uploading.value=true;try{const data=new FormData();data.append('file',file);slides.value.push((await api.post('/api/branding/images',data)).data);ElMessage.success('上传完成，请保存设置')}catch(err){ElMessage.error(err.response?.data?.detail||'上传失败')}finally{uploading.value=false}}
async function save(){saving.value=true;try{await api.put('/api/branding',{slides:slides.value});ElMessage.success('登录页照片已更新')}catch(err){ElMessage.error(err.response?.data?.detail||'保存失败')}finally{saving.value=false}}
</script>
<style scoped>
.branding-actions{display:flex;flex-wrap:wrap;gap:12px;margin:22px 0}.upload-label{position:relative;padding:8px 16px;background:var(--el-color-primary);color:white;border-radius:8px;cursor:pointer}.upload-label input{position:absolute;inset:0;opacity:0;width:100%;cursor:pointer}.branding-list{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(260px,100%),1fr));gap:18px}.branding-item{display:flex;flex-direction:column;gap:12px;padding:16px;border:1px solid var(--el-border-color);border-radius:12px;min-width:0}.branding-item img{width:100%;height:180px;object-fit:contain;background:#112b52;border-radius:8px}.branding-item>div{display:flex;gap:6px;flex-wrap:wrap}p{line-height:1.8;color:var(--el-text-color-secondary)}
</style>
