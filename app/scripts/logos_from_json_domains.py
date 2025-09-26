#!/usr/bin/env python3
import argparse, csv, io, json, re, time
from pathlib import Path
from urllib.parse import urlparse, urljoin

import requests
from bs4 import BeautifulSoup
from PIL import Image

# Optional decoders
try:
    import imageio.v3 as iio
    HAS_IMAGEIO = True
except Exception:
    HAS_IMAGEIO = False

try:
    import cairosvg
    HAS_CAIROSVG = True
except Exception:
    HAS_CAIROSVG = False

EMBED_URL_TMPL = "https://cdn.brandfetch.io/{identifier}/w/400/h/400"

PAGE_HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) "
                   "Chrome/120.0.0.0 Safari/537.36"),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/*;q=0.8,*/*;q=0.5",
    "Accept-Language": "en-US,en;q=0.9",
}
IMG_HEADERS_BASE = {
    "User-Agent": PAGE_HEADERS["User-Agent"],
    "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
}

def parse_args():
    ap = argparse.ArgumentParser(
        description="Use JSON (company, domain) → try Brandfetch embed → scrape/download → write brand_name_map.csv."
    )
    ap.add_argument("--client-id", required=True, help="Brandfetch Client ID (?c=...).")
    ap.add_argument("--json", required=True, help="JSON file with a list of objects: {company: str, domain: str}.")
    ap.add_argument("--outdir", default="logos_png", help="Folder for PNGs (and SVGs if kept).")
    ap.add_argument("--summary", default="brandfetch_download_summary.csv", help="Full results CSV.")
    ap.add_argument("--mapfile", default="brand_name_map.csv", help="Mapping CSV: input_company→matched_name(=same)→identifier(host).")
    ap.add_argument("--sleep", type=float, default=2.0, help="Sleep between companies (default: 2.0s).")
    ap.add_argument("--timeout", type=float, default=25.0, help="HTTP timeout seconds.")
    ap.add_argument("--retries", type=int, default=3, help="Retries for 429/5xx.")
    ap.add_argument("--referer", default="", help="Optional Referer header (some CDNs require a real origin).")
    ap.add_argument("--keep-svg", action="store_true", help="Keep SVG alongside PNG (default: keep only PNG).")
    ap.add_argument("--strip-www", action="store_true", help="Strip a leading 'www.' from host if present.")
    return ap.parse_args()

def load_json(path: str) -> list[dict]:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    # Expect entries with keys 'company' and 'domain'
    rows = []
    for row in data:
        company = (row.get("company") or row.get("company_name") or "").strip()
        domain = (row.get("domain") or "").strip()
        rows.append({"company": company, "domain": domain})
    return rows

def extract_host(domain: str, strip_www: bool) -> str:
    """
    Accepts 'tacobell.com' or full URLs like 'https://www.tacobell.com/path?x=y'.
    Returns host; if strip_www=True and host starts with 'www.', removes it.
    """
    if not domain:
        return ""
    # If it's already a bare host, urlparse will place it in path, so prepend scheme
    if "://" not in domain:
        parsed = urlparse("http://" + domain)
    else:
        parsed = urlparse(domain)
    host = parsed.netloc or parsed.path  # handle 'tacobell.com' without scheme
    host = host.strip().strip("/")
    if strip_www and host.startswith("www."):
        host = host[4:]
    return host

