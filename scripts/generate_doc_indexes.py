#!/usr/bin/env python3
"""
Generate documentation indexes for all documentation categories.

This script scans the docs/ directory and generates index files (README.md)
for each documentation category following the DOCS-KEEPER protocol.
"""

import os
import re
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any


def parse_frontmatter(file_path: Path) -> Dict[str, Any]:
    """Parse frontmatter from markdown files."""
    metadata = {}

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

            # Extract title (first H1)
            title_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
            if title_match:
                metadata['title'] = title_match.group(1)

            # Extract date
            date_match = re.search(r'^Date:\s*(.+)$', content, re.MULTILINE)
            if date_match:
                metadata['date'] = date_match.group(1).strip()

            # Extract status
            status_match = re.search(r'^Status:\s*(.+)$', content, re.MULTILINE)
            if status_match:
                metadata['status'] = status_match.group(1).strip()

            # Extract severity (for investigations/runbooks)
            severity_match = re.search(r'^Severity:\s*(.+)$', content, re.MULTILINE)
            if severity_match:
                metadata['severity'] = severity_match.group(1).strip()

    except Exception as e:
        print(f"Error parsing {file_path}: {e}")

    return metadata


def generate_adr_index(docs_path: Path) -> str:
    """Generate index for Architecture Decision Records."""
    adr_path = docs_path / "adr"
    adr_files = sorted([f for f in adr_path.glob("*.md") if f.name != "README.md"])

    active_adrs = []
    superseded_adrs = []

    for adr_file in adr_files:
        metadata = parse_frontmatter(adr_file)
        title = metadata.get('title', adr_file.stem)
        date = metadata.get('date', 'N/A')
        status = metadata.get('status', 'Unknown')

        # Extract ADR number from filename
        adr_num_match = re.match(r'(\d+)', adr_file.stem)
        adr_num = adr_num_match.group(1) if adr_num_match else 'N/A'

        row = f"| {adr_num} | [{title}]({adr_file.name}) | {date} | {status} |"

        if status.lower() in ['superseded', 'deprecated']:
            superseded_adrs.append(row)
        else:
            active_adrs.append(row)

    content = "# Architecture Decision Records\n\n"

    content += "## Active\n\n"
    if active_adrs:
        content += "| ADR | Title | Date | Status |\n"
        content += "|-----|-------|------|--------|\n"
        content += "\n".join(active_adrs) + "\n"
    else:
        content += "*No active ADRs yet*\n"

    content += "\n## Superseded\n\n"
    if superseded_adrs:
        content += "| ADR | Title | Date | Status |\n"
        content += "|-----|-------|------|--------|\n"
        content += "\n".join(superseded_adrs) + "\n"
    else:
        content += "*No superseded ADRs*\n"

    return content


def generate_investigation_index(docs_path: Path) -> str:
    """Generate index for investigations."""
    inv_path = docs_path / "investigations"
    inv_files = sorted([f for f in inv_path.glob("*.md") if f.name != "README.md"])

    active = []
    resolved = []

    for inv_file in inv_files:
        metadata = parse_frontmatter(inv_file)
        title = metadata.get('title', inv_file.stem).replace('Investigation: ', '')
        date = metadata.get('date', 'N/A')
        status = metadata.get('status', 'Unknown')
        severity = metadata.get('severity', 'Unknown')

        row = f"| [{title}]({inv_file.name}) | {severity} | {date} | {status} |"

        if status.lower() in ['resolved', 'closed']:
            resolved.append(row)
        else:
            active.append(row)

    content = "# Investigations\n\n"

    content += "## Active\n\n"
    if active:
        content += "| Issue | Severity | Date | Status |\n"
        content += "|-------|----------|------|--------|\n"
        content += "\n".join(active) + "\n"
    else:
        content += "*No active investigations*\n"

    content += "\n## Resolved\n\n"
    if resolved:
        content += "| Issue | Severity | Date | Status |\n"
        content += "|-------|----------|------|--------|\n"
        content += "\n".join(resolved) + "\n"
    else:
        content += "*No resolved investigations yet*\n"

    return content


def main():
    """Main entry point."""
    project_root = Path(__file__).parent.parent
    docs_path = project_root / "docs"

    print("Generating documentation indexes...")

    # Generate ADR index
    adr_index_path = docs_path / "adr" / "README.md"
    if (docs_path / "adr").exists():
        adr_content = generate_adr_index(docs_path)
        with open(adr_index_path, 'w', encoding='utf-8') as f:
            f.write(adr_content)
        print(f"✓ Generated {adr_index_path}")

    # Generate investigation index
    inv_index_path = docs_path / "investigations" / "README.md"
    if (docs_path / "investigations").exists():
        inv_content = generate_investigation_index(docs_path)
        with open(inv_index_path, 'w', encoding='utf-8') as f:
            f.write(inv_content)
        print(f"✓ Generated {inv_index_path}")

    print("\nIndex generation complete!")
    print(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == "__main__":
    main()
