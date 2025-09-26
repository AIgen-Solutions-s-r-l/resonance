#!/usr/bin/env python3
# check_images.py  (async, no hangs)
import argparse, asyncio, csv, re, sys
from typing import Optional, Dict

import httpx

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

RANGE_HEADER = {"Range": "bytes=0-4095"}
RANGE_LIMIT = 4096
PLAIN_LIMIT = 8192
STATUS_RETRY = {429, 500, 502, 503, 504}

def sniff_image_magic(data: bytes) -> Optional[str]:
    if not data: return None
    if data.startswith(b"\xff\xd8\xff"): return "image/jpeg"
    if data.startswith(b"\x89PNG\r\n\x1a\n"): return "image/png"
    if data.startswith(b"GIF87a") or data.startswith(b"GIF89a"): return "image/gif"
    if data.startswith(b"RIFF") and b"WEBP" in data[:16]: return "image/webp"
    if data.startswith(b"BM"): return "image/bmp"
    if data.startswith(b"II*\x00") or data.startswith(b"MM\x00*".encode()): return "image/tiff"
    if len(data) >= 12 and data[4:8] == b"ftyp":
        brand = data[8:12]
        if brand in (b"avif", b"avis"): return "image/avif"
        if brand in (b"mif1", b"msf1", b"heic", b"heix", b"hevc", b"hevx", b"heif", b"heim", b"heis", b"hevm", b"hevs"):
            return "image/heic"
    head = data.lstrip()
    if head.startswith(b"<?xml") or head.startswith(b"<svg"):
        if re.search(br"<svg(\s|>)", head[:4096], flags=re.I):
            return "image/svg+xml"
    return None

def is_image_ct(ct: Optional[str]) -> bool:
    return bool(ct) and ct.split(";")[0].strip().lower().startswith("image/")

async def read_up_to(resp: httpx.Response, limit: int) -> bytes:
    data = b""
    async for chunk in resp.aiter_bytes():
        if not chunk: break
        take = min(len(chunk), max(0, limit - len(data)))
        data += chunk[:take]
        if len(data) >= limit: break
    return data

async def classify_once(url: str, client: httpx.AsyncClient, op_timeout: float) -> Dict[str, str]:
    """One attempt (no retries)."""
    result = {"url": url, "ok": "false", "status_code": "", "mime": "", "reason": ""}

    # 1) HEAD
    try:
        r = await client.request("HEAD", url, follow_redirects=True, timeout=op_timeout)
        result["status_code"] = str(r.status_code)
        ct = r.headers.get("content-type", "")
        if r.is_success and is_image_ct(ct):
            result.update(ok="true", mime=ct.split(";")[0].strip().lower(), reason="HEAD: Content-Type is image/*")
            return result
    except httpx.HTTPError:
        pass

    # 2) Range GET
    try:
        async with client.stream("GET", url, headers=RANGE_HEADER, follow_redirects=True, timeout=op_timeout) as r2:
            result["status_code"] = str(r2.status_code)
            if r2.status_code in (400,401,403,405,406,409,412,416) or not r2.is_success:
                # 3) Plain GET
                async with client.stream("GET", url, follow_redirects=True, timeout=op_timeout) as r3:
                    result["status_code"] = str(r3.status_code)
                    if r3.is_success:
                        ctp = r3.headers.get("content-type", "")
                        if is_image_ct(ctp):
                            result.update(ok="true", mime=ctp.split(";")[0].strip().lower(), reason="Plain GET: Content-Type is image/*")
                            return result
                        data = await read_up_to(r3, PLAIN_LIMIT)
                        mime = sniff_image_magic(data)
                        if mime:
                            result.update(ok="true", mime=mime, reason="Plain GET: magic bytes")
                            return result
                        if data.lstrip().lower().startswith(b"<!doctype html") or b"<html" in data[:4096].lower():
                            result["reason"] = "Plain GET: looks like HTML, not an image"
                        else:
                            result["reason"] = "Plain GET: not recognized as image"
                    else:
                        result["reason"] = f"HTTP error {r3.status_code} after Range rejection"
                return result

            # Range path ok
            ctg = r2.headers.get("content-type", "")
            if r2.is_success and is_image_ct(ctg):
                result.update(ok="true", mime=ctg.split(";")[0].strip().lower(), reason="Range GET: Content-Type is image/*")
                return result
            data = await read_up_to(r2, RANGE_LIMIT)
            mime = sniff_image_magic(data)
            if mime:
                result.update(ok="true", mime=mime, reason="Range GET: magic bytes")
                return result
            if data.lstrip().lower().startswith(b"<!doctype html") or b"<html" in data[:4096].lower():
                result["reason"] = "Range GET: looks like HTML, not an image"
            else:
                result["reason"] = "Range GET: not recognized as image"
    except httpx.TimeoutException:
        result["reason"] = "Timeout"
    except httpx.HTTPError as e:
        result["reason"] = f"HTTP error: {e.__class__.__name__}"
    except Exception as e:
        result["reason"] = f"Unexpected: {e.__class__.__name__}"

    return result

