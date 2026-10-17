from models import QQConfig
from sqlalchemy.orm import Session
import json
import urllib.request

def _get_qq_config(db: Session):
    cfg = db.query(QQConfig).first()
    if not cfg or not cfg.enabled or not cfg.api_url:
        return None
    return cfg



def _send_qq_msg(api_url: str, endpoint: str, payload: dict) -> dict:
    """调用 OneBot HTTP API 发送消息"""
    # 分离 base_url 和 access_token
    from urllib.parse import urlparse, parse_qs
    parsed = urlparse(api_url)
    token = parse_qs(parsed.query).get('access_token', [None])[0]
    base = parsed._replace(query='').geturl()
    # Docker 内部网络优先用容器名 napcat，避免宿主外网 IP 回环问题
    base = base.replace('8.134.98.118:3001', 'napcat:3001')
    url = base.rstrip("/") + "/" + endpoint.lstrip("/")
    if token:
        url += ('&' if '?' in url else '?') + 'access_token=' + token
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        return {"status": "failed", "error": str(e)}

