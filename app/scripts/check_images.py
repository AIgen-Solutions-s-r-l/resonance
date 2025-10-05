#!/usr/bin/env python3
"""
Robust logo URL checker with proxy support (hard-coded Oculus round-robin, static/env, NST)
and a --no-proxy override.

Features:
- Persistent Session with retries/backoff
- Range-GET sniff → (if 206 image/* and tiny) full GET retry → HEAD → full GET
- Magic-bytes + optional Pillow verify
- Clean HTML detection (no ascii-ratio false positives)
- Explicit SVG handling (even when served as text/xml)
- AVIF/ISOBMFF recognition (+ allow image/avif, image/heic)
- Content-Disposition / extension traps
- Strict mode (--strict)
- Proxies:
  * Hard-coded Oculus proxies (default if none provided)
  * --proxy <url>
  * --proxies-file proxies.txt (round-robin)
  * --use-env-proxy (HTTP(S)_PROXY)
  * --nst (NST_PROXY_API_KEY) with optional --nst-country/--nst-keyword
  * --no-proxy to force direct connections (skips any proxy usage)
- Logging and jittered sleep between requests (--sleep)
- Fallback: on network-ish failure with proxy, retry once w/o proxy
"""
import argparse, json, sys, time, re, csv, threading, random, logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Tuple, Optional, Dict, Any, List
from urllib.parse import urlparse

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

try:
    from PIL import Image
    from io import BytesIO
    HAS_PIL = True
except Exception:
    HAS_PIL = False

DEFAULT_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

ALLOWED_IMAGE_CT = {
    "image/png",
    "image/jpeg",
    "image/gif",
    "image/webp",
    "image/svg+xml",
    "image/x-icon",
    "image/vnd.microsoft.icon",
    "image/avif",
    "image/heic",
}
TEXTY_CT = {"application/json", "application/xml"}
TEXTY_CT_PREFIX = ("text/",)

NON_IMAGE_EXTS = {".txt", ".html", ".htm", ".pdf", ".csv", ".json", ".xml"}
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".ico", ".avif", ".heic"}

MIN_IMAGE_BYTES = 64
SNIFF_BYTES = 4096

# ----------------------------- Proxy Providers -----------------------------

