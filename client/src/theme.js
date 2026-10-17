import { ref } from 'vue'
const stored = localStorage.getItem('theme')
export const theme = ref(['light','dark','system'].includes(stored) ? stored : 'system')
const media = matchMedia('(prefers-color-scheme: dark)')
function apply() {
  const dark = theme.value === 'dark' || (theme.value === 'system' && media.matches)
  document.documentElement.classList.toggle('dark', dark)
  document.documentElement.style.colorScheme = dark ? 'dark' : 'light'
  document.querySelector('meta[name="theme-color"]')?.setAttribute('content', dark ? '#111c30' : '#f2f6ff')
  window.Capacitor?.Plugins?.SystemBars?.setStyle({style:dark?'DARK':'LIGHT'}).catch(()=>{})
}
export function setTheme(value) { theme.value=value; localStorage.setItem('theme',value); apply() }
media.addEventListener('change',apply)
apply()
