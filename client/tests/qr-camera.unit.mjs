import test from 'node:test'
import assert from 'node:assert/strict'
import { createQrCamera, cameraErrorKind, scanBox } from '../src/utils/qrCamera.js'
const emptyReader = { querySelectorAll: () => [] }
const deferred = () => { let resolve; const promise = new Promise(done => { resolve = done }); return { promise, resolve } }

test('rear-camera constraint failure falls back and releases partially attached stream', async () => {
  let stops = 0, calls = [], cleared = 0
  const video = { srcObject: { getTracks: () => [{ stop: () => stops++ }] } }
  const camera = createQrCamera(() => ({
    isScanning: false,
    async start(_, config) { calls.push(config.videoConstraints); if (calls.length === 1) throw 'OverconstrainedError'; this.isScanning = true },
    async stop() { this.isScanning = false }, clear() { cleared++ },
  }), { querySelectorAll: () => [video] }, () => {})
  assert.equal(await camera.start(), true)
  assert.deepEqual(calls, [{ facingMode: { ideal: 'environment' } }, {}])
  assert.equal(stops, 1); assert.equal(cleared, 1)
  await camera.stop()
})

test('permission refusal stops after one attempt and permits user-initiated retry', async () => {
  let calls = 0
  const camera = createQrCamera(() => ({ async start() { if (++calls === 1) throw 'NotAllowedError: denied'; this.isScanning = true }, async stop() {}, clear() {} }), emptyReader, () => {})
  await assert.rejects(camera.start(), error => cameraErrorKind(error) === 'permission')
  assert.equal(calls, 1)
  assert.equal(await camera.start(), true)
  await camera.stop()
})

test('late permission grant after cancellation is released and cannot decode', async () => {
  const gate = deferred(); let stopped = 0, decoded = 0, callback
  const camera = createQrCamera(() => ({ async start(_, config, cb) { callback = cb; await gate.promise; this.isScanning = true }, async stop() { stopped++; this.isScanning = false }, clear() {} }), emptyReader, () => decoded++)
  const first = camera.start(), duplicate = camera.start()
  assert.equal(first, duplicate)
  const stop = camera.stop(); gate.resolve()
  assert.equal(await first, false); await stop; callback('late-code')
  assert.equal(stopped, 1); assert.equal(decoded, 0)
})

test('restart waits for previous camera to release', async () => {
  const gate = deferred(); let created = 0
  const camera = createQrCamera(() => { created++; return { async start() { this.isScanning = true }, async stop() { await gate.promise; this.isScanning = false }, clear() {} } }, emptyReader, () => {})
  await camera.start(); const stop = camera.stop(); const restart = camera.start('rear-camera')
  assert.equal(created, 1); gate.resolve(); await stop; assert.equal(await restart, true); assert.equal(created, 2)
  await camera.stop()
})

test('constructor errors recover and the scan box fits narrow/landscape views', async () => {
  let calls = 0
  const camera = createQrCamera(() => { if (++calls < 3) throw Error('decoder failed'); return { async start() { this.isScanning = true }, async stop() {}, clear() {} } }, emptyReader, () => {})
  await assert.rejects(camera.start(), /decoder failed/)
  assert.equal(await camera.start(), true); await camera.stop()
  for (const [w, h] of [[200, 150], [280, 210], [400, 180]]) {
    const box = scanBox(w, h); assert.equal(box.width, box.height); assert.ok(box.width < Math.min(w, h))
  }
})
