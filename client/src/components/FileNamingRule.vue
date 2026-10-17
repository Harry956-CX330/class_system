<template>
  <div class="naming-rule">
    <div class="naming-options" role="group" aria-label="文件命名方案">
      <button v-for="preset in presets" :key="preset.id" type="button" class="naming-option"
        :class="{ selected: selected === preset.id }" :aria-pressed="selected === preset.id" @click="choose(preset)">
        <span class="naming-option-title">{{ preset.title }}<span v-if="preset.recommended" class="naming-badge">推荐</span></span>
        <span class="naming-option-desc">{{ preset.description }}</span>
      </button>
      <button type="button" class="naming-option" :class="{ selected: selected === 'custom' }"
        :aria-pressed="selected === 'custom'" @click="custom = true">
        <span class="naming-option-title">自定义规则</span><span class="naming-option-desc">保留原有规则，或按需组合字段</span>
      </button>
    </div>
    <div v-if="selected === 'custom'" class="naming-custom">
      <el-input :model-value="modelValue" maxlength="160" aria-label="自定义文件命名规则" placeholder="例如：{sid}-{name}-{seq}-{orig}"
        @update:model-value="$emit('update:modelValue', $event)" />
      <div class="naming-tokens">
        <button v-for="token in tokens" :key="token.key" type="button" @click="$emit('update:modelValue', modelValue + token.key)">{{ token.label }}</button>
      </div>
      <p class="naming-note">点击字段即可添加。扩展名由系统保留，无需输入 .pdf 等后缀。</p>
    </div>
    <div class="naming-preview" aria-live="polite">
      <span class="naming-preview-label">下载文件名示例</span>
      <span v-for="name in previews" :key="name" class="naming-preview-file">{{ name }}</span>
      <span class="naming-note">上传时无需手动改名。单个文件和打包下载采用相同规则。</span>
    </div>
    <p v-if="patternError" class="naming-error" role="alert">{{ patternError }}</p>
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
const props = defineProps({ modelValue: { type: String, default: '' }, groupEnabled: Boolean, taskTitle: String, taskDate: String })
const emit = defineEmits(['update:modelValue'])
const custom = ref(false)
const presets = computed(() => [
  { id: 'standard', title: '按学号整理', description: '学号 · 姓名 · 序号 · 原文件名', pattern: '{sid}-{name}-{seq}-{orig}', recommended: !props.groupEnabled },
  { id: 'compact', title: '简洁编号', description: '学号 · 姓名 · 序号', pattern: '{sid}-{name}-{seq}' },
  ...(props.groupEnabled ? [{ id: 'group', title: '按小组整理', description: '组名 · 姓名 · 序号 · 原文件名', pattern: '{group}-{name}-{seq}-{orig}', recommended: true }] : []),
])
const selected = computed(() => custom.value ? 'custom' : presets.value.find(p => p.pattern === props.modelValue)?.id || 'custom')
watch(() => props.modelValue, () => { if (presets.value.some(p => p.pattern === props.modelValue)) custom.value = false })
function choose(preset) { custom.value = false; emit('update:modelValue', preset.pattern) }
const tokens = computed(() => [
  { key: '{sid}', label: '完整学号' }, { key: '{name}', label: '学生姓名' }, { key: '{seq}', label: '文件序号' },
  { key: '{orig}', label: '原文件名' }, { key: '{task}', label: '任务标题' }, { key: '{date}', label: '发布日期' },
  { key: '{sid2}', label: '学号后两位' }, { key: '{sid3}', label: '学号后三位' },
  ...(props.groupEnabled ? [{ key: '{group}', label: '小组名称' }, { key: '{leader}', label: '组长姓名' }] : []),
])
const allowed = new Set(['sid', 'name', 'seq', 'orig', 'task', 'date', 'sid2', 'sid3', 'group', 'leader'])
const patternError = computed(() => {
  if (!props.modelValue.trim()) return '请选择命名方案，或填写自定义规则'
  const rest = props.modelValue.replace(/\{\{|\}\}/g, '').replace(/\{([a-z0-9]+)\}/g, (match, key) => allowed.has(key) ? '' : match)
  return /[{}]/.test(rest) ? '命名规则中有无效字段或括号，请使用下方提供的字段' : ''
})
const previews = computed(() => {
  const date = (props.taskDate || new Date().toLocaleDateString('sv-SE')).slice(0, 10).replaceAll('-', '')
  return ['实验报告', '补充材料'].map((orig, index) => {
    const values = { name: '张三', sid: '20240001', sid2: '01', sid3: '001', group: '第一小组', leader: '李四', task: props.taskTitle || '课程作业', orig, seq: String(index + 1).padStart(2, '0'), date }
    const pattern = props.modelValue || '{sid}-{name}-{seq}-{orig}'
    let base = pattern.replace(/\{\{|\}\}|\{([a-z0-9]+)\}/g, (match, key) => match === '{{' ? '{' : match === '}}' ? '}' : values[key] ?? match)
      .normalize('NFKC').replace(/[<>:"/\\|?*\u0000-\u001f\u007f]/g, '_').replace(/_+/g, '_').replace(/^[ .]+|[ .]+$/g, '') || '附件'
    if (/^(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(\.|$)/i.test(base)) base = '_' + base
    let bytes = 0
    base = [...base].filter(ch => (bytes += new TextEncoder().encode(ch).length) <= 160).join('').replace(/[ .]+$/g, '')
    return base + '.pdf'
  })
})
defineExpose({ patternError })
</script>

<style scoped>
.naming-rule { width:100%; }
.naming-options { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:10px; }
.naming-option { display:flex; flex-direction:column; gap:6px; padding:14px; text-align:left; background:#fff; border:1px solid #dce5ed; border-radius:10px; cursor:pointer; min-width:0; color:#203047; }
.naming-option.selected { border-color:#157f82; background:#edf7f6; box-shadow:0 0 0 1px #157f82 inset; }
.naming-option-title { font-size:14px; font-weight:600; display:flex; flex-wrap:wrap; align-items:center; gap:8px; }
.naming-option-desc { font-size:12px; color:#60798b; line-height:1.6; }
.naming-badge { font-size:11px; background:#d1eae5; color:#126d69; border-radius:5px; padding:0 6px; }
.naming-custom { padding-top:14px; }
.naming-tokens { display:flex; flex-wrap:wrap; gap:6px; padding-top:10px; }
.naming-tokens button { cursor:pointer; border:1px solid #dce5ed; border-radius:6px; padding:6px 10px; background:#f8fafc; color:#385368; font-size:12px; }
.naming-preview { display:flex; flex-direction:column; gap:6px; padding:14px; background:#f5f8fb; border-radius:10px; margin-top:12px; line-height:1.7; }
.naming-preview-label { color:#60798b; font-size:12px; }
.naming-preview-file { color:#28546b; font-size:13px; overflow-wrap:anywhere; }
.naming-note { font-size:12px; color:#6e8293; line-height:1.7; margin:6px 0 0; }
.naming-error { color:#bd3b3b; font-size:13px; line-height:1.6; }
@media(max-width:400px) { .naming-options { grid-template-columns:1fr; } }
</style>
