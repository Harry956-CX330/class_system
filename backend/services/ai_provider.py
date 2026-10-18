"""Single-worker AI admission control and a fixed-origin, bounded provider client."""
import json
import math
import socket
import threading
import time
import urllib.error
import urllib.request
from collections import OrderedDict, deque
from contextlib import contextmanager
from fastapi import HTTPException
from services.ai_settings import API_URL, MODEL

class AILimiter:
    def __init__(self, clock=time.monotonic):
        self.clock = clock
        self.lock = threading.Lock()
        self.active = set()
        self.users = OrderedDict()
        self.global_events = deque()
        self.cooldown_until = 0.0

    @staticmethod
    def reject(message, seconds, status=429):
        raise HTTPException(status, message, headers={'Retry-After': str(max(1, math.ceil(seconds)))})

    @contextmanager
    def admit(self, identity, settings):
        with self.lock:
            now = self.clock()
            if now < self.cooldown_until:
                self.reject('智谱服务正在限流，请等待后重试', self.cooldown_until - now)
            if identity in self.active:
                self.reject('你的上一条问题仍在处理，请等待回答', 3)
            if len(self.active) >= settings['max_concurrent']:
                self.reject('AI 正在回答其他同学的问题，请稍后重试', 5, 503)
            while self.global_events and now - self.global_events[0] >= 86400:
                self.global_events.popleft()
            user_events = self.users.pop(identity, deque())
            while user_events and now - user_events[0] >= 86400:
                user_events.popleft()
            self.users[identity] = user_events
            if user_events and now - user_events[-1] < settings['min_interval_seconds']:
                self.reject('提问过于频繁，请稍后再发送', settings['min_interval_seconds'] - (now - user_events[-1]))
            for events, limit, seconds, message in [
                (user_events, settings['user_per_minute'], 60, '本分钟提问次数已用完'),
                (user_events, settings['user_per_day'], 86400, '你在最近 24 小时的提问次数已用完'),
                (self.global_events, settings['global_per_minute'], 60, '全站本分钟 AI 调用次数已用完'),
                (self.global_events, settings['global_per_day'], 86400, '全站最近 24 小时 AI 调用次数已用完'),
            ]:
                recent = [stamp for stamp in events if now - stamp < seconds]
                if len(recent) >= limit:
                    self.reject(message + '，请等待后重试', seconds - (now - recent[-limit]))
            user_events.append(now)
            self.global_events.append(now)
            self.active.add(identity)
            while len(self.users) > 2048:
                self.users.popitem(last=False)
        try:
            yield
        finally:
            with self.lock:
                self.active.discard(identity)

    def cool_down(self, seconds):
        with self.lock:
            self.cooldown_until = max(self.cooldown_until, self.clock() + seconds)

limiter = AILimiter()

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None

# Never follow redirects with the API key and never accept a user-supplied API host.
provider_opener = urllib.request.build_opener(NoRedirect())


def complete(settings, messages, *, connection_test=False):
    payload = {
        'model': MODEL, 'messages': messages, 'stream': False,
        'max_tokens': 64 if connection_test else settings['max_tokens'],
        'thinking': {'type': 'disabled'}, 'temperature': 0.3,
    }
    request = urllib.request.Request(API_URL,
        data=json.dumps(payload, ensure_ascii=False).encode('utf-8'), method='POST',
        headers={'Authorization': 'Bearer ' + settings['api_key'], 'Content-Type': 'application/json'})
    try:
        with provider_opener.open(request, timeout=settings['timeout_seconds']) as response:
            raw = response.read(256 * 1024 + 1)
        if len(raw) > 256 * 1024:
            raise HTTPException(502, 'AI 返回内容过长，请缩小问题范围后重试')
        result = json.loads(raw)
    except urllib.error.HTTPError as error:
        # Provider error bodies can echo prompts or credentials. Never return/log them.
        status = error.code
        retry_value = error.headers.get('Retry-After', '30') if error.headers else '30'
        error.close()
        if status == 429:
            try: retry = max(5, min(120, int(retry_value)))
            except (ValueError, TypeError): retry = 30
            limiter.cool_down(retry)
            raise HTTPException(429, '智谱调用额度或并发达到限制，请等待后重试', headers={'Retry-After': str(retry)}) from None
        if status in (401, 403):
            raise HTTPException(503, 'AI 密钥无效或无模型权限，请联系管理员检查 AI 设置') from None
        if status == 400:
            raise HTTPException(502, '模型未能处理本次内容，请减少图片或缩短问题后重试') from None
        raise HTTPException(502, '智谱服务暂不可用，请稍后重试') from None
    except (TimeoutError, socket.timeout):
        raise HTTPException(504, 'AI 回答超时，请稍后重试或减少图片') from None
    except urllib.error.URLError as error:
        status = 504 if isinstance(error.reason, (TimeoutError, socket.timeout)) else 502
        raise HTTPException(status, 'AI 服务连接失败，请稍后重试') from None
    except (ValueError, UnicodeError, OSError):
        raise HTTPException(502, 'AI 服务返回异常，请稍后重试') from None
    try:
        choice = result['choices'][0]
        answer = choice['message']['content']
        if not isinstance(answer, str) or not answer.strip():
            raise ValueError()
        if choice.get('finish_reason') in {'sensitive', 'network_error', 'model_context_window_exceeded'}:
            raise ValueError()
    except (KeyError, IndexError, TypeError, ValueError):
        raise HTTPException(502, '本次没有生成可用回答，请调整问题后重试') from None
    usage = result.get('usage') or {}
    if not isinstance(usage, dict):
        usage = {}
    return {'answer': answer.strip()[:20000], 'model': MODEL,
            'truncated': choice.get('finish_reason') == 'length',
            'total_tokens': usage.get('total_tokens') if isinstance(usage.get('total_tokens'), int) else None}