async def classify_with_retries(url: str, client: httpx.AsyncClient, per_url_cap: float, op_timeout: float, retries: int, quiet: bool) -> Dict[str, str]:
    # Hard cap per URL — guarantees no hangs
    async def attempt_loop():
        last = None
        for i in range(retries + 1):
            res = await classify_once(url, client, op_timeout)
            last = res
            # Simple retry policy on transient statuses
            if res["reason"].startswith("HTTP error"):
                try:
                    code = int(res["reason"].split()[2])
                except Exception:
                    code = None
                if code in STATUS_RETRY and i < retries:
                    await asyncio.sleep(0.3 * (2 ** i))
                    continue
            break
        return last

    try:
        res = await asyncio.wait_for(attempt_loop(), timeout=per_url_cap)
    except asyncio.TimeoutError:
        res = {"url": url, "ok": "false", "status_code": "", "mime": "", "reason": "Timeout (per-URL cap reached)"}

    if not quiet:
        sys.stdout.write(f"[{res['ok']}] {res['status_code'] or '-'} {res['mime'] or '-'} :: {res['url']} ({res['reason']})\n")
        sys.stdout.flush()
    return res

def load_urls(path: str):
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            u = line.strip()
            if u and not u.startswith("#"):
                yield u

async def main_async(args):
    # Prefer AsyncHTTPTransport if available (httpx>=0.24)
    transport = None
    if hasattr(httpx, "AsyncHTTPTransport"):
        transport = httpx.AsyncHTTPTransport(retries=args.retries)
    limits = httpx.Limits(max_connections=args.workers, max_keepalive_connections=args.workers)
    timeout = httpx.Timeout(connect=args.timeout, read=args.timeout, write=args.timeout, pool=args.timeout)

    async with httpx.AsyncClient(
        headers={"User-Agent": USER_AGENT, "Accept": "*/*"},
        verify=not args.no_verify_ssl,
        http2=args.http2,
        limits=limits,
        timeout=timeout,
        trust_env=False,
        transport=transport,  # may be None; that’s fine
    ) as client:
        sem = asyncio.Semaphore(args.workers)
        urls = list(load_urls(args.input))

        async def bound(u):
            async with sem:
                return await classify_with_retries(u, client, args.per_url_cap, args.timeout, args.retries, args.quiet)

        results = await asyncio.gather(*(bound(u) for u in urls))

    with open(args.output, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["url", "ok", "status_code", "mime", "reason"])
        w.writeheader()
        w.writerows(results)

def main():
    ap = argparse.ArgumentParser(description="Check if URLs are downloadable images without saving files (async, hard per-URL cutoff).")
    ap.add_argument("input", help="Path to .txt file with one URL per line")
    ap.add_argument("-o", "--output", default="image_checks.csv", help="Output CSV (default: image_checks.csv)")
    ap.add_argument("-w", "--workers", type=int, default=32, help="Concurrent requests (default: 32)")
    ap.add_argument("-t", "--timeout", type=float, default=5.0, help="Per-operation timeout seconds (default: 5)")
    ap.add_argument("--per-url-cap", type=float, default=10.0, help="Hard cap per URL in seconds (default: 10)")
    ap.add_argument("--retries", type=int, default=1, help="Retries for transient 429/5xx (default: 1)")
    ap.add_argument("--no-verify-ssl", action="store_true", help="Disable SSL verification")
    ap.add_argument("--http2", action="store_true", help="Enable HTTP/2 (default off)")
    ap.add_argument("--quiet", action="store_true", help="Suppress per-URL logs (CSV only)")
    args = ap.parse_args()

    try:
        asyncio.run(main_async(args))
    except KeyboardInterrupt:
        print("\nInterrupted.", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
