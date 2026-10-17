import { ElMessage } from 'element-plus'

export function showMailResult(data) {
  const result = data.detail || data
  if (data.success === false || result.success === false) {
    ElMessage.error(typeof result.detail === 'string' ? result.detail : '邮件发送失败，请检查邮件服务配置或发送记录')
    return
  }
  const message = `邮件发送完成：成功 ${result.sent || 0} 人，失败 ${result.failed || 0} 人`
  if (result.failed) ElMessage.warning(message)
  else ElMessage.success(message)
}
