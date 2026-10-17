from models import QQConfig
from sqlalchemy.orm import Session
import json
import urllib.request
import threading
from fastapi import HTTPException

_qq_slot = threading.BoundedSemaphore(1)

class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None

def _get_qq_config(db: Session):
    cfg = db.query(QQConfig).first()
    if not cfg or not cfg.enabled or not cfg.api_url:
        return None
    return cfg



def _call_qq(api_url: str, endpoint: str, payload: dict) -> dict:
    """调用 OneBot HTTP API 发送消息"""
    # 分离 base_url 和 access_token
    from urllib.parse import urlparse, parse_qs
    parsed = urlparse(api_url)
    import os
    allowed = {h.strip() for h in os.environ.get("QQ_ALLOWED_HOSTS","127.0.0.1,localhost,napcat,8.163.67.49").split(",")}
    if parsed.scheme not in {"http","https"} or parsed.hostname not in allowed or parsed.username or parsed.password:
        return {"status":"failed","error":"机器人地址未在 QQ_ALLOWED_HOSTS 白名单中"}
    token = parse_qs(parsed.query).get('access_token', [None])[0]
    base = parsed._replace(query='').geturl()
    # Docker 内部网络优先用容器名 napcat，避免宿主外网 IP 回环问题
    base = base.replace('8.163.67.49:3001', 'napcat:3001') if os.environ.get('QQ_UPLOAD_ROOT') else base
    url = base.rstrip("/") + "/" + endpoint.lstrip("/")

    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json", **({"Authorization":"Bearer "+token} if token else {})})
    try:
        with urllib.request.build_opener(_NoRedirect).open(req, timeout=120 if endpoint in {'upload_group_file','upload_private_file'} else 20) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception:
        return {"status": "failed", "error": "QQ 服务连接失败，请检查机器人和访问令牌"}



def _send_qq_msg(api_url, endpoint, payload):
    if not _qq_slot.acquire(blocking=False):
        raise HTTPException(503, '已有 QQ 消息正在发送，请稍后重试', headers={'Retry-After': '15'})
    try:
        return _send_qq_media(api_url, endpoint, payload)
    finally:
        _qq_slot.release()


def _send_qq_media(api_url, endpoint, payload):
    from services.richtext import content_parts
    from services.notifications import media_info, public_media_url
    from fastapi import HTTPException
    import os
    message = payload.get("message")
    if not isinstance(message,str):
        return _call_qq(api_url,endpoint,payload)
    text,media = content_parts(message)
    segments = [{"type":"text","data":{"text":text}}]
    files = []
    shared = os.environ.get("QQ_UPLOAD_ROOT","")
    for item in media:
        path,name = media_info(item)
        if not path.is_file():
            return {"status":"failed","error":"正文引用的附件已丢失"}
        local = (shared.rstrip("/")+"/"+item["url"][len("/static/"):]) if shared else None
        if item["image"] and local and (endpoint == "send_group_msg" or path.stat().st_size <= 64*1024):
            segments.append({"type":"image","data":{"file":"file://"+local}})
        elif not item["image"] and local and endpoint == "send_group_msg" and path.stat().st_size <= 1024*1024:
            files.append((local,name))
        else:
            segments.append({"type":"text","data":{"text":"\n"+name+"（7 天内有效）: "+public_media_url(item)}})
    result = _call_qq(api_url,endpoint,dict(payload,message=segments))
    if not (result.get("status")=="ok" or result.get("retcode")==0):
        return result
    for local,name in files:
        group = "group_id" in payload
        response = _call_qq(api_url,"upload_group_file" if group else "upload_private_file",
            {("group_id" if group else "user_id"):payload["group_id" if group else "user_id"],"file":local,"name":name})
        if not (response.get("status")=="ok" or response.get("retcode")==0):
            return {"status":"failed","error":"文字已发送，但部分附件失败，请检查机器人文件权限","partial":True}
    return result
