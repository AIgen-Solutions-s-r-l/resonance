#!/usr/bin/env python3
import argparse, json, sys, time, re, csv
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Tuple, Optional

import requests

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
}

NON_IMAGE_EXTS = {".txt", ".html", ".htm", ".pdf", ".csv", ".json", ".xml"}

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

def magic_bytes_look_like_image(sniff: bytes) -> bool:
    if sniff.startswith(b"\x89PNG\r\n\x1a\n"):                 # PNG
        return True
    if sniff.startswith(b"\xff\xd8\xff"):                      # JPEG
        return True
    if sniff.startswith(b"GIF87a") or sniff.startswith(b"GIF89a"):  # GIF
        return True
    if sniff.startswith(b"RIFF") and b"WEBP" in sniff[:16]:    # WebP
        return True
    if b"<svg" in sniff[:2048].lower():                        # SVG tag
        return True
    return False

def looks_like_html_or_text(sniff: bytes) -> bool:
    s = sniff[:2048].lstrip().lower()
    if s.startswith(b"<!doctype html") or s.startswith(b"<html"):
        return True
    # heuristic: mostly printable ascii and contains many spaces/newlines → text-ish
    ascii_portion = sum(32 <= b <= 126 or b in (9,10,13) for b in s)
    return len(s) > 0 and ascii_portion / max(1, len(s)) > 0.95

def strict_image_decision(content_type: Optional[str], sniff: bytes, content_length: Optional[int]) -> Tuple[bool, str]:
    ct = (content_type or "").lower().split(";")[0].strip()

    # Fast path: clear HTML/text signature
    if looks_like_html_or_text(sniff):
        return False, "HTML/TEXT bytes"

    # Reject if CT clearly non-image and bytes don't prove otherwise
    if ct not in ALLOWED_IMAGE_CT:
        if magic_bytes_look_like_image(sniff):
            return True, "Magic-bytes image (mislabelled CT)"
        return False, f"CT {ct or 'missing'}; bytes not image"

    # Allowed CT: we still want matching magic bytes if possible
    if magic_bytes_look_like_image(sniff):
        return True, "OK image"

    # No magic yet; if we truly got no data but server claims image with length > 0, allow
    if not sniff and content_length and content_length > 0:
        return True, "Allowed CT + positive Content-Length (no sniff)"

    # Otherwise, treat as non-image
    return False, "Allowed CT but bytes not image"

def fetch_sniff(url: str, headers: dict, timeout: float, max_get_sniff: int = 4096) -> Tuple[requests.Response, bytes]:
    """
    Try streaming first; if we get 0 bytes, retry with non-stream GET to force a small body.
    """
    g = requests.get(url, allow_redirects=True, headers=headers, timeout=timeout, stream=True)
    try:
        if g.status_code >= 400:
            return g, b""
        sniff = b""
        for chunk in g.iter_content(chunk_size=1024):
            if not chunk:
                continue
            sniff += chunk
            if len(sniff) >= max_get_sniff:
                break
        if sniff:
            return g, sniff
    finally:
        g.close()

    # Retry non-stream (some CDNs delay chunking):
    g2 = requests.get(url, allow_redirects=True, headers=headers, timeout=timeout, stream=False)
    sniff2 = g2.content[:max_get_sniff] if g2.status_code < 400 else b""
    return g2, sniff2

def check_url(url: str, timeout: float = 10.0) -> Tuple[bool, str]:
    headers = {
        "User-Agent": DEFAULT_UA,
        "Accept": "*/*",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
    }
    try:
        r = requests.head(url, allow_redirects=True, headers=headers, timeout=timeout)
        if r.status_code >= 400:
            return False, f"HEAD {r.status_code}"

        g, sniff = fetch_sniff(url, headers, timeout, max_get_sniff=4096)
        if g.status_code >= 400:
            return False, f"GET {g.status_code}"

        disp = g.headers.get("Content-Disposition")
        ext = filename_ext_from_disposition(disp)
        ct = g.headers.get("Content-Type")
        cl = g.headers.get("Content-Length")
        cl_int = None
        try:
            cl_int = int(cl) if cl else None
        except Exception:
            cl_int = None

        # Reject explicit non-image downloads
        if ext and ext in NON_IMAGE_EXTS:
            return False, f"Content-Disposition ext {ext}"

        ok, reason = strict_image_decision(ct, sniff, cl_int)
        return ok, reason

    except requests.RequestException as e:
        return False, f"Exception: {type(e).__name__}"

def process_item(item: dict, timeout: float) -> Tuple[str, bool, str, str]:
    name = str(item.get("company_name", "")).strip()
    url = str(item.get("logo", "")).strip()
    if not url:
        return name, False, url, "Empty URL"
    ok, reason = check_url(url, timeout=timeout)
    return name, ok, url, reason

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", required=True)
    ap.add_argument("--out", default="bad_logos.txt")
    ap.add_argument("--bad-csv", default="")
    ap.add_argument("--workers", type=int, default=20)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--timeout", type=float, default=10.0)
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

    bad_names, bad_rows = [], []
    t0 = time.time()

    def _worker(it):
        return process_item(it, timeout=args.timeout)

    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futures = {ex.submit(_worker, it): it for it in items}
        for fut in as_completed(futures):
            name, ok, url, reason = fut.result()
            if not ok and name:
                bad_names.append(name)
                bad_rows.append((name, url, reason))

    Path(args.out).write_text("\n".join(bad_names) + ("\n" if bad_names else ""), encoding="utf-8")
    if args.bad_csv:
        with open(args.bad_csv, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f); w.writerow(["company_name", "url", "reason"]); w.writerows(bad_rows)

    dt = time.time() - t0
    print(f"Checked {len(items)} items in {dt:.1f}s")
    print(f"Bad/non-image links: {len(bad_names)}")
    print(f"Wrote names: {Path(args.out).resolve()}")
    if args.bad_csv:
        print(f"Wrote details: {Path(args.bad_csv).resolve()}")

if __name__ == "__main__":
    main()
