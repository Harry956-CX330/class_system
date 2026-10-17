<template><div class="rich-content" @click="openAttachment" v-html="richHtml(content)" /></template>
<script setup>
import { richHtml } from '../utils/richtext'
import { browserDownload } from '../utils/download'
import { ElMessage } from 'element-plus'
defineProps({ content: { type: String, default: '' } })
async function openAttachment(event) {
  const href = event.target.closest('a')?.getAttribute('href') || ''
  if (!/^\/static\/rich\/[a-f0-9]{32}\.[a-z0-9]+$/.test(href)) return
  event.preventDefault()
  try { await browserDownload(href) }
  catch (error) { ElMessage.error(error.response?.data?.detail || '附件下载失败，请重试') }
}
</script>