HARD_CODED_PROXIES = [
    "http://oc-cdaa040e0fa99abd955a1706475e5054e865e483d0bde1499da4225d10aba13b-country-US-session-12a7f:vrxywb8jk36k@proxy.oculus-proxy.com:31111",
    "http://oc-cdaa040e0fa99abd955a1706475e5054e865e483d0bde1499da4225d10aba13b-country-US-session-ab38a:vrxywb8jk36k@proxy.oculus-proxy.com:31111",
    "http://oc-cdaa040e0fa99abd955a1706475e5054e865e483d0bde1499da4225d10aba13b-country-US-session-8a8d0:vrxywb8jk36k@proxy.oculus-proxy.com:31111",
    "http://oc-cdaa040e0fa99abd955a1706475e5054e865e483d0bde1499da4225d10aba13b-country-US-session-69515:vrxywb8jk36k@proxy.oculus-proxy.com:31111",
    "http://oc-cdaa040e0fa99abd955a1706475e5054e865e483d0bde1499da4225d10aba13b-country-US-session-2254f:vrxywb8jk36k@proxy.oculus-proxy.com:31111",
    "http://oc-cdaa040e0fa99abd955a1706475e5054e865e483d0bde1499da4225d10aba13b-country-US-session-ef6d1:vrxywb8jk36k@proxy.oculus-proxy.com:31111",
    "http://oc-cdaa040e0fa99abd955a1706475e5054e865e483d0bde1499da4225d10aba13b-country-US-session-1fd56:vrxywb8jk36k@proxy.oculus-proxy.com:31111",
    "http://oc-cdaa040e0fa99abd955a1706475e5054e865e483d0bde1499da4225d10aba13b-country-US-session-218a3:vrxywb8jk36k@proxy.oculus-proxy.com:31111",
    "http://oc-cdaa040e0fa99abd955a1706475e5054e865e483d0bde1499da4225d10aba13b-country-US-session-f5ff0:vrxywb8jk36k@proxy.oculus-proxy.com:31111",
    "http://oc-cdaa040e0fa99abd955a1706475e5054e865e483d0bde1499da4225d10aba13b-country-US-session-5a4ef:vrxywb8jk36k@proxy.oculus-proxy.com:31111",
    "http://oc-cdaa040e0fa99abd955a1706475e5054e865e483d0bde1499da4225d10aba13b-country-US-session-bf2b4:vrxywb8jk36k@proxy.oculus-proxy.com:31111",
    "http://oc-cdaa040e0fa99abd955a1706475e5054e865e483d0bde1499da4225d10aba13b-country-US-session-9e4ff:vrxywb8jk36k@proxy.oculus-proxy.com:31111",
    "http://oc-cdaa040e0fa99abd955a1706475e5054e865e483d0bde1499da4225d10aba13b-country-US-session-9c612:vrxywb8jk36k@proxy.oculus-proxy.com:31111",
    "http://oc-cdaa040e0fa99abd955a1706475e5054e865e483d0bde1499da4225d10aba13b-country-US-session-e6fd4:vrxywb8jk36k@proxy.oculus-proxy.com:31111",
    "http://oc-cdaa040e0fa99abd955a1706475e5054e865e483d0bde1499da4225d10aba13b-country-US-session-64853:vrxywb8jk36k@proxy.oculus-proxy.com:31111",
    "http://oc-cdaa040e0fa99abd955a1706475e5054e865e483d0bde1499da4225d10aba13b-country-US-session-bcf6a:vrxywb8jk36k@proxy.oculus-proxy.com:31111",
    "http://oc-cdaa040e0fa99abd955a1706475e5054e865e483d0bde1499da4225d10aba13b-country-US-session-c57b2:vrxywb8jk36k@proxy.oculus-proxy.com:31111",
    "http://oc-cdaa040e0fa99abd955a1706475e5054e865e483d0bde1499da4225d10aba13b-country-US-session-9372f:vrxywb8jk36k@proxy.oculus-proxy.com:31111",
    "http://oc-cdaa040e0fa99abd955a1706475e5054e865e483d0bde1499da4225d10aba13b-country-US-session-d0699:vrxywb8jk36k@proxy.oculus-proxy.com:31111",
    "http://oc-cdaa040e0fa99abd955a1706475e5054e865e483d0bde1499da4225d10aba13b-country-US-session-319d0:vrxywb8jk36k@proxy.oculus-proxy.com:31111",
    "http://oc-cdaa040e0fa99abd955a1706475e5054e865e483d0bde1499da4225d10aba13b-country-US-session-11af4:vrxywb8jk36k@proxy.oculus-proxy.com:31111",
    "http://oc-cdaa040e0fa99abd955a1706475e5054e865e483d0bde1499da4225d10aba13b-country-US-session-7cd68:vrxywb8jk36k@proxy.oculus-proxy.com:31111",
    "http://oc-cdaa040e0fa99abd955a1706475e5054e865e483d0bde1499da4225d10aba13b-country-US-session-71004:vrxywb8jk36k@proxy.oculus-proxy.com:31111",
    "http://oc-cdaa040e0fa99abd955a1706475e5054e865e483d0bde1499da4225d10aba13b-country-US-session-e7d66:vrxywb8jk36k@proxy.oculus-proxy.com:31111",
    "http://oc-cdaa040e0fa99abd955a1706475e5054e865e483d0bde1499da4225d10aba13b-country-US-session-105a0:vrxywb8jk36k@proxy.oculus-proxy.com:31111",
    "http://oc-cdaa040e0fa99abd955a1706475e5054e865e483d0bde1499da4225d10aba13b-country-US-session-91338:vrxywb8jk36k@proxy.oculus-proxy.com:31111",
    "http://oc-cdaa040e0fa99abd955a1706475e5054e865e483d0bde1499da4225d10aba13b-country-US-session-2f858:vrxywb8jk36k@proxy.oculus-proxy.com:31111",
    "http://oc-cdaa040e0fa99abd955a1706475e5054e865e483d0bde1499da4225d10aba13b-country-US-session-ca1eb:vrxywb8jk36k@proxy.oculus-proxy.com:31111",
    "http://oc-cdaa040e0fa99abd955a1706475e5054e865e483d0bde1499da4225d10aba13b-country-US-session-4ea51:vrxywb8jk36k@proxy.oculus-proxy.com:31111",
    "http://oc-cdaa040e0fa99abd955a1706475e5054e865e483d0bde1499da4225d10aba13b-country-US-session-79ea1:vrxywb8jk36k@proxy.oculus-proxy.com:31111",
    "http://oc-cdaa040e0fa99abd955a1706475e5054e865e483d0bde1499da4225d10aba13b-country-US-session-2c7bc:vrxywb8jk36k@proxy.oculus-proxy.com:31111",
    "http://oc-cdaa040e0fa99abd955a1706475e5054e865e483d0bde1499da4225d10aba13b-country-US-session-c34ca:vrxywb8jk36k@proxy.oculus-proxy.com:31111",
    "http://oc-cdaa040e0fa99abd955a1706475e5054e865e483d0bde1499da4225d10aba13b-country-US-session-f48e4:vrxywb8jk36k@proxy.oculus-proxy.com:31111",
    "http://oc-cdaa040e0fa99abd955a1706475e5054e865e483d0bde1499da4225d10aba13b-country-US-session-76f66:vrxywb8jk36k@proxy.oculus-proxy.com:31111",
    "http://oc-cdaa040e0fa99abd955a1706475e5054e865e483d0bde1499da4225d10aba13b-country-US-session-93cf5:vrxywb8jk36k@proxy.oculus-proxy.com:31111",
    "http://oc-cdaa040e0fa99abd955a1706475e5054e865e483d0bde1499da4225d10aba13b-country-US-session-99175:vrxywb8jk36k@proxy.oculus-proxy.com:31111",
    "http://oc-cdaa040e0fa99abd955a1706475e5054e865e483d0bde1499da4225d10aba13b-country-US-session-e834e:vrxywb8jk36k@proxy.oculus-proxy.com:31111",
    "http://oc-cdaa040e0fa99abd955a1706475e5054e865e483d0bde1499da4225d10aba13b-country-US-session-b4299:vrxywb8jk36k@proxy.oculus-proxy.com:31111",
    "http://oc-cdaa040e0fa99abd955a1706475e5054e865e483d0bde1499da4225d10aba13b-country-US-session-1aa71:vrxywb8jk36k@proxy.oculus-proxy.com:31111",
    "http://oc-cdaa040e0fa99abd955a1706475e5054e865e483d0bde1499da4225d10aba13b-country-US-session-afa3a:vrxywb8jk36k@proxy.oculus-proxy.com:31111",
    "http://oc-cdaa040e0fa99abd955a1706475e5054e865e483d0bde1499da4225d10aba13b-country-US-session-633b3:vrxywb8jk36k@proxy.oculus-proxy.com:31111",
    "http://oc-cdaa040e0fa99abd955a1706475e5054e865e483d0bde1499da4225d10aba13b-country-US-session-5f805:vrxywb8jk36k@proxy.oculus-proxy.com:31111",
    "http://oc-cdaa040e0fa99abd955a1706475e5054e865e483d0bde1499da4225d10aba13b-country-US-session-47b7b:vrxywb8jk36k@proxy.oculus-proxy.com:31111",
    "http://oc-cdaa040e0fa99abd955a1706475e5054e865e483d0bde1499da4225d10aba13b-country-US-session-90150:vrxywb8jk36k@proxy.oculus-proxy.com:31111",
    "http://oc-cdaa040e0fa99abd955a1706475e5054e865e483d0bde1499da4225d10aba13b-country-US-session-679e3:vrxywb8jk36k@proxy.oculus-proxy.com:31111",
    "http://oc-cdaa040e0fa99abd955a1706475e5054e865e483d0bde1499da4225d10aba13b-country-US-session-e55f0:vrxywb8jk36k@proxy.oculus-proxy.com:31111",
    "http://oc-cdaa040e0fa99abd955a1706475e5054e865e483d0bde1499da4225d10aba13b-country-US-session-ccec6:vrxywb8jk36k@proxy.oculus-proxy.com:31111",
    "http://oc-cdaa040e0fa99abd955a1706475e5054e865e483d0bde1499da4225d10aba13b-country-US-session-a3153:vrxywb8jk36k@proxy.oculus-proxy.com:31111",
    "http://oc-cdaa040e0fa99abd955a1706475e5054e865e483d0bde1499da4225d10aba13b-country-US-session-47bd5:vrxywb8jk36k@proxy.oculus-proxy.com:31111",
    "http://oc-cdaa040e0fa99abd955a1706475e5054e865e483d0bde1499da4225d10aba13b-country-US-session-f9684:vrxywb8jk36k@proxy.oculus-proxy.com:31111",
    "http://oc-cdaa040e0fa99abd955a1706475e5054e865e483d0bde1499da4225d10aba13b-country-US-session-6faf0:vrxywb8jk36k@proxy.oculus-proxy.com:31111",
    "http://oc-cdaa040e0fa99abd955a1706475e5054e865e483d0bde1499da4225d10aba13b-country-US-session-72947:vrxywb8jk36k@proxy.oculus-proxy.com:31111",
    "http://oc-cdaa040e0fa99abd955a1706475e5054e865e483d0bde1499da4225d10aba13b-country-US-session-d44b6:vrxywb8jk36k@proxy.oculus-proxy.com:31111",
    "http://oc-cdaa040e0fa99abd955a1706475e5054e865e483d0bde1499da4225d10aba13b-country-US-session-6e26e:vrxywb8jk36k@proxy.oculus-proxy.com:31111",
    "http://oc-cdaa040e0fa99abd955a1706475e5054e865e483d0bde1499da4225d10aba13b-country-US-session-8f188:vrxywb8jk36k@proxy.oculus-proxy.com:31111",
    "http://oc-cdaa040e0fa99abd955a1706475e5054e865e483d0bde1499da4225d10aba13b-country-US-session-5cedc:vrxywb8jk36k@proxy.oculus-proxy.com:31111",
    "http://oc-cdaa040e0fa99abd955a1706475e5054e865e483d0bde1499da4225d10aba13b-country-US-session-f33e5:vrxywb8jk36k@proxy.oculus-proxy.com:31111",
    "http://oc-cdaa040e0fa99abd955a1706475e5054e865e483d0bde1499da4225d10aba13b-country-US-session-1d113:vrxywb8jk36k@proxy.oculus-proxy.com:31111",
    "http://oc-cdaa040e0fa99abd955a1706475e5054e865e483d0bde1499da4225d10aba13b-country-US-session-e605c:vrxywb8jk36k@proxy.oculus-proxy.com:31111",
    "http://oc-cdaa040e0fa99abd955a1706475e5054e865e483d0bde1499da4225d10aba13b-country-US-session-4a384:vrxywb8jk36k@proxy.oculus-proxy.com:31111",
    "http://oc-cdaa040e0fa99abd955a1706475e5054e865e483d0bde1499da4225d10aba13b-country-US-session-69dc6:vrxywb8jk36k@proxy.oculus-proxy.com:31111",
    "http://oc-cdaa040e0fa99abd955a1706475e5054e865e483d0bde1499da4225d10aba13b-country-US-session-2c9de:vrxywb8jk36k@proxy.oculus-proxy.com:31111",
    "http://oc-cdaa040e0fa99abd955a1706475e5054e865e483d0bde1499da4225d10aba13b-country-US-session-d67e6:vrxywb8jk36k@proxy.oculus-proxy.com:31111",
    "http://oc-cdaa040e0fa99abd955a1706475e5054e865e483d0bde1499da4225d10aba13b-country-US-session-d80b2:vrxywb8jk36k@proxy.oculus-proxy.com:31111",
    "http://oc-cdaa040e0fa99abd955a1706475e5054e865e483d0bde1499da4225d10aba13b-country-US-session-9d284:vrxywb8jk36k@proxy.oculus-proxy.com:31111",
]


