// Compress locally before sending: no public upload URL and no original image metadata.
export async function prepareAiImage(file) {
  if (!/^image\/(jpeg|png|webp)$/.test(file.type) || file.size > 10 * 1024 * 1024) {
    throw new Error('请选择 10 MiB 以内的 JPG、PNG 或 WebP 图片')
  }
  const url = URL.createObjectURL(file)
  try {
    const image = new Image()
    image.src = url
    await new Promise((resolve, reject) => { image.onload = resolve; image.onerror = () => reject(new Error('图片无法读取')) })
    if (image.naturalWidth * image.naturalHeight > 16000000) throw new Error('图片分辨率过大，请裁剪到题目或公告区域后再导入')
    for (const [edge, quality] of [[1600, 0.88], [1600, 0.75], [1280, 0.72], [1024, 0.65], [800, 0.55]]) {
      const scale = Math.min(1, edge / Math.max(image.naturalWidth, image.naturalHeight))
      const canvas = document.createElement('canvas')
      canvas.width = Math.max(1, Math.round(image.naturalWidth * scale))
      canvas.height = Math.max(1, Math.round(image.naturalHeight * scale))
      const context = canvas.getContext('2d')
      if (!context) throw new Error('当前浏览器无法处理图片，请换用系统浏览器')
      context.fillStyle = '#fff'; context.fillRect(0, 0, canvas.width, canvas.height)
      context.drawImage(image, 0, 0, canvas.width, canvas.height)
      const blob = await new Promise(resolve => canvas.toBlob(resolve, 'image/jpeg', quality))
      canvas.width = 0; canvas.height = 0
      if (blob && blob.size <= 160 * 1024) {
        const dataUrl = await new Promise((resolve, reject) => {
          const reader = new FileReader(); reader.onload = () => resolve(reader.result); reader.onerror = reject; reader.readAsDataURL(blob)
        })
        return { name: file.name.slice(0, 120), data_url: dataUrl }
      }
    }
    throw new Error('图片内容过于复杂，请先裁剪题目区域')
  } finally { URL.revokeObjectURL(url) }
}
