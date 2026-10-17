"""Bandwidth-aware MIME messages and OneBot attachment references."""
import html
import json
import mimetypes
from pathlib import Path
from email.message import EmailMessage
from config import PUBLIC_BASE_URL, MAIL_INLINE_BYTES, MAIL_BATCH_BYTES
from services.files import safe_upload_path
from services.richtext import clean_html, content_parts
from fastapi import HTTPException

def media_info(item):
    path = Path(safe_upload_path(item["url"][len("/static/"):]))
    name = item["name"]
    metadata = path.with_suffix(path.suffix+".meta.json")
    try:
        name = json.loads(metadata.read_text(encoding="utf-8")).get("name",name)
    except (OSError,ValueError):
        pass
    return path, name.replace("\r", "").replace("\n", "")[:180]

def public_media_url(item):
    if not PUBLIC_BASE_URL.startswith(("https://", "http://")):
        raise HTTPException(503,"请配置 PUBLIC_BASE_URL，以便发送图片和附件下载链接")
    from routers.transfers import make_ticket
    return PUBLIC_BASE_URL + "/api/transfers/open/" + make_ticket(item["url"],seconds=7*24*3600)

def build_email(sender, recipient, subject, body, recipients=1):
    cleaned = clean_html(body)
    text,media = content_parts(cleaned)
    budget = min(MAIL_INLINE_BYTES, MAIL_BATCH_BYTES // max(recipients,1))
    small,links = [],[]
    for index,item in enumerate(media):
        path,name = media_info(item)
        if not path.is_file():
            raise HTTPException(409,"正文中的附件已丢失，请先更新正文")
        # Base64 + MIME overhead is budgeted before attaching bytes.
        estimated = path.stat().st_size*4//3+2048
        if estimated <= budget:
            budget -= estimated
            cid = f"class-media-{index}"
            small.append((item,path,name,cid))
            if item["image"]:
                cleaned = cleaned.replace(item["url"],"cid:"+cid)
            else:
                cleaned = cleaned.replace(item["url"],"#attachment-"+cid)
        else:
            url = public_media_url(item)
            # Do not embed large remote images (50 recipients fetching simultaneously).
            if item["image"]:
                import re
                cleaned = re.sub(r'<img[^>]*src="'+re.escape(item["url"])+r'"[^>]*>', '<p><a href="'+html.escape(url,quote=True)+'">查看图片：'+html.escape(name)+'</a></p>',cleaned)
            else:
                cleaned = cleaned.replace(item["url"],html.escape(url,quote=True))
            links.append(f"{name}: {url}")
    message = EmailMessage()
    message["From"],message["To"],message["Subject"] = sender,recipient,subject.replace("\r","").replace("\n","")[:300]
    message.set_content(text+("\n\n附件与图片（链接有效期 7 天）：\n"+"\n".join(links) if links else ""))
    message.add_alternative('<div style="white-space:pre-wrap;font-family:sans-serif;line-height:1.7">'+cleaned+'</div>',subtype="html")
    html_part = message.get_payload()[-1]
    for item,path,name,cid in small:
        major,minor = (mimetypes.guess_type(path.name)[0] or "application/octet-stream").split("/",1)
        if item["image"]:
            html_part.add_related(path.read_bytes(),maintype=major,subtype=minor,cid="<"+cid+">",filename=name,disposition="inline")
        else:
            message.add_attachment(path.read_bytes(),maintype=major,subtype=minor,filename=name)
    return message
