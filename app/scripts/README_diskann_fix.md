# Fixing DiskANN Index Issues

This document provides instructions for fixing the diskann index issues that cause the following error:

```
diskann index needs to be upgraded to version 2
DETAIL: If you haven't changed vector dimension for the indexed column, and, "max_neighbors" and "l_value_ib" parameters for the index since it's created, you can use upgrade_diskann_index() function to quickly upgrade the index. Otherwise, upgrade_diskann_index() is not recommended and REINDEX is required.
```

## Available Scripts

Two scripts are provided to fix this issue:

1. `upgrade_diskann_index.py` - A simple script that only performs the upgrade operation
2. `fix_diskann_index.py` - A comprehensive script with multiple options for fixing the issue

## Quick Fix

If you just want to quickly fix the issue and haven't changed the vector dimensions or other parameters, run:

```bash
python -m app.scripts.upgrade_diskann_index
```

This will attempt to upgrade all diskann indices to version 2 using the `upgrade_diskann_index()` function.

## Advanced Options

For more control over the fix process, use the `fix_diskann_index.py` script which provides three modes:

1. **Upgrade Mode** (default): Uses the `upgrade_diskann_index()` function
   ```bash
   python -m app.scripts.fix_diskann_index --mode=upgrade
   ```

2. **Reindex Mode**: Uses the `REINDEX` command to rebuild the index
   ```bash
   python -m app.scripts.fix_diskann_index --mode=reindex
   ```

3. **Recreate Mode**: Drops the existing index so it can be recreated
   ```bash
   python -m app.scripts.fix_diskann_index --mode=recreate
   ```

You can add the `--force` flag to skip confirmation prompts:
```bash
python -m app.scripts.fix_diskann_index --mode=recreate --force
```

## When to Use Each Mode

- **Upgrade**: Use this when you haven't changed the vector dimension, max_neighbors, or l_value_ib parameters. This is the fastest option.
- **Reindex**: Use this if the upgrade fails or if you've made minor changes to the index parameters.
- **Recreate**: Use this as a last resort if both upgrade and reindex fail. After dropping the index, you'll need to run the `create_vector_indices.py` script to recreate it.

## After Recreating Indices

If you used the recreate mode, you'll need to recreate the indices using:

```bash
python -m app.scripts.create_vector_indices
```

## Troubleshooting

If you encounter issues with any of these scripts:

1. Check the PostgreSQL logs for more detailed error messages
2. Verify that the pgvector extension is properly installed
3. Ensure your database user has the necessary permissions to modify indices
4. If all else fails, consider recreating the entire database schema and reindexing

## Impact on Application

While fixing the indices, the vector similarity search functionality may be temporarily unavailable or slower than usual. Plan to run these scripts during a maintenance window if possible.