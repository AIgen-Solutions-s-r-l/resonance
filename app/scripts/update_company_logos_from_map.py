#!/usr/bin/env python3
"""
Update public."Companies".logo from brand_name_map.csv

- Reads brand_name_map.csv (columns: input_company, matched_name, identifier)
- For each row with a non-empty identifier, sets:
    logo = {base_url}/{identifier}.png
  where base_url defaults to:
    https://laboroprodhot.z1.web.core.windows.net/logos
- Matches rows by exact company_name == input_company (first column).
- Uses the project's async DB pool via app.utils.db_utils.get_db_cursor.

Usage:
  python update_company_logos_from_map.py \
    --csv ../../brand_name_map.csv \
    --apply

Options:
  --base-url  Override base blob URL (default shown above)
  --apply     Actually write to DB (otherwise dry run)
  --batch     Batch size for executemany (default 200)
  --ci        Case-insensitive match on company_name
  --table     Override table (default public."Companies")
"""

import asyncio
import csv
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple

# Ensure project root is on sys.path (same pattern as other scripts)
from pathlib import Path as _Path
_project_root = str(_Path(__file__).parents[2])
if _project_root not in sys.path:
    sys.path.append(_project_root)

from loguru import logger
from app.utils.db_utils import get_db_cursor
from app.core.config import settings

DEFAULT_BASE_URL = "https://laboroprodhot.z1.web.core.windows.net/logos"

@dataclass
class Args:
    csv_path: Path
    base_url: str = DEFAULT_BASE_URL
    apply: bool = False
    batch: int = 200
    ci: bool = False
    table: str = 'public."Companies"'


def parse_args() -> Args:
    import argparse

    p = argparse.ArgumentParser(
        description='Update public."Companies".logo from brand_name_map.csv'
    )
    p.add_argument(
        "--csv",
        required=True,
        help="Path to brand_name_map.csv (expects input_company,matched_name,identifier).",
    )
    p.add_argument(
        "--base-url",
        default=DEFAULT_BASE_URL,
        help=f"Base blob URL (default: {DEFAULT_BASE_URL})",
    )
    p.add_argument(
        "--apply",
        action="store_true",
        help="Write changes to DB. Omit to run as dry run.",
    )
    p.add_argument(
        "--batch",
        type=int,
        default=200,
        help="Batch size for updates (default: 200).",
    )
    p.add_argument(
        "--ci",
        action="store_true",
        help="Case-insensitive match on company_name.",
    )
    p.add_argument(
        "--table",
        default='public."Companies"',
        help='Target table (default: public."Companies").',
    )

    a = p.parse_args()
    return Args(
        csv_path=Path(a.csv),
        base_url=a.base_url.rstrip("/"),
        apply=a.apply,
        batch=a.batch,
        ci=a.ci,
        table=a.table,
    )


def load_map(csv_path: Path) -> List[Tuple[str, str]]:
    """
    Returns a list of (input_company, identifier).
    """
    rows: List[Tuple[str, str]] = []
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            input_company = (r.get("input_company") or "").strip()
            identifier = (r.get("identifier") or "").strip()
            rows.append((input_company, identifier))
    return rows


async def update_exact(args: Args, pairs: List[Tuple[str, str]]) -> Tuple[int, int, int, int]:
    """
    Exact match on company_name.
    Returns: (updated, unchanged, missing_in_db, skipped_no_identifier)
    """
    updated = unchanged = missing = skipped = 0

    # Filter usable rows
    usable = [(name, ident) for (name, ident) in pairs if name and ident]
    skipped = len([1 for (_, ident) in pairs if not ident])

    if not usable:
        return (0, 0, 0, skipped)

    # Preload existing rows for these names to avoid 1-by-1 SELECT
    names = list({name for (name, _) in usable})
    index = {}

    query_existing = f"""
        SELECT company_id, company_name, logo
        FROM {args.table}
        WHERE company_name = ANY(%s)
    """

    async with get_db_cursor() as cur:
        await cur.execute(query_existing, (names,))
        for row in await cur.fetchall():
            index[row["company_name"]] = (row["company_id"], row["logo"])

    # Prepare updates
    updates: List[Tuple[str, str]] = []  # (logo_url, company_name)
    for company_name, identifier in usable:
        logo_url = f"{args.base_url}/{identifier}.png"
        if company_name in index:
            _, current_logo = index[company_name]
            if current_logo == logo_url:
                unchanged += 1
            else:
                updates.append((logo_url, company_name))
        else:
            missing += 1

    # Apply in batches
    if args.apply and updates:
        update_sql = f'UPDATE {args.table} SET logo = %s WHERE company_name = %s'
        async with get_db_cursor() as cur:
            for i in range(0, len(updates), args.batch):
                chunk = updates[i:i + args.batch]
                await cur.executemany(update_sql, chunk)
        updated = len(updates)
    else:
        updated = len(updates)

    return (updated, unchanged, missing, skipped)


