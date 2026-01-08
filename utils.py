import hashlib
import re
from urllib.parse import urlparse


def get_domain(url: str) -> str:
    d = urlparse(url).netloc.lower()
    return d.replace("www.", "")


def hash_url(url: str) -> str:
    return hashlib.sha1(url.encode("utf-8", errors="ignore")).hexdigest()


_ws = re.compile(r"\s+")

def hash_text(text: str) -> str:
    t = (text or "").replace("\r\n", "\n").replace("\r", "\n")
    t = _ws.sub(" ", t).strip()
    return hashlib.sha256(t.encode("utf-8", errors="ignore")).hexdigest()