class ProxyProvider:
    def get(self) -> Optional[str]:
        return None

class StaticProxyProvider(ProxyProvider):
    def __init__(self, proxy: Optional[str]):
        self.proxy = proxy
    def get(self) -> Optional[str]:
        return self.proxy

class RoundRobinProxyProvider(ProxyProvider):
    def __init__(self, proxies: List[str]):
        self.proxies = [p.strip() for p in proxies if p.strip()]
        self._i = 0
        self._lock = threading.Lock()
    def get(self) -> Optional[str]:
        if not self.proxies:
            return None
        with self._lock:
            p = self.proxies[self._i % len(self.proxies)]
            self._i += 1
            return p

class EnvProxyProvider(ProxyProvider):
    def __init__(self):
        import os
        self.http = os.environ.get("HTTP_PROXY") or os.environ.get("http_proxy")
        self.https = os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy")
    def get(self) -> Optional[str]:
        return self.https or self.http

class NstProxyProvider(ProxyProvider):
    def __init__(self, api_key: Optional[str]=None, country: Optional[str]=None, keyword: Optional[str]=None):
        import os
        self.api_key = api_key or os.getenv("NST_PROXY_API_KEY", "")
        self.country = country
        self.keyword = keyword
        self._session = requests.Session()
        self._session.headers.update({"User-Agent": DEFAULT_UA})
        self._lock = threading.Lock()

    def _choose_channel(self) -> Optional[Dict[str, Any]]:
        r = self._session.get(
            "https://api.nstproxy.com/api/v1/api/channels",
            params={"page": 1, "pageSize": 50, "status": 1, "token": self.api_key},
            timeout=12,
        )
        r.raise_for_status()
        data = r.json()
        if data.get("code") != 200 or data.get("err"):
            return None
        channels = data.get("data", {}).get("data", []) or data.get("data", [])
        if self.country:
            channels = [c for c in channels if str(c.get("country") or "").lower() == self.country.lower()]
        if self.keyword:
            kw = self.keyword.lower()
            channels = [c for c in channels if kw in str(c.get("name","")).lower()]
        if not channels:
            return None
        return random.choice(channels)

    def get(self) -> Optional[str]:
        if not self.api_key:
            return None
        with self._lock:
            try:
                ch = self._choose_channel()
                if not ch:
                    return None
                params = {
                    "channelId": ch.get("channelId") or ch.get("channel_id"),
                    "country": ch.get("country"),
                    "protocol": "http",
                    "sessionDuration": 5400,
                    "count": 1,
                    "token": self.api_key,
                }
                r = self._session.get("https://api.nstproxy.com/api/v1/api/proxies", params=params, timeout=12)
                r.raise_for_status()
                data = r.json()
                if data.get("code") != 200 or data.get("err"):
                    return None
                proxies = (data.get("data") or {}).get("proxies") or []
                if not proxies:
                    return None
                return str(proxies[0])
            except Exception:
                return None

