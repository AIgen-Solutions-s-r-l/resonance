# Documentation Maintenance Scripts

This directory contains scripts for maintaining documentation following the DOCS-KEEPER protocol.

## Available Scripts

### generate_doc_indexes.py

Generates index files (README.md) for all documentation categories.

```bash
python scripts/generate_doc_indexes.py
```

**What it does:**
- Scans all documentation directories (adr/, hld/, investigations/, etc.)
- Parses metadata from markdown files
- Generates organized index tables
- Updates README.md files in each category

**When to run:**
- After adding new ADRs, HLDs, investigations, or other documents
- Weekly as part of documentation maintenance
- Before major releases

### check_doc_links.py

Validates internal links in documentation files.

```bash
python scripts/check_doc_links.py
```

**What it does:**
- Scans all markdown files in docs/
- Extracts internal markdown links
- Validates that linked files exist
- Reports broken links with file and line number

**When to run:**
- Before committing documentation changes
- As part of CI/CD pipeline
- Daily automated check

**Exit codes:**
- 0: All links valid
- 1: Broken links found

### find_stale_docs.py

Identifies documentation that may need updating.

```bash
python scripts/find_stale_docs.py
```

**What it does:**
- Finds files not updated in > 6 months
- Identifies documents in Draft status for > 30 days
- Reports potentially outdated documentation

**When to run:**
- Monthly documentation audit
- Quarterly review process
- Before major releases

**Exit codes:**
- 0: No stale docs found
- 1: Stale docs detected

## Automation

### Weekly Tasks

```bash
# Run all maintenance scripts
python scripts/generate_doc_indexes.py
python scripts/check_doc_links.py
python scripts/find_stale_docs.py
```

### CI/CD Integration

Add to your GitHub Actions workflow:

```yaml
- name: Check documentation links
  run: python scripts/check_doc_links.py

- name: Check for stale documentation
  run: python scripts/find_stale_docs.py
```

### Pre-commit Hook

Add to `.git/hooks/pre-commit`:

```bash
#!/bin/bash
# Check documentation links before commit
python scripts/check_doc_links.py
if [ $? -ne 0 ]; then
    echo "❌ Documentation has broken links. Fix them before committing."
    exit 1
fi
```

## Adding New Scripts

When adding new documentation maintenance scripts:

1. Follow the existing naming convention
2. Include proper error handling
3. Return appropriate exit codes (0 = success, 1 = issues found)
4. Add usage documentation to this README
5. Update automation workflows if applicable

## Related Documentation

- **DOCS-KEEPER Protocol**: `dev-prompts/DOCS-KEEPER-PROTO.yaml`
- **Documentation Index**: `docs/README.md`
- **Templates**: `docs/templates/`
