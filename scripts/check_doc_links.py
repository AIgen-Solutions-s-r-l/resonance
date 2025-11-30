#!/usr/bin/env python3
"""
Check for broken links in documentation files.

This script validates internal markdown links in the docs/ directory
and reports any broken references.
"""

import os
import re
from pathlib import Path
from typing import List, Tuple, Set


def find_markdown_files(root_path: Path) -> List[Path]:
    """Find all markdown files in the given path."""
    return list(root_path.rglob("*.md"))


def extract_links(content: str, file_path: Path) -> List[Tuple[str, int]]:
    """Extract all markdown links from content with line numbers."""
    links = []

    # Match markdown links: [text](url)
    pattern = r'\[([^\]]+)\]\(([^\)]+)\)'

    for line_num, line in enumerate(content.split('\n'), 1):
        for match in re.finditer(pattern, line):
            link_url = match.group(2)
            # Only check relative links (internal documentation)
            if not link_url.startswith(('http://', 'https://', '#', 'mailto:')):
                links.append((link_url, line_num))

    return links


def resolve_link(file_path: Path, link: str) -> Path:
    """Resolve a relative link to an absolute path."""
    # Handle anchor links
    if '#' in link:
        link = link.split('#')[0]
        if not link:  # Pure anchor link (same file)
            return file_path

    # Resolve relative to the file's directory
    target = (file_path.parent / link).resolve()
    return target


def check_links(root_path: Path) -> Tuple[List[str], int]:
    """Check all markdown files for broken links."""
    markdown_files = find_markdown_files(root_path)
    broken_links = []
    total_links = 0

    for md_file in markdown_files:
        try:
            with open(md_file, 'r', encoding='utf-8') as f:
                content = f.read()

            links = extract_links(content, md_file)
            total_links += len(links)

            for link_url, line_num in links:
                target = resolve_link(md_file, link_url)

                if not target.exists():
                    relative_path = md_file.relative_to(root_path)
                    broken_links.append(
                        f"{relative_path}:{line_num} -> {link_url} (resolved to {target})"
                    )

        except Exception as e:
            print(f"Error processing {md_file}: {e}")

    return broken_links, total_links


def main():
    """Main entry point."""
    project_root = Path(__file__).parent.parent
    docs_path = project_root / "docs"

    print("Checking documentation links...")
    print(f"Scanning: {docs_path}\n")

    broken_links, total_links = check_links(docs_path)

    if broken_links:
        print(f"❌ Found {len(broken_links)} broken link(s) out of {total_links} total links:\n")
        for broken_link in broken_links:
            print(f"  - {broken_link}")
        return 1
    else:
        print(f"✓ All {total_links} internal links are valid!")
        return 0


if __name__ == "__main__":
    exit(main())