def build_session(timeout: float, proxy_provider: ProxyProvider) -> requests.Session:
    s = requests.Session()
    retry = Retry(
        total=3,
        read=3,
        connect=3,
        status=3,
        backoff_factor=0.6,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset(["HEAD", "GET"]),
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry, pool_connections=200, pool_maxsize=200)
    s.mount("http://", adapter)
    s.mount("https://", adapter)
    s.headers.update({
        "User-Agent": DEFAULT_UA,
        "Accept": "*/*",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
    })
    s.request_timeout = timeout
    s.trust_env = False  # we set proxies ourselves
    p = proxy_provider.get()
    if p:
        s.proxies.update({"http": p, "https": p})
    return s

# -------------------------- Content detection utils -------------------------

def filename_ext_from_disposition(disposition: Optional[str]) -> Optional[str]:
    if not disposition:
        return None
    m = re.search(r'filename\*\s*=\s*(?:[^\']+\'[^\']*\'|)([^;]+)', disposition, flags=re.IGNORECASE)
    if not m:
        m = re.search(r'filename\s*=\s*"([^"]+)"', disposition, flags=re.IGNORECASE)
    if not m:
        m = re.search(r'filename\s*=\s*([^;]+)', disposition, flags=re.IGNORECASE)
    if not m:
        return None
    fname = m.group(1).strip().strip('"')
    fname = fname.split("?")[0]
    if "." in fname:
        return "." + fname.rsplit(".", 1)[-1].lower()
    return None

