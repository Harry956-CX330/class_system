<template><select class="theme-switch" aria-label="外观主题" :value="theme" @change="setTheme($event.target.value)"><option value="system">跟随系统</option><option value="light">浅色主题</option><option value="dark">深色主题</option></select></template>
<script setup>
import { theme, setTheme } from '../theme'
</script>
<style scoped>
.theme-switch{max-width:110px;min-height:34px;border:1px solid var(--el-border-color);border-radius:8px;background:var(--el-bg-color);color:var(--el-text-color-primary);padding:4px 7px;font-size:12px}
</style>