def safe_name(s: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", (s or "").strip()) or "logo"

def http_get(url: str, headers: dict, timeout: float, retries: int, sleep: float):
    backoff = 0.8
    last = None
    for _ in range(retries):
        try:
            r = requests.get(url, headers=headers, timeout=timeout, allow_redirects=True)
            last = r
            if r.status_code in (429, 500, 502, 503, 504):
                time.sleep(backoff); backoff *= 1.6; continue
            return r
        except requests.RequestException:
            time.sleep(backoff); backoff *= 1.6
    return last

def pick_from_srcset(srcset: str, base_url: str) -> str | None:
    best, best_score = None, -1.0
    for part in [p.strip() for p in srcset.split(",") if p.strip()]:
        seg = part.split()
        url = seg[0]; desc = seg[1] if len(seg) > 1 else ""
        score = 0.0
        if desc.endswith("x"):
            try: score = float(desc[:-1])
            except: score = 1.0
        elif desc.endswith("w"):
            try: score = float(desc[:-1])
            except: score = heuristic_size_score(url)
        else:
            score = heuristic_size_score(url)
        if score > best_score:
            best_score, best = score, urljoin(base_url, url)
    return best

def heuristic_size_score(url: str) -> float:
    nums = [int(x) for x in re.findall(r'(?:(?<=/w/)|(?<=/h/)|(?<=\bw=)|(?<=\bh=))(\d{2,4})', url)]
    return max(nums) if nums else 1.0

def parse_best_img_url(html: bytes, base_url: str) -> str | None:
    soup = BeautifulSoup(html, "lxml")
    meta = soup.find("meta", attrs={"property": "og:image"})
    if meta and meta.get("content"):
        return urljoin(base_url, meta["content"])
    for link in soup.find_all("link", attrs={"rel": ["preload", "prefetch"]}):
        if (link.get("as") == "image" or "image" in (link.get("imagesrcset") or "")) and link.get("href"):
            return urljoin(base_url, link["href"])
    for pic in soup.find_all("picture"):
        for source in pic.find_all("source"):
            srcset = source.get("srcset")
            if srcset:
                best = pick_from_srcset(srcset, base_url)
                if best: return best
        img = pic.find("img")
        if img and img.get("src"): return urljoin(base_url, img["src"])
    candidates = []
    for img in soup.find_all("img"):
        src = img.get("src")
        if not src: continue
        full = urljoin(base_url, src)
        candidates.append((heuristic_size_score(full), full))
    if candidates:
        candidates.sort(reverse=True)
        return candidates[0][1]
    for source in soup.find_all("source"):
        srcset = source.get("srcset")
        if srcset:
            best = pick_from_srcset(srcset, base_url)
            if best: return best
    return None

def raster_to_png(data: bytes, out_png: Path) -> bool:
    try:
        with Image.open(io.BytesIO(data)) as im:
            if im.mode not in ("RGB","RGBA"):
                im = im.convert("RGBA" if "A" in im.getbands() else "RGB")
            out_png.parent.mkdir(parents=True, exist_ok=True)
            im.save(out_png, format="PNG")
        return True
    except Exception:
        pass
    if HAS_IMAGEIO:
        try:
            arr = iio.imread(data)
            out_png.parent.mkdir(parents=True, exist_ok=True)
            iio.imwrite(out_png, arr, extension=".png")
            return True
        except Exception:
            pass
    return False

def svg_to_png(svg_bytes: bytes, out_png: Path) -> bool:
    if not HAS_CAIROSVG: return False
    try:
        out_png.parent.mkdir(parents=True, exist_ok=True)
        cairosvg.svg2png(bytestring=svg_bytes, write_to=str(out_png))
        return True
    except Exception:
        return False

def guess_ext_from_ctype(ctype: str) -> str:
    if "webp" in ctype: return ".webp"
    if "png"  in ctype: return ".png"
    if "jpeg" in ctype or "jpg" in ctype: return ".jpg"
    if "svg"  in ctype: return ".svg"
    return ".bin"

def fetch_png_from_embed(embed_url: str, identifier: str, outdir: Path, timeout: float, retries: int, sleep: float, referer: str, keep_svg: bool):
    page_headers = PAGE_HEADERS.copy()
    img_headers = IMG_HEADERS_BASE.copy()
    if referer:
        page_headers["Referer"] = referer
        img_headers["Referer"] = referer

    base = re.sub(r"[^A-Za-z0-9._-]+", "_", identifier or "logo")
    out_png = outdir / f"{base}.png"
    out_svg = outdir / f"{base}.svg"

    r = http_get(embed_url, page_headers, timeout, retries, sleep)
    if r is None or not r.ok:
        return "", "", "error", f"http_{getattr(r,'status_code','NA') if r else 'NA'}"

    ctype = (r.headers.get("Content-Type") or "").lower()

    if ctype.startswith("image/"):
        data = r.content
        if "svg" in ctype:
            try:
                out_svg.write_bytes(data)
            except Exception as e:
                return "", "", "error", f"svg_save_error:{e}"
            if svg_to_png(data, out_png):
                if not keep_svg:
                    try: out_svg.unlink(missing_ok=True)
                    except Exception: pass
                    return str(out_png), "", "ok_svg_to_png", ""
                return str(out_png), str(out_svg), "ok_svg_to_png", ""
            else:
                return "", str(out_svg), "ok_svg_saved_only", "cairosvg_not_installed"
        if raster_to_png(data, out_png):
            return str(out_png), "", "ok_png", ""
        ext = guess_ext_from_ctype(ctype)
        raw = outdir / f"{base}{ext}"
        try:
            raw.write_bytes(data)
            return "", str(raw), "saved_original_only", "decode_failed"
        except Exception as e:
            return "", "", "error", f"save_original_failed:{e}"

    img_url = parse_best_img_url(r.content, r.url)
    if not img_url:
        return "", "", "error", "no_image_found_in_html"

    r2 = http_get(img_url, img_headers, timeout, retries, sleep)
    if r2 is None or not r2.ok:
        return "", "", "error", f"image_fetch_failed:{getattr(r2,'status_code','NA')}"

    ctype2 = (r2.headers.get("Content-Type") or "").lower()
    data2 = r2.content

    if "svg" in ctype2 or img_url.lower().endswith(".svg"):
        try:
            out_svg.write_bytes(data2)
        except Exception as e:
            return "", "", "error", f"svg_save_error:{e}"
        if svg_to_png(data2, out_png):
            if not keep_svg:
                try: out_svg.unlink(missing_ok=True)
                except Exception: pass
                return str(out_png), "", "ok_svg_to_png", ""
            return str(out_png), str(out_svg), "ok_svg_to_png", ""
        else:
            return "", str(out_svg), "ok_svg_saved_only", "cairosvg_not_installed"

    if raster_to_png(data2, out_png):
        return str(out_png), "", "ok_png", ""
    else:
        ext = guess_ext_from_ctype(ctype2)
        raw = outdir / f"{base}{ext}"
        try:
            raw.write_bytes(data2)
            return "", str(raw), "saved_original_only", "decode_failed"
        except Exception as e:
            return "", "", "error", f"save_original_failed:{e}"

def main():
    args = parse_args()
    outdir = Path(args.outdir); outdir.mkdir(parents=True, exist_ok=True)
    entries = load_json(args.json)

    results = []
    brand_map_rows = []

    total = len(entries)
    for i, row in enumerate(entries, start=1):
        name = (row.get("company") or "").strip()
        raw_domain = (row.get("domain") or "").strip()
        host = extract_host(raw_domain, strip_www=args.strip_www)

        print(f"[{i}/{total}] {name}  —  domain: {raw_domain}  → host: {host or '(none)'}")
        time.sleep(args.sleep)

        matched_name = name  # per your requirement: second column repeats the company name
        identifier = ""
        status = ""
        error = ""
        saved_png = ""
        saved_svg = ""
        logo_url = ""

        if not host:
            status, error = "no_domain", ""
        else:
            # Build Brandfetch embed URL and try to fetch/convert
            logo_url = f"{EMBED_URL_TMPL.format(identifier=host)}?c={args.client_id}"
            png, aux, st, err = fetch_png_from_embed(
                embed_url=logo_url,
                identifier=host,
                outdir=outdir,
                timeout=args.timeout,
                retries=args.retries,
                sleep=args.sleep,
                referer=args.referer,
                keep_svg=args.keep_svg,
            )
            saved_png, saved_svg, status, error = png, aux, st, (err or "")
            # Only write third column (identifier) if we succeeded in getting a PNG (or SVG→PNG)
            if status.startswith("ok_"):
                identifier = host
            else:
                identifier = ""  # leave blank if fetch failed

        # full results
        results.append({
            "input_company": name,
            "matched_name": matched_name,
            "identifier": identifier,
            "logo_url": logo_url,
            "saved_png": saved_png,
            "saved_svg": saved_svg,
            "status": status,
            "error": error,
        })

        # brand_name_map.csv row (exactly as you asked)
        brand_map_rows.append({
            "input_company": name,
            "matched_name": matched_name,
            "identifier": identifier,  # blank if fetch failed
        })

    # Write summary CSV
    summary = Path(args.summary)
    with open(summary, "w", newline="", encoding="utf-8") as f:
        fields = ["input_company","matched_name","identifier","logo_url","saved_png","saved_svg","status","error"]
        w = csv.DictWriter(f, fieldnames=fields); w.writeheader()
        for r in results: w.writerow(r)

    # Write brand mapping CSV
    mapfile = Path(args.mapfile)
    with open(mapfile, "w", newline="", encoding="utf-8") as f:
        fields = ["input_company","matched_name","identifier"]
        w = csv.DictWriter(f, fieldnames=fields); w.writeheader()
        for r in brand_map_rows: w.writerow(r)

    ok = sum(1 for r in results if r["status"].startswith("ok"))
    total = len(results)
    pct = round(ok / total * 100, 2) if total else 0.0
    print(f"\nDone. PNGs for {ok}/{total} ({pct}%).")
    print(f"Logos dir: {outdir.resolve()}")
    print(f"Summary:   {summary.resolve()}")
    print(f"Brand map: {mapfile.resolve()}")
    if any(r["status"] == "ok_svg_saved_only" for r in results) and not HAS_CAIROSVG:
        print("Note: Some SVGs were not rasterized. Install 'cairosvg' to convert SVG → PNG.")

if __name__ == "__main__":
    main()
