# PostGIS Setup Guide

This guide provides step-by-step instructions for setting up PostGIS in the matching service database.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Installing PostGIS](#installing-postgis)
3. [Database Configuration](#database-configuration)
4. [Running Migrations](#running-migrations)
5. [Verifying the Setup](#verifying-the-setup)
6. [Troubleshooting](#troubleshooting)

## Prerequisites

Before setting up PostGIS, ensure you have:

- PostgreSQL 16.x or later installed
- Database user with superuser privileges
- Access to the matching service database
- Alembic migration tool installed

## Installing PostGIS

### On Ubuntu/Debian

```bash
# Install PostGIS package
sudo apt update
sudo apt install postgresql-16-postgis-3

# Verify installation
sudo -u postgres psql -c "SELECT PostGIS_version();"
```

### On macOS (using Homebrew)

```bash
# Install PostGIS
brew install postgis

# Verify installation
psql -d postgres -c "SELECT PostGIS_version();"
```

### On Windows

1. Download the PostGIS bundle from [https://postgis.net/windows_downloads/](https://postgis.net/windows_downloads/)
2. Run the installer and follow the instructions
3. Verify installation:
   ```bash
   psql -d postgres -c "SELECT PostGIS_version();"
   ```

### Using Docker

If you're using Docker, use the official PostGIS image:

```bash
# Pull the PostGIS image
docker pull postgis/postgis:16-3.4

# Run a PostgreSQL container with PostGIS
docker run --name postgres-postgis -e POSTGRES_PASSWORD=password -d postgis/postgis:16-3.4
```

## Database Configuration

### Enabling PostGIS Extension

Connect to your database and enable the PostGIS extension:

```sql
-- Connect to your database
\c matching

-- Enable PostGIS extension
CREATE EXTENSION IF NOT EXISTS postgis;

-- Verify PostGIS is enabled
SELECT PostGIS_version();
```

### Setting Up Additional Extensions

For vector search capabilities, also enable these extensions:

```sql
-- Enable vector extension for embeddings
CREATE EXTENSION IF NOT EXISTS vector;

-- Enable pg_trgm for text search
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Enable pg_diskann for approximate nearest neighbor search (if available)
CREATE EXTENSION IF NOT EXISTS pg_diskann;
```

## Running Migrations

Our project uses Alembic migrations to set up the database schema, including PostGIS support.

### Using the Migration Script

The easiest way to run migrations is using our migration script:

```bash
# Run migrations with verbose output
python -m app.scripts.run_migrations --verbose

# Run a dry run to see what would be applied
python -m app.scripts.run_migrations --dry-run

# Backup the database schema before applying migrations
python -m app.scripts.run_migrations --backup
```

### Manual Migration with Alembic

If you prefer to run Alembic directly:

```bash
# Navigate to the alembic directory
cd app/alembic/alembic

# Run migrations
alembic upgrade head

# Check current revision
alembic current
```

## Verifying the Setup

### Using the Verification Script

We provide a script to verify that PostGIS is properly set up:

```bash
# Run the verification script
python -m app.scripts.verify_postgis
```

The script checks:
- PostGIS extension is installed
- Geometry column exists in the Locations table
- Trigger function for updating geometry is working
- Spatial index is created
- Basic spatial queries work correctly

### Manual Verification

You can also verify the setup manually:

```sql
-- Check PostGIS version
SELECT PostGIS_version();

-- Check geometry column in Locations table
SELECT f_geometry_column, type, srid, coord_dimension 
FROM geometry_columns 
WHERE f_table_name = 'Locations';

-- Check trigger function
SELECT routine_name, routine_definition 
FROM information_schema.routines 
WHERE routine_name = 'update_geom_column';

-- Check trigger
SELECT trigger_name, event_manipulation, action_statement
FROM information_schema.triggers 
WHERE trigger_name = 'update_location_geom';

-- Check spatial index
SELECT indexname, indexdef 
FROM pg_indexes 
WHERE indexname = 'idx_locations_geom';

-- Test a spatial query
SELECT COUNT(*) FROM "Locations" 
WHERE ST_DWithin(
    geom::geography,
    ST_SetSRID(ST_MakePoint(-74.0060, 40.7128), 4326)::geography,
    5000
);
```

## Troubleshooting

### Common Issues

#### PostGIS Extension Not Found

If you get an error like `ERROR: could not open extension control file "/usr/share/postgresql/16/extension/postgis.control"`:

```bash
# Check if PostGIS package is installed
dpkg -l | grep postgis  # On Debian/Ubuntu
brew list | grep postgis  # On macOS

# Install the package if missing
sudo apt install postgresql-16-postgis-3  # On Debian/Ubuntu
brew install postgis  # On macOS
```

#### Permission Denied

If you get permission errors:

```bash
# Grant superuser privileges to your database user
sudo -u postgres psql -c "ALTER USER adminlaborolabs WITH SUPERUSER;"
```

#### Migration Fails

If the migration fails:

1. Check the error message for specific issues
2. Verify database connection settings in `.env` file
3. Try running with `--verbose` flag for more detailed output:
   ```bash
   python -m app.scripts.run_migrations --verbose
   ```

#### Geometry Column Not Updating

If the geometry column isn't being updated automatically:

```sql
-- Check if trigger is working
SELECT tgname, tgenabled 
FROM pg_trigger 
WHERE tgname = 'update_location_geom';

-- Recreate the trigger if needed
DROP TRIGGER IF EXISTS update_location_geom ON "Locations";
CREATE TRIGGER update_location_geom
BEFORE INSERT OR UPDATE ON "Locations"
FOR EACH ROW
EXECUTE FUNCTION update_geom_column();

-- Update existing locations
UPDATE "Locations"
SET geom = ST_SetSRID(ST_MakePoint(longitude, latitude), 4326)
WHERE latitude IS NOT NULL AND longitude IS NOT NULL AND geom IS NULL;
```

### Getting Help

If you encounter issues not covered here:

1. Check the PostgreSQL logs:
   ```bash
   sudo tail -f /var/log/postgresql/postgresql-16-main.log  # On Ubuntu
   ```

2. Run the database analysis script for more insights:
   ```bash
   python -m app.scripts.analyze_gis_functions
   ```

3. Contact the database administrator or open an issue in the project repository.