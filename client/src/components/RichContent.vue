<template><div class="rich-content" v-html="richHtml(content)" /></template>
<script setup>
import { richHtml } from '../utils/richtext'
defineProps({ content: { type: String, default: '' } })
</script>
