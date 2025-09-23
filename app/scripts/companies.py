#!/usr/bin/env python3
import argparse
import csv
import time
from pathlib import Path
from urllib.parse import quote, urlparse

import requests

SEARCH_URL_TMPL = "https://api.brandfetch.io/v2/search/{query}"
CDN_URL_TMPL = "https://cdn.brandfetch.io/{identifier}/w/400/h/400"

DEFAULT_COMPANIES = [
    "AO Globe Life",
    "Destination Canada",
    "Taco Bell Private",
    "The Jackson Agency",
    "Bespoke Technologies, Inc.",
    "Rebuilt",
    "83BAR",
    "Ast",
    "TNStumpff Enterprises",
    "Brilliant PR & Marketing",
    "CCOF",
    "Proprietors of the Cemetery of Mount Auburn",
    "B2C2",
    "ARMM Logistics Corp",
    "M Star Shipping Corp",
    "Ciq",
    "48forty Solutions and Relogistics Services",
    "Ea Agency / Symmetry Financial Group",
    "Ark Development Greenville",
    "WeightWatchers",
    "DIG Restaurant Teams",
    "Current Job Openings at MNTN",
    "Flock Freight",
    "Leland Saylor Associates",
    "LeafGuard",
    "TandemLaunch",
    "Current Job Openings at SingleStore",
    "Ortho2, LLC.",
    "Nutcracker Therapeutics",
    "East Harlem Tutorial Program",
    "AlphaSense - for Referrals",
    "DNA Script",
    "Aimé Leon Dore EU",
    "Unlimited Technology",
    "Job Board",
    "PALO IT",
    "Brandon J. Broderick",
    "Read AI",
    "Current Job Openings at MLB (Job Board Only)",
    "ANS",
    "Tiger Correctional Services",
    "Phase Four",
    "Salsify",
    "The Party Staff, Inc.",
    "AQR India",
    "ShipMonk",
    "AEVEX Aerospace",
    "STI",
    "Metropolitan Commercial Bank",
]

def parse_args():
    p = argparse.ArgumentParser(description="Build Brandfetch logo links after doing Brand Search.")
    p.add_argument("--client-id", required=True, help="Brandfetch client id (used as '?c=...').")
    p.add_argument("--input", help="Optional text file with one company per line. Defaults to built-in list.")
    p.add_argument("--outfile", default="brand_logo_links.csv", help="Output CSV path. Default: brand_logo_links.csv")
    p.add_argument("--sleep", type=float, default=0.35, help="Sleep seconds between requests. Default: 0.35")
    p.add_argument("--timeout", type=float, default=15.0, help="HTTP timeout in seconds. Default: 15")
    p.add_argument("--retries", type=int, default=3, help="Retries for 429/5xx. Default: 3")
    return p.parse_args()

def load_companies(path: str | None) -> list[str]:
    if not path:
        return DEFAULT_COMPANIES[:]
    with open(path, "r", encoding="utf-8") as f:
        names = [ln.strip() for ln in f if ln.strip()]
    return names

def http_get(url: str, params: dict, timeout: float, retries: int) -> requests.Response | None:
    backoff = 0.8
    for attempt in range(1, retries + 1):
        try:
            r = requests.get(url, params=params, timeout=timeout)
        except requests.RequestException:
            if attempt == retries:
                return None
            time.sleep(backoff)
            backoff *= 1.6
            continue
        if r.status_code in (429, 500, 502, 503, 504):
            if attempt == retries:
                return r
            time.sleep(backoff)
            backoff *= 1.6
            continue
        return r
    return None

def extract_identifier_from_item(item: dict) -> str | None:
    """
    Prefer a bare domain (e.g., 'apple.com'). Fallbacks: website->netloc, then brandId/id/slug.
    """
    candidates = []
    if item.get("domain"):
        candidates.append(item["domain"])
    if item.get("website"):
        try:
            netloc = urlparse(item["website"]).netloc
            if netloc:
                candidates.append(netloc)
        except Exception:
            pass
    for key in ("brandId", "id", "slug"):
        if item.get(key):
            candidates.append(item[key])

    for cand in candidates:
        if "." in cand or "/" not in cand:
            return cand
    return candidates[0] if candidates else None

def brand_search_first(query: str, client_id: str, timeout: float, retries: int) -> dict | None:
    url = SEARCH_URL_TMPL.format(query=quote(query, safe=""))
    params = {"c": client_id}
    resp = http_get(url, params=params, timeout=timeout, retries=retries)
    if resp is None:
        return {"_error": "request_error_none"}
    if not resp.ok:
        # still return structure with error so caller can record it
        return {"_error": f"http_{resp.status_code}", "_body": (resp.text or "")[:300]}

    try:
        data = resp.json()
    except ValueError:
        return {"_error": "invalid_json"}

    if isinstance(data, list) and data:
        return data[0]
    if isinstance(data, dict):
        for key in ("results", "brands", "items"):
            if isinstance(data.get(key), list) and data[key]:
                return data[key][0]
    return None  # no results

def main():
    args = parse_args()
    client_id = args.client_id.strip()
    companies = load_companies(args.input)
    outpath = Path(args.outfile)

    with open(outpath, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["input_company", "matched_name", "identifier", "logo_url", "error"])

        for i, name in enumerate(companies, start=1):
            print(f"[{i}/{len(companies)}] {name}")
            time.sleep(args.sleep)

            first = brand_search_first(name, client_id, timeout=args.timeout, retries=args.retries)

            matched_name = None
            identifier = None
            error = None
            logo_url = ""

            if first is None:
                error = "no_results"
            elif isinstance(first, dict) and first.get("_error"):
                error = first["_error"]
            else:
                matched_name = first.get("name")
                identifier = extract_identifier_from_item(first)
                if not identifier:
                    error = "no_identifier_in_first_result"
                else:
                    logo_url = f"{CDN_URL_TMPL.format(identifier=identifier)}?c={client_id}"

            writer.writerow([name, matched_name or "", identifier or "", logo_url, error or ""])

    print(f"\nLinks written to: {outpath.resolve()}")

if __name__ == "__main__":
    main()