def path_ext(url: str) -> Optional[str]:
    try:
        p = urlparse(url).path
        if "." in p.rsplit("/", 1)[-1]:
            return "." + p.rsplit(".", 1)[-1].lower()
    except Exception:
        pass
    return None

def magic_bytes_look_like_image(sniff: bytes) -> bool:
    s2k = sniff[:2048]
    # PNG
    if s2k.startswith(b"\x89PNG\r\n\x1a\n"):
        return True
    # JPEG
    if s2k.startswith(b"\xff\xd8\xff"):
        return True
    # GIF
    if s2k.startswith(b"GIF87a") or s2k.startswith(b"GIF89a"):
        return True
    # WebP (RIFF + 'WEBP' in header)
    if s2k.startswith(b"RIFF") and b"WEBP" in s2k[:16]:
        return True
    # SVG textual
    if b"<svg" in s2k.lower():
        return True
    # ICO
    if s2k.startswith(b"\x00\x00\x01\x00"):
        return True
    # AVIF/ISOBMFF (ftyp brand avif/avis/heic/mif1)
    if len(s2k) >= 16 and s2k[4:8] == b"ftyp" and any(b in s2k[8:16] for b in (b"avif", b"avis", b"heic", b"mif1")):
        return True
    return False

def looks_like_html(sniff: bytes) -> bool:
    # Only treat as HTML if real HTML tags are present
    s = sniff[:2048].lstrip().lower()
    if s.startswith(b"<!doctype html") or s.startswith(b"<html"):
        return True
    if b"<html" in s or b"<head" in s or b"<body" in s:
        return True
    return False

