"""HTML allowlist and local attachment references; never fetch remote URLs."""
import html
import re
from html.parser import HTMLParser
from urllib.parse import urlsplit, unquote
import nh3

TAGS = {"p", "br", "strong", "b", "em", "i", "u", "s", "h2", "h3", "ul", "ol", "li", "blockquote", "pre", "code", "a", "img", "hr"}
ATTRS = {"a": {"href", "title"}, "img": {"src", "alt", "title", "width", "height", "loading"}}

def _attribute(tag, key, value):
    if key == "src" and not re.fullmatch(r"/static/rich/[a-f0-9]{32}\.(?:jpg|png|webp)", value):
        return None
    if key == "href":
        if value.startswith("/static/rich/"):
            return value if re.fullmatch(r"/static/rich/[a-f0-9]{32}\.[a-z0-9]+", value) else None
        if not value.startswith(("https://", "http://", "mailto:")):
            return None
    return value

def clean_html(value):
    value = value or ""
    if not value.strip():
        return ""
    if not re.search(r"</?[a-zA-Z][^>]*>", value):
        value = "<p>" + html.escape(value).replace("\n", "<br>") + "</p>"
    return nh3.clean(value, tags=TAGS, attributes=ATTRS, attribute_filter=_attribute,
                     url_schemes={"https", "http", "mailto"}, link_rel="noopener noreferrer")

class _Content(HTMLParser):
    def __init__(self):
        super().__init__()
        self.text, self.media = [], []
    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag in {"p", "br", "li", "h2", "h3"}:
            self.text.append("\n")
        url = attrs.get("src" if tag == "img" else "href", "")
        if tag in {"img", "a"} and re.fullmatch(r"/static/rich/[a-f0-9]{32}\.[a-z0-9]+", url):
            self.media.append({"url": url, "name": attrs.get("alt") or attrs.get("title") or "附件", "image": tag == "img"})
    def handle_data(self, data):
        self.text.append(data)

def content_parts(value):
    parser = _Content()
    parser.feed(clean_html(value))
    unique = {item["url"]: item for item in parser.media}
    return "".join(parser.text).strip(), list(unique.values())

def plain_text(value):
    return content_parts(value)[0]
