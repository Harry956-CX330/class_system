import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import Components from 'unplugin-vue-components/vite'
import { ElementPlusResolver } from 'unplugin-vue-components/resolvers'
import { readFileSync } from 'node:fs'
import { execFileSync } from 'node:child_process'
const { version } = JSON.parse(readFileSync(new URL('./package.json', import.meta.url), 'utf8'))
let revision = process.env.APP_REVISION || 'unknown'
if (revision === 'unknown') {
  try { revision = execFileSync('git', ['rev-parse', '--short=8', 'HEAD'], { encoding: 'utf8', stdio:['ignore','pipe','ignore'] }).trim() } catch {}
}

export default defineConfig({
  define: { __APP_VERSION__: JSON.stringify(version), __APP_REVISION__: JSON.stringify(revision.slice(0,8)) },
  plugins: [vue(), Components({ resolvers: [ElementPlusResolver()], dts: false })],
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/static': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})