async def update_case_insensitive(args: Args, pairs: List[Tuple[str, str]]) -> Tuple[int, int, int, int]:
    """
    Case-insensitive match on company_name.
    Loads all names once, then matches by lower(name).
    """
    updated = unchanged = missing = skipped = 0

    usable = [(name, ident) for (name, ident) in pairs if name and ident]
    skipped = len([1 for (_, ident) in pairs if not ident])

    if not usable:
        return (0, 0, 0, skipped)

    # Load all companies once
    async with get_db_cursor() as cur:
        await cur.execute(f'SELECT company_id, company_name, logo FROM {args.table}')
        all_rows = await cur.fetchall()

    index = {row["company_name"].lower(): (row["company_id"], row["company_name"], row["logo"]) for row in all_rows}

    updates: List[Tuple[str, str]] = []  # (logo_url, exact_company_name)
    for company_name, identifier in usable:
        key = company_name.lower()
        if key in index:
            _, exact_name, current_logo = index[key]
            logo_url = f"{args.base_url}/{identifier}.png"
            if current_logo == logo_url:
                unchanged += 1
            else:
                updates.append((logo_url, exact_name))
        else:
            missing += 1

    if args.apply and updates:
        update_sql = f'UPDATE {args.table} SET logo = %s WHERE company_name = %s'
        async with get_db_cursor() as cur:
            for i in range(0, len(updates), args.batch):
                chunk = updates[i:i + args.batch]
                await cur.executemany(update_sql, chunk)
        updated = len(updates)
    else:
        updated = len(updates)

    return (updated, unchanged, missing, skipped)


async def main_async(args: Args):
    logger.info(f"DB URL detected: {'SET' if settings.database_url else 'NOT SET'}")
    pairs = load_map(args.csv_path)
    total = len(pairs)
    with_id = sum(1 for _, ident in pairs if ident)
    logger.info(f"Loaded {total} CSV rows; {with_id} with identifier (3rd column).")

    if args.ci:
        updated, unchanged, missing, skipped = await update_case_insensitive(args, pairs)
    else:
        updated, unchanged, missing, skipped = await update_exact(args, pairs)

    logger.info("=== Summary ===")
    logger.info(f"Apply changes: {'YES' if args.apply else 'NO (dry-run)'}")
    logger.info(f"Updated rows:  {updated}")
    logger.info(f"Unchanged:     {unchanged}")
    logger.info(f"Missing in DB: {missing}")
    logger.info(f"Skipped (no id): {skipped}")


def main():
    args = parse_args()
    asyncio.run(main_async(args))


if __name__ == "__main__":
    main()

'''
# from repo root
python app/scripts/update_company_logos_from_map.py --csv brand_name_map.csv --apply

# or if your CSV sits one level up from scripts/
python app/scripts/update_company_logos_from_map.py --csv ../../brand_name_map.csv --apply

# Dry-run first (recommended)
python app/scripts/update_company_logos_from_map.py --csv ../../brand_name_map.csv

# Case-insensitive matches (if needed)
python app/scripts/update_company_logos_from_map.py --csv ../../brand_name_map.csv --ci --apply

# Custom batch size or base URL
python app/scripts/update_company_logos_from_map.py --csv ../../brand_name_map.csv --batch 500 \
  --base-url https://laboroprodhot.z1.web.core.windows.net/logos --apply

'''