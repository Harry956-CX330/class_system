import { readdir, readFile, writeFile } from 'node:fs/promises'
import { gzipSync } from 'node:zlib'
import { createHash } from 'node:crypto'
import { execFileSync } from 'node:child_process'
let revision = process.env.APP_REVISION || 'unknown'
if (revision === 'unknown') {
  try { revision = execFileSync('git', ['rev-parse', 'HEAD'], { encoding:'utf8', stdio:['ignore','pipe','ignore'] }).trim() } catch {}
}
const { version } = JSON.parse(await readFile('package.json', 'utf8'))
const index = await readFile('dist/index.html')
const entries = [...index.toString().matchAll(/(?:src|href)="(\/assets\/[^"?]+\.(?:js|css))"/g)].map(match => match[1])
const assets = Object.fromEntries(await Promise.all(entries.map(async path => [path, createHash('sha256').update(await readFile('dist' + path)).digest('hex') ])))
await writeFile('dist/build-info.json', JSON.stringify({version, revision, built_at:new Date().toISOString(), index_sha256:createHash('sha256').update(index).digest('hex'), assets}, null, 2) + '\n')
for (const name of await readdir('dist/assets')) {
  if (!/\.(js|css|svg)$/.test(name)) continue
  const bytes = await readFile(`dist/assets/${name}`)
  if (bytes.length > 1024) await writeFile(`dist/assets/${name}.gz`, gzipSync(bytes, { level: 9 }))
}
