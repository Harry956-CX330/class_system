import { readdir, readFile, writeFile } from 'node:fs/promises'
import { gzipSync } from 'node:zlib'
for (const name of await readdir('dist/assets')) {
  if (!/\.(js|css|svg)$/.test(name)) continue
  const bytes = await readFile(`dist/assets/${name}`)
  if (bytes.length > 1024) await writeFile(`dist/assets/${name}.gz`, gzipSync(bytes, { level: 9 }))
}