def pillow_verifies(sniff: bytes) -> bool:
    if not HAS_PIL:
        return False
    try:
        with Image.open(BytesIO(sniff)) as im:
            im.verify()
        return True
    except Exception:
        return False

# -------------------------------- Fetch logic -------------------------------

def fetch_sniff(session: requests.Session, url: str, timeout: float) -> Tuple[requests.Response, bytes]:
    # 1) Range GET
    headers = {"Range": f"bytes=0-{SNIFF_BYTES-1}"}
    try:
        r = session.get(url, headers=headers, allow_redirects=True, timeout=timeout, stream=False)
        sniff = r.content[:SNIFF_BYTES] if r.status_code < 400 else b""
        ct = (r.headers.get("Content-Type","").lower().split(";")[0].strip())
        # If 206 and image/* but sniff tiny → retry full GET without Range
        if r.status_code == 206 and ct.startswith("image/") and len(sniff) < 32:
            r2 = session.get(url, allow_redirects=True, timeout=timeout, stream=False)
            return r2, r2.content[:SNIFF_BYTES] if r2.status_code < 400 else b""
        if sniff or r.status_code == 206 or r.headers.get("Content-Type"):
            return r, sniff
    except requests.RequestException:
        pass

    # 2) HEAD fallback
    try:
        _ = session.head(url, allow_redirects=True, timeout=timeout)
    except requests.RequestException:
        pass

    # 3) Full GET
    g = session.get(url, allow_redirects=True, timeout=timeout, stream=False)
    sniff = g.content[:SNIFF_BYTES] if g.status_code < 400 else b""
    return g, sniff

def strict_image_decision(content_type: Optional[str], sniff: bytes, content_length: Optional[int], strict: bool) -> Tuple[bool, str]:
    ct = (content_type or "").lower().split(";")[0].strip()

    # 1) If bytes look like an image (or Pillow says OK) → accept
    if magic_bytes_look_like_image(sniff) or pillow_verifies(sniff):
        return True, "OK image bytes"

    # 2) If CT says image/* and we have positive length but no bytes yet → maybe accept
    if ct.startswith("image/"):
        # accept SVG even if served as text-like bytes (already handled above if <svg is present)
        if b"<svg" in sniff[:2048].lower():
            return True, "SVG text image"
        if (not sniff) and content_length and content_length > 0 and not strict:
            return True, "Image CT + positive CL (lenient)"

    # 3) Only now treat clear HTML as not image
    if looks_like_html(sniff):
        return False, "HTML page (login/error)"

    # 4) Text-like CTs → reject unless it's clearly SVG
    if ct.startswith(TEXTY_CT_PREFIX) or ct in TEXTY_CT:
        if b"<svg" in sniff[:2048].lower():
            return True, "SVG as XML"
        return False, f"CT {ct}; not image"

    # 5) Missing/unknown CT
    if not ct or ct == "application/octet-stream":
        if len(sniff) >= MIN_IMAGE_BYTES:
            # We already checked magic/Pillow above; treat as non-image now
            return False, "Unknown CT; bytes not image"
        if content_length and content_length > 0 and not strict:
            return True, "Unknown CT + positive CL (lenient)"
        return False, f"CT {ct or 'missing'}; bytes not image"

    # 6) Known image CT but bytes didn’t prove it
    if ct in ALLOWED_IMAGE_CT:
        if not sniff and content_length and content_length > 0 and not strict:
            return True, "Image CT + positive CL (lenient)"
        return False, "Image CT but bytes don’t look like image"

    # 7) Unknown CT
    return False, f"Unknown CT {ct}; bytes not image"

