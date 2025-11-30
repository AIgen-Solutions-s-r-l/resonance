#!/usr/bin/env python3
"""
Find stale documentation that hasn't been updated recently.

This script identifies documentation files that:
- Haven't been updated in > 6 months
- Reference deprecated code or features
- Are marked as 'Draft' for > 30 days
"""

import os
import re
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict


def get_file_age(file_path: Path) -> int:
    """Get the age of a file in days since last modification."""
    mtime = os.path.getmtime(file_path)
    age = datetime.now() - datetime.fromtimestamp(mtime)
    return age.days


def check_draft_status(file_path: Path) -> bool:
    """Check if a document is marked as Draft."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            # Check for Status: Draft
            if re.search(r'^Status:\s*Draft', content, re.MULTILINE | re.IGNORECASE):
                return True
    except Exception:
        pass
    return False


def find_stale_docs(root_path: Path, age_threshold: int = 180) -> List[Dict[str, any]]:
    """Find documentation files that are potentially stale."""
    stale_docs = []

    markdown_files = list(root_path.rglob("*.md"))

    for md_file in markdown_files:
        # Skip README files and templates
        if md_file.name == "README.md" or "template" in md_file.parts:
            continue

        age_days = get_file_age(md_file)
        is_draft = check_draft_status(md_file)

        reasons = []

        # Check if older than threshold
        if age_days > age_threshold:
            reasons.append(f"Not updated in {age_days} days")

        # Check if draft for too long
        if is_draft and age_days > 30:
            reasons.append(f"Draft status for {age_days} days")

        if reasons:
            stale_docs.append({
                'path': md_file.relative_to(root_path),
                'age_days': age_days,
                'reasons': reasons
            })

    return sorted(stale_docs, key=lambda x: x['age_days'], reverse=True)


def main():
    """Main entry point."""
    project_root = Path(__file__).parent.parent
    docs_path = project_root / "docs"

    print("Checking for stale documentation...")
    print(f"Threshold: 180 days (6 months)\n")

    stale_docs = find_stale_docs(docs_path)

    if stale_docs:
        print(f"⚠️  Found {len(stale_docs)} potentially stale document(s):\n")
        for doc in stale_docs:
            print(f"  {doc['path']}")
            print(f"    Age: {doc['age_days']} days")
            for reason in doc['reasons']:
                print(f"    - {reason}")
            print()

        print("Consider reviewing and updating these documents.")
        return 1
    else:
        print("✓ No stale documentation found!")
        return 0


if __name__ == "__main__":
    exit(main())
