import api from '../api'
// Browser streams to disk instead of keeping large Blob objects in Vue memory.
export async function browserDownload(path) {
  const { data } = await api.post('/api/transfers', { path })
  const link = document.createElement('a')
  link.href = data.url; link.target = '_blank'; link.rel = 'noopener noreferrer'
  document.body.appendChild(link); link.click(); link.remove()
}
