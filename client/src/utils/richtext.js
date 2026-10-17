import DOMPurify from 'dompurify'
export function richHtml(value = '') {
  if (!/<\/?[a-zA-Z][^>]*>/.test(value)) {
    const node = document.createElement('div')
    node.textContent = value
    value = `<p>${node.innerHTML.replace(/\n/g, '<br>')}</p>`
  }
  const html = DOMPurify.sanitize(value, {
    ALLOWED_TAGS: ['p','br','strong','b','em','i','u','s','h2','h3','ul','ol','li','blockquote','pre','code','a','img','hr'],
    ALLOWED_ATTR: ['href','title','src','alt','width','height'],
  })
  const doc = new DOMParser().parseFromString(html, 'text/html')
  doc.querySelectorAll('img').forEach(image => {
    if (!/^\/static\/rich\/[a-f0-9]{32}\.(jpg|png|webp)$/.test(image.getAttribute('src') || '')) image.remove()
    image.loading = 'lazy'; image.decoding = 'async'
  })
  doc.querySelectorAll('a').forEach(link => {
    const href = link.getAttribute('href') || ''
    if (!/^(https?:\/\/|mailto:|\/static\/rich\/[a-f0-9]{32}\.[a-z0-9]+$)/.test(href)) link.removeAttribute('href')
    link.rel = 'noopener noreferrer'
    link.target = '_blank'
  })
  return doc.body.innerHTML
}
export function plainText(value = '') {
  return new DOMParser().parseFromString(richHtml(value), 'text/html').body.textContent || ''
}
export function optionsList(value) {
  if (Array.isArray(value)) return value
  try { const parsed = JSON.parse(value); if (Array.isArray(parsed)) return parsed } catch {}
  return (value || '').replace(/，/g, ',').split(',').map(x => x.trim()).filter(Boolean)
}
