<template>
  <div class="rich-editor" :aria-busy="uploading">
    <div class="rich-toolbar" role="toolbar" aria-label="正文格式">
      <button v-for="tool in tools" :key="tool.label" type="button" :title="tool.label" :aria-label="tool.label"
        :class="{ active: editor?.isActive(tool.active) }" :disabled="disabled" @mousedown.prevent @click="tool.run()">{{ tool.text }}</button>
      <button type="button" :disabled="disabled" @click="addLink">链接</button>
      <button v-if="canAttach" type="button" :disabled="uploading || disabled" @click="fileInput.click()">{{ uploading ? '上传中…' : '图片 / 附件' }}</button>
      <input ref="fileInput" type="file" hidden accept=".jpg,.jpeg,.png,.webp,.gif,.pdf,.doc,.docx,.xls,.xlsx,.ppt,.pptx,.txt,.zip,.rar" @change="onFile" />
    </div>
    <editor-content :editor="editor" class="rich-edit-body" />
    <div class="rich-editor-hint">{{ canAttach ? '图片自动压缩；图片 ≤5 MiB，附件 ≤20 MiB。大附件在提醒中使用限时链接。' : '支持段落、标题、列表和链接。' }}</div>
  </div>
</template>
<script setup>
import { ref, watch, onBeforeUnmount, computed } from 'vue'
import { useEditor, EditorContent } from '@tiptap/vue-3'
import StarterKit from '@tiptap/starter-kit'
import Image from '@tiptap/extension-image'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useAuthStore } from '../stores/auth'
import { richHtml } from '../utils/richtext'
import api from '../api'
const props = defineProps({ modelValue: { type: String, default: '' }, disabled: Boolean })
const emit = defineEmits(['update:modelValue'])
const auth = useAuthStore()
const canAttach = computed(() => auth.isAdmin || auth.isClassLeader)
const fileInput = ref(null), uploading = ref(false)
const editor = useEditor({
  extensions: [StarterKit.configure({ link: { openOnClick: false, autolink: false } }), Image.configure({ allowBase64: false })],
  content: richHtml(props.modelValue), editable: !props.disabled,
  editorProps: { attributes: { role: 'textbox', 'aria-label': '富文本正文', 'aria-multiline': 'true' },
    handlePaste: (_, event) => {
      if (event.clipboardData?.files.length) {
        event.preventDefault(); if (canAttach.value) upload(event.clipboardData.files[0]); return true
      }
      return false
    }
  },
  onUpdate: ({ editor }) => emit('update:modelValue', editor.isEmpty ? '' : editor.getHTML()),
})
const tools = [
  { label: '加粗', text: 'B', active: 'bold', run: () => editor.value.chain().focus().toggleBold().run() },
  { label: '斜体', text: 'I', active: 'italic', run: () => editor.value.chain().focus().toggleItalic().run() },
  { label: '下划线', text: 'U', active: 'underline', run: () => editor.value.chain().focus().toggleUnderline().run() },
  { label: '二级标题', text: 'H2', active: 'heading', run: () => editor.value.chain().focus().toggleHeading({ level: 2 }).run() },
  { label: '无序列表', text: '• 列表', active: 'bulletList', run: () => editor.value.chain().focus().toggleBulletList().run() },
  { label: '有序列表', text: '1. 列表', active: 'orderedList', run: () => editor.value.chain().focus().toggleOrderedList().run() },
  { label: '引用', text: '引用', active: 'blockquote', run: () => editor.value.chain().focus().toggleBlockquote().run() },
  { label: '撤销', text: '↶', run: () => editor.value.chain().focus().undo().run() },
]
async function addLink() {
  try {
    const { value } = await ElMessageBox.prompt('输入 https:// 开头的网址；留空可移除链接', '插入链接', { inputValue: editor.value.getAttributes('link').href || '', inputValidator: v => !v || /^https?:\/\//.test(v) || '请输入有效网址' })
    if (value) editor.value.chain().focus().extendMarkRange('link').setLink({ href: value }).run()
    else editor.value.chain().focus().unsetLink().run()
  } catch {}
}
async function onFile(event) { const file = event.target.files[0]; event.target.value = ''; if (file) await upload(file) }
async function upload(file) {
  if (uploading.value || props.disabled) return
  const image = /\.(jpe?g|png|webp|gif)$/i.test(file.name)
  if (file.size > (image ? 5 : 20)*1024*1024) return ElMessage.warning(image ? '图片不能超过 5 MiB' : '附件不能超过 20 MiB')
  uploading.value = true
  try {
    const data = new FormData(); data.append('file',file)
    const { data: result } = await api.post('/api/media',data,{ timeout: 0 })
    if (result.image) editor.value.chain().focus().setImage({ src: result.url, alt: result.name }).run()
    else editor.value.chain().focus().insertContent([{ type:'paragraph', content:[{ type:'text',text:'📎 '+result.name,marks:[{ type:'link',attrs:{ href:result.url,title:result.name } }] }] },{ type:'paragraph' }]).run()
  } catch (error) { ElMessage.error(error.response?.data?.detail || '附件上传失败') }
  finally { uploading.value = false }
}
watch(() => props.modelValue, value => { if (editor.value && value !== editor.value.getHTML()) editor.value.commands.setContent(richHtml(value), { emitUpdate: false }) })
watch(() => props.disabled, value => editor.value?.setEditable(!value))
onBeforeUnmount(() => editor.value?.destroy())
</script>
