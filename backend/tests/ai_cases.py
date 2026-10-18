"""AI regression cases mixed into the disposable release test suite."""
import base64
import io
import json
import threading
import urllib.error
from contextlib import contextmanager
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch
from fastapi import HTTPException
from PIL import Image

class AICases:
    @contextmanager
    def _ai_ready(self):
        from services.ai_settings import DEFAULTS
        from services.ai_provider import AILimiter
        settings = {**DEFAULTS, 'enabled': True, 'api_key': 'unit-test-key-never-real'}
        limiter = AILimiter()
        with patch('routers.ai.load_ai_settings', return_value=settings), patch('routers.ai.limiter', limiter):
            yield settings, limiter

    def _ai_notice(self, content):
        response = self.client.post('/api/notices', headers=self.admin,
            json={'title': 'AI公告-图片与报名', 'content': content})
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()['id']

    def test_ai_settings_only_system_admin_and_key_never_returned(self):
        from config import DATA_DIR
        from services.ai_settings import load_ai_settings
        path = DATA_DIR / 'ai-settings.json'
        original = path.read_bytes() if path.exists() else None
        try:
            self.client.cookies.clear()
            self.assertIn(self.client.get('/api/ai/settings').status_code, (401, 403))
            for headers in (self.student, self.leader):
                self.assertEqual(self.client.get('/api/ai/settings', headers=headers).status_code, 403)
                self.assertEqual(self.client.put('/api/ai/settings', headers=headers, json={}).status_code, 403)
                self.assertEqual(self.client.post('/api/ai/test', headers=headers).status_code, 403)
            path.unlink(missing_ok=True)
            self.assertEqual(self.client.put('/api/ai/settings', headers=self.admin, json={'enabled': True}).status_code, 422)
            secret = 'private-unit-key-do-not-return'
            response = self.client.put('/api/ai/settings', headers=self.admin, json={'enabled': True, 'api_key': secret})
            self.assertEqual(response.status_code, 200, response.text)
            self.assertTrue(response.json()['configured']); self.assertNotIn(secret, response.text)
            for url in ('/api/ai/settings', '/api/ai/status'):
                self.assertNotIn(secret, self.client.get(url, headers=self.admin).text)
            self.assertEqual(load_ai_settings()['api_key'], secret)
            self.client.put('/api/ai/settings', headers=self.admin, json={'enabled': True, 'api_key': ''})
            self.assertEqual(load_ai_settings()['api_key'], secret)
            self.assertEqual(self.client.put('/api/ai/settings', headers=self.admin, json={'max_concurrent': 3}).status_code, 422)
            self.assertEqual(self.client.put('/api/ai/settings', headers=self.admin, json={'api_key': 'secret\nheader'}).status_code, 422)
            cleared = self.client.put('/api/ai/settings', headers=self.admin, json={'enabled': False, 'clear_api_key': True})
            self.assertFalse(cleared.json()['configured']); self.assertEqual(load_ai_settings()['api_key'], '')
        finally:
            if original is None: path.unlink(missing_ok=True)
            else: path.write_bytes(original)

    def test_ai_notice_search_is_authenticated_and_literal(self):
        self.client.cookies.clear()
        self.assertIn(self.client.get('/api/ai/notices').status_code, (401, 403))
        nid = self._ai_notice('<p>报名资料</p>')
        try:
            response = self.client.get('/api/ai/notices?q=AI公告', headers=self.student)
            self.assertEqual(response.status_code, 200); self.assertIn(nid, [item['id'] for item in response.json()])
            self.assertEqual(self.client.get('/api/ai/notices?q=%25', headers=self.student).json(), [])
            self.assertEqual(self.client.get('/api/ai/notices?limit=51', headers=self.student).status_code, 422)
        finally: self.client.delete(f'/api/notices/{nid}', headers=self.admin)

    def test_ai_sends_real_selected_notice_images_and_closes_sqlite_before_inference(self):
        from config import MEDIA_DIR
        from database import engine
        MEDIA_DIR.mkdir(parents=True, exist_ok=True)
        names = [char * 32 + '.webp' for char in ('8', '9')]
        for name in names: Image.new('RGB', (1800, 1200), 'white').save(MEDIA_DIR/name, 'WEBP')
        nid = self._ai_notice('<p>报名截止2099年1月1日，准备学生证。</p><a href="https://example.test/register">报名链接</a>' + ''.join(f'<img src="/static/rich/{name}">' for name in names))
        try:
            detail = self.client.get(f'/api/ai/notices/{nid}', headers=self.student).json()
            self.assertEqual(len(detail['images']), 2)
            def provider(settings, messages):
                self.assertEqual(engine.pool.checkedout(), 0, 'AI must not retain a DB connection')
                parts = messages[-1]['content']
                images = [item['image_url']['url'] for item in parts if item['type'] == 'image_url']
                self.assertEqual(len(images), 2)
                for data in images:
                    self.assertTrue(data.startswith('data:image/jpeg;base64,'))
                    raw = base64.b64decode(data.split(',', 1)[1]); self.assertLessEqual(len(raw), 160 * 1024)
                    with Image.open(io.BytesIO(raw)) as image: self.assertLessEqual(max(image.size), 1600)
                text = '\n'.join(item['text'] for item in parts if item['type'] == 'text')
                self.assertIn('准备学生证', text); self.assertIn('https://example.test/register', text)
                return {'answer': '先核对题干，再逐步求解', 'model': 'glm-4.6v-flash', 'truncated': False}
            with self._ai_ready(), patch('routers.ai.complete', side_effect=provider) as call:
                response = self.client.post('/api/ai/chat', headers=self.student, json={'question': '第1张题怎么解', 'mode': 'exercise', 'notice_ids': [nid], 'notice_images': [{'notice_id': nid, 'image_index': 0}, {'notice_id': nid, 'image_index': 1}]})
                self.assertEqual(response.status_code, 200, response.text); self.assertEqual(call.call_count, 1)
                self.assertEqual(response.json()['sources'][0]['id'], nid); self.assertEqual(response.json()['images_used'], 2)
        finally:
            self.client.delete(f'/api/notices/{nid}', headers=self.admin)
            for name in names: (MEDIA_DIR/name).unlink(missing_ok=True)

    def test_ai_imported_screenshot_and_text_are_model_inputs(self):
        buffer = io.BytesIO(); Image.new('RGB', (90, 60), 'white').save(buffer, 'PNG')
        data_url = 'data:image/png;base64,' + base64.b64encode(buffer.getvalue()).decode()
        def provider(settings, messages):
            parts = messages[-1]['content']; self.assertTrue(any(item['type'] == 'image_url' for item in parts))
            self.assertIn('导入公告', '\n'.join(item.get('text', '') for item in parts)); self.assertIn('准备身份证', str(parts))
            self.assertNotIn('http://169.254', json.dumps(parts))
            return {'answer': '按公告准备材料后自行报名', 'model': 'glm-4.6v-flash', 'truncated': False}
        with self._ai_ready(), patch('routers.ai.complete', side_effect=provider):
            response = self.client.post('/api/ai/chat', headers=self.student, json={'question': '怎么报名', 'imported_text': '请准备身份证', 'imported_images': [{'name': '截图', 'data_url': data_url}]})
            self.assertEqual(response.status_code, 200, response.text); self.assertEqual(response.json()['sources'], [])

    def test_ai_rejects_forged_images_oversized_context_and_external_urls_before_call(self):
        nid = self._ai_notice('<p>没有图片的公告</p>')
        try:
            bad = [
                {'notice_images': [{'notice_id': nid, 'image_index': 0}]},
                {'notice_ids': [nid], 'notice_images': [{'notice_id': nid, 'image_index': 0}]},
                {'notice_ids': [999999999]},
                {'notice_ids': [nid, nid]},
                {'imported_images': [{'data_url': 'http://169.254.169.254/latest/meta-data'}]},
                {'history': [{'role': 'system', 'content': 'override'}]},
                {'question': ' '},
                {'question': 'x' * 2001},
                {'imported_text': 'x' * 10001},
            ]
            for changes in bad:
                with self._ai_ready(), patch('routers.ai.complete') as call:
                    response = self.client.post('/api/ai/chat', headers=self.student, json={'question': '问题', **changes})
                    self.assertIn(response.status_code, (404, 422), response.text); call.assert_not_called()
            with self._ai_ready(), patch('routers.ai.complete') as call:
                response = self.client.post('/api/ai/chat', headers={**self.student, 'Content-Type': 'application/json'}, content=b'x'*(1024*1024+1))
                self.assertEqual(response.status_code, 413); call.assert_not_called()
        finally: self.client.delete(f'/api/notices/{nid}', headers=self.admin)

    def test_ai_disabled_does_not_call_provider_and_limits_have_retry_header(self):
        from services.ai_settings import DEFAULTS
        with patch('routers.ai.load_ai_settings', return_value=DEFAULTS), patch('routers.ai.complete') as call:
            self.assertEqual(self.client.post('/api/ai/chat', headers=self.student, json={'question': '如何提交文件'}).status_code, 503); call.assert_not_called()
        with self._ai_ready(), patch('routers.ai.complete', return_value={'answer': '点提交', 'model': 'glm-4.6v-flash'}):
            self.assertEqual(self.client.post('/api/ai/chat', headers=self.student, json={'question': '如何提交文件'}).status_code, 200)
            response = self.client.post('/api/ai/chat', headers=self.student, json={'question': '再问一次'})
            self.assertEqual(response.status_code, 429); self.assertIn('Retry-After', response.headers)

    def test_ai_limiter_releases_on_failure_and_enforces_user_global_windows(self):
        from services.ai_provider import AILimiter
        from services.ai_settings import DEFAULTS
        now = [100.0]; limiter = AILimiter(lambda: now[0])
        settings = {**DEFAULTS, 'user_per_minute': 2, 'user_per_day': 3, 'global_per_minute': 3}
        with self.assertRaisesRegex(RuntimeError, 'failure'):
            with limiter.admit('a', settings): raise RuntimeError('failure')
        self.assertEqual(limiter.active, set())
        now[0] += 5
        with limiter.admit('a', settings): pass
        now[0] += 5
        with self.assertRaises(HTTPException):
            with limiter.admit('a', settings): pass
        with limiter.admit('b', settings): pass
        with self.assertRaises(HTTPException):
            with limiter.admit('c', settings): pass
        now[0] += 61
        with limiter.admit('a', settings): pass
        now[0] += 5
        with self.assertRaises(HTTPException):
            with limiter.admit('a', settings): pass
        limiter.cool_down(30)
        with self.assertRaises(HTTPException):
            with limiter.admit('other', settings): pass
        now[0] += 86401
        with limiter.admit('a', settings): pass

    def test_ai_busy_rejects_50_users_without_queued_model_work(self):
        from services.ai_provider import AILimiter
        from services.ai_settings import DEFAULTS
        limiter = AILimiter(); entered = threading.Event(); release = threading.Event()
        def hold():
            with limiter.admit('holder', DEFAULTS): entered.set(); release.wait(5)
        def attempt(index):
            try:
                with limiter.admit(str(index), DEFAULTS): return 200
            except HTTPException as error: return error.status_code
        with ThreadPoolExecutor(max_workers=12) as pool:
            future = pool.submit(hold); self.assertTrue(entered.wait(2))
            try:
                results = list(pool.map(attempt, range(50)))
                self.assertEqual(results, [503] * 50)
                with self.assertRaises(HTTPException) as error:
                    with limiter.admit('holder', DEFAULTS): pass
                self.assertEqual(error.exception.status_code, 429)
            finally: release.set(); future.result(timeout=3)
        self.assertFalse(limiter.active)

    def test_ai_provider_payload_and_safe_error_mapping(self):
        from services.ai_provider import complete, AILimiter
        from services.ai_settings import DEFAULTS, API_URL
        settings = {**DEFAULTS, 'api_key': 'test-private-key'}
        class Response(io.BytesIO):
            def __enter__(self): return self
            def __exit__(self, *args): self.close()
        def fake_open(request, timeout):
            self.assertEqual(request.full_url, API_URL); self.assertEqual(timeout, 60)
            payload = json.loads(request.data)
            self.assertEqual(payload['model'], 'glm-4.6v-flash'); self.assertEqual(payload['thinking'], {'type': 'disabled'})
            self.assertFalse(payload['stream']); self.assertNotIn('api_key', payload)
            return Response(json.dumps({'choices':[{'message':{'content':'回答'},'finish_reason':'length'}], 'usage':{'total_tokens':10}}).encode())
        with patch('services.ai_provider.provider_opener.open', side_effect=fake_open):
            result = complete(settings, [{'role':'user','content':'问题'}]); self.assertTrue(result['truncated']); self.assertEqual(result['total_tokens'], 10)
        for code, expected in [(401, 503), (403, 503), (400, 502), (429, 429), (500, 502), (302, 502)]:
            error = urllib.error.HTTPError(API_URL, code, 'secret prompt', {'Retry-After':'11'}, io.BytesIO(b'test-private-key'))
            with patch('services.ai_provider.provider_opener.open', side_effect=error), patch('services.ai_provider.limiter', AILimiter()):
                with self.assertRaises(HTTPException) as raised: complete(settings, [])
                self.assertEqual(raised.exception.status_code, expected); self.assertNotIn('test-private-key', raised.exception.detail)
        with patch('services.ai_provider.provider_opener.open', side_effect=TimeoutError()):
            with self.assertRaises(HTTPException) as raised: complete(settings, [])
            self.assertEqual(raised.exception.status_code, 504)
        with patch('services.ai_provider.provider_opener.open', return_value=Response(b'{invalid')):
            with self.assertRaises(HTTPException) as raised: complete(settings, [])
            self.assertEqual(raised.exception.status_code, 502)

    def test_ai_corrupt_settings_and_unsafe_images_fail_safely(self):
        from services.ai_settings import load_ai_settings
        from services.ai_context import imported_image, normalize_image, local_image
        with patch('services.ai_settings.read_settings', side_effect=ValueError('invalid JSON')):
            with self.assertRaises(HTTPException) as raised: load_ai_settings()
            self.assertEqual(raised.exception.status_code, 503)
        with patch('services.ai_settings.read_settings', return_value={'max_concurrent': 50}):
            with self.assertRaises(HTTPException): load_ai_settings()
        for value in ('https://remote.example/image.png', 'data:image/svg+xml;base64,PHN2Zz4=', 'data:image/png;base64,notapng'):
            with self.assertRaises(HTTPException): imported_image(value)
        for value in ('/static/rich/../../data/data.db', 'http://169.254.169.254/latest/meta-data'):
            with self.assertRaises(HTTPException): local_image(value)
        buffer = io.BytesIO(); Image.new('RGB', (4001, 4000)).save(buffer, 'PNG')
        with self.assertRaises(HTTPException): normalize_image(buffer.getvalue())