def check_url(session: requests.Session, url: str, timeout: float, strict: bool) -> Tuple[bool, str, Dict[str, str]]:
    meta = {
        "final_url": "",
        "status": "",
        "ct": "",
        "cl": "",
        "disp": "",
        "path_ext": path_ext(url) or "",
        "proxy": session.proxies.get("https") or session.proxies.get("http") or ""
    }
    try:
        r, sniff = fetch_sniff(session, url, timeout)
        meta["final_url"] = r.url
        meta["status"]   = str(r.status_code)
        meta["ct"]       = r.headers.get("Content-Type","")
        meta["cl"]       = r.headers.get("Content-Length","")
        meta["disp"]     = r.headers.get("Content-Disposition","")

        if r.status_code >= 400:
            return False, f"HTTP {r.status_code}", meta

        disp_ext = filename_ext_from_disposition(meta["disp"])
        if disp_ext and disp_ext in NON_IMAGE_EXTS:
            return False, f"Content-Disposition ext {disp_ext}", meta

        pext = path_ext(meta["final_url"])
        if pext and pext in NON_IMAGE_EXTS:
            return False, f"URL path ext {pext}", meta

        cl_int = None
        try:
            cl_int = int(meta["cl"]) if meta["cl"] else None
        except Exception:
            cl_int = None

        # Workday assets/logo: reject if text CT and not SVG bytes
        fu = (meta["final_url"] or "").lower()
        ct_low = (meta["ct"] or "").lower().split(";")[0].strip()
        if "myworkdayjobs.com" in fu and "/assets/logo" in fu:
            if b"<svg" not in sniff[:2048].lower() and (ct_low.startswith("text/") or ct_low in TEXTY_CT):
                return False, "Workday assets/logo returned text (not an image)", meta

        ok, reason = strict_image_decision(ct_low, sniff, cl_int, strict)
        if ok and sniff and len(sniff) < MIN_IMAGE_BYTES and strict and not magic_bytes_look_like_image(sniff):
            return False, "Too few bytes for image (strict)", meta

        return ok, reason, meta

    except requests.TooManyRedirects:
        return False, "Too many redirects", meta
    except requests.Timeout:
        return False, "Timeout", meta
    except requests.RequestException as e:
        return False, f"Exception: {type(e).__name__}", meta

def process_item(session: requests.Session, item: dict, timeout: float, strict: bool) -> Tuple[str, bool, str, str, Dict[str,str]]:
    name = str(item.get("company_name", "")).strip()
    url = str(item.get("logo", "")).strip()
    if not url:
        return name, False, url, "Empty URL", {}
    ok, reason, meta = check_url(session, url, timeout=timeout, strict=strict)
    return name, ok, url, reason, meta

# ----------------------------------- CLI -----------------------------------

