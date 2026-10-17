"""Shared presentation for every mail, group notice and private reminder."""
import html
import re
from datetime import datetime, timezone, timedelta
from config import PUBLIC_BASE_URL
from services.richtext import clean_html, content_parts

BRAND = '数科2441智能班务系统'

def notification_parts(body, subject='班务提醒'):
    # Older callers supply a first-line heading. Normalize it in one place.
    match = re.match(r'^\s*【([^】\n]+)】\s*\n?', body or '')
    title = match[1] if match else subject
    title = re.sub(r'^(?:数科2441班|数科2441智能班务系统)[·：\s]*', '', title).strip() or '班务提醒'
    value = body[match.end():] if match else body
    value = re.sub(r'\n+---\s*\n此邮件由智能班务系统自动发送，请勿回复\s*$', '', value or '')
    content = clean_html(value)
    text, media = content_parts(content)
    sent = datetime.now(timezone(timedelta(hours=8))).strftime('%Y-%m-%d %H:%M')
    return {'title':title, 'html':content, 'text':text, 'media':media, 'sent':sent}

def qq_text(parts):
    url = '\n班务入口：'+PUBLIC_BASE_URL if PUBLIC_BASE_URL else ''
    return f'【{BRAND}】\n{parts["title"]}\n────────────\n{parts["text"]}\n────────────\n发送时间：{parts["sent"]}（北京时间）{url}\n系统提醒 · 如已完成，请忽略；有疑问请联系发布人。'

def email_document(parts, content):
    link = ('<a style="color:#2563eb" href="'+html.escape(PUBLIC_BASE_URL,quote=True)+'">打开班务系统</a>') if PUBLIC_BASE_URL else ''
    return ('<!doctype html><html lang="zh-CN"><body style="margin:0;background:#f1f5fc;color:#203047;font-family:Arial,sans-serif">'
            '<div style="max-width:640px;margin:auto;padding:24px 16px"><div style="padding:22px;background:#1d4fa8;color:white;border-radius:12px 12px 0 0">'
            '<div style="font-size:13px">'+BRAND+'</div><h1 style="font-size:22px;margin:12px 0 0">'+html.escape(parts['title'])+'</h1></div>'
            '<div style="padding:24px;background:white;line-height:1.85;overflow-wrap:anywhere;white-space:pre-wrap">'+content+'</div>'
            '<div style="padding:18px;background:#e6eefb;border-radius:0 0 12px 12px;font-size:12px;line-height:1.8">'+link+
            '<br>发送时间：'+parts['sent']+'（北京时间）<br>系统自动提醒，请勿直接回复；如有疑问请联系发布人。<br>附件链接有效期 7 天，请勿转发包含个人资料的下载链接。</div></div></body></html>')