def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    logging.info("Starting logo check")

    ap = argparse.ArgumentParser()
    ap.add_argument("--json", required=True, help="Input JSON list of {company_name, logo}")
    ap.add_argument("--out", default="bad_logos.txt")
    ap.add_argument("--bad-csv", default="")
    ap.add_argument("--workers", type=int, default=20)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--timeout", type=float, default=10.0)
    ap.add_argument("--strict", action="store_true", help="Disallow image CT without confirming image bytes")

    # Proxy options
    ap.add_argument("--proxy", default="", help="Single proxy URL (e.g., http://user:pass@host:port)")
    ap.add_argument("--proxies-file", default="", help="File with one proxy URL per line (round-robin)")
    ap.add_argument("--use-env-proxy", action="store_true", help="Use HTTP(S)_PROXY environment variables")
    ap.add_argument("--nst", action="store_true", help="Use NST proxy (requires NST_PROXY_API_KEY env)")
    ap.add_argument("--nst-country", default="", help="NST channel country filter (optional)")
    ap.add_argument("--nst-keyword", default="", help="NST channel name keyword filter (optional)")
    ap.add_argument("--sleep", type=float, default=0.25, help="Sleep seconds between requests (per task)")
    ap.add_argument("--no-proxy", dest="no_proxy", action="store_true", help="Force direct connections, skipping any proxy usage")
    args = ap.parse_args()

    src = Path(args.json)
    if not src.exists():
        print(f"Input JSON not found: {src}", file=sys.stderr)
        sys.exit(1)

    items = json.loads(src.read_text(encoding="utf-8"))
    if not isinstance(items, list):
        print("JSON root must be a list of objects.", file=sys.stderr)
        sys.exit(1)
    if args.limit > 0:
        items = items[:args.limit]

    # Build proxy provider preference: no-proxy > NST > file > explicit > env > hard-coded > none
    provider: ProxyProvider
    if args.no_proxy:
        logging.info("⚠️  --no-proxy set: using direct connections only")
        provider = StaticProxyProvider(None)
    elif args.nst:
        logging.info("Using NST proxy provider")
        provider = NstProxyProvider(country=(args.nst_country or None), keyword=(args.nst_keyword or None))
    elif args.proxies_file:
        logging.info(f"Using proxies from file: {args.proxies_file}")
        lines = [l.strip() for l in Path(args.proxies_file).read_text(encoding="utf-8").splitlines() if l.strip() and not l.strip().startswith("#")]
        provider = RoundRobinProxyProvider(lines)
    elif args.proxy:
        logging.info("Using single static proxy")
        provider = StaticProxyProvider(args.proxy.strip())
    elif args.use_env_proxy:
        logging.info("Using environment proxies")
        provider = EnvProxyProvider()
    else:
        if HARD_CODED_PROXIES:
            logging.info("Using hard-coded Oculus proxies (round-robin)")
            provider = RoundRobinProxyProvider(HARD_CODED_PROXIES)
        else:
            provider = StaticProxyProvider(None)

    def _worker(it):
        # jittered sleep between requests
        time.sleep(max(0.0, args.sleep) * (0.5 + random.random()))
        session = build_session(timeout=args.timeout, proxy_provider=provider)
        name, ok, url, reason, meta = process_item(session, it, timeout=args.timeout, strict=args.strict)
        logging.info(f"Checked: {url} | proxy={meta.get('proxy','')} | ok={ok} | reason={reason}")
        # fallback once without proxy on network failures (and only if not already --no-proxy)
        if (not ok) and (not args.no_proxy) and any(k in reason.lower() for k in ['timeout','redirect','exception','http 429','http 5','too many redirects']):
            logging.info("Retrying without proxy...")
            session2 = build_session(timeout=args.timeout, proxy_provider=StaticProxyProvider(None))
            name, ok2, url, reason2, meta2 = process_item(session2, it, timeout=args.timeout, strict=args.strict)
            logging.info(f"Fallback result: ok={ok2} | reason={reason2}")
            if ok2:
                return name, ok2, url, reason2, meta2
        return name, ok, url, reason, meta

    bad_names, bad_rows = [], []
    t0 = time.time()

    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futures = {ex.submit(_worker, it): it for it in items}
        for fut in as_completed(futures):
            name, ok, url, reason, meta = fut.result()
            if not ok:
                label = name or url or "(unknown)"
                bad_names.append(label)
                bad_rows.append((
                    name, url, reason,
                    meta.get("final_url",""),
                    meta.get("status",""),
                    meta.get("ct",""),
                    meta.get("cl",""),
                    meta.get("disp",""),
                    meta.get("path_ext",""),
                    meta.get("proxy",""),
                ))

    Path(args.out).write_text("\n".join(bad_names) + ("\n" if bad_names else ""), encoding="utf-8")
    if args.bad_csv:
        with open(args.bad_csv, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["company_name","url","reason","final_url","http_status","content_type","content_length","content_disposition","path_ext","proxy_used"])
            w.writerows(bad_rows)

    dt = time.time() - t0
    print(f"Checked {len(items)} items in {dt:.1f}s")
    print(f"Bad/non-image links: {len(bad_names)}")
    print(f"Wrote names: {Path(args.out).resolve()}")
    if args.bad_csv:
        print(f"Wrote details: {Path(args.bad_csv).resolve()}")

if __name__ == "__main__":
    main()
