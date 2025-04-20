# PostGIS Setup and Verification

This document provides instructions for setting up, migrating, and verifying the PostGIS extension in the matching service database.

## Overview

The matching service uses PostgreSQL with the PostGIS extension for geospatial functionality. This allows for efficient proximity searches, distance calculations, and other spatial operations.

## Prerequisites

- PostgreSQL 12+ with PostGIS extension installed on the server
- Database connection credentials with sufficient privileges
- Python 3.9+ with required packages installed

## Setup Steps

### 1. Run Database Migrations

The Alembic migration script adds PostGIS support to the database, including:
- Enabling the PostGIS extension
- Adding geometry columns to the Locations table
- Creating trigger functions for automatic geometry updates
- Setting up spatial indexes

To run the migrations:

```bash
# From the project root directory
python -m app.scripts.run_migrations
```

This script will:
1. Locate the Alembic configuration file
2. Run the migration to upgrade the database schema
3. Log the results of the migration

### 2. Verify PostGIS Setup

After running the migrations, you can verify that PostGIS is properly set up:

```bash
# From the project root directory
python -m app.scripts.verify_postgis
```

This script will:
1. Check if the PostGIS extension is installed
2. Verify that the geometry column exists in the Locations table
3. Test the trigger function by inserting a test location
4. Run a spatial query to confirm functionality
5. Clean up test data

### 3. Analyze GIS Functions

To analyze the GIS functions used in the codebase:

```bash
# From the project root directory
python -m app.scripts.analyze_gis_functions
```

This script will:
1. List all available PostGIS functions in the database
2. Identify which functions are being used in the codebase
3. Provide recommendations for optimization

## Troubleshooting

### Common Issues

1. **Missing PostGIS Extension**

   Error: `ERROR: extension "postgis" does not exist`

   Solution: Install PostGIS on the database server:
   ```bash
   # For PostgreSQL 12+ on Ubuntu/Debian
   sudo apt-get install postgresql-12-postgis-3
   
   # For PostgreSQL 12+ on CentOS/RHEL
   sudo yum install postgis30_12
   ```

2. **Permission Issues**

   Error: `ERROR: permission denied for schema public`

   Solution: Ensure the database user has sufficient privileges:
   ```sql
   GRANT ALL ON SCHEMA public TO your_user;
   GRANT ALL ON ALL TABLES IN SCHEMA public TO your_user;
   ```

3. **Migration Failures**

   If migrations fail, check:
   - Database connection settings in `.env` file
   - Database user permissions
   - PostgreSQL and PostGIS versions

## Additional Resources

For more information about the PostGIS implementation in the matching service, see:

- [PostGIS Implementation Documentation](./postgis_implementation.md) - Detailed explanation of the implementation
- [Geospatial Filtering Documentation](./geospatial_filtering.md) - Guide to geospatial filtering with PostGIS

## References

- [PostGIS Official Documentation](https://postgis.net/docs/)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [Alembic Documentation](https://alembic.sqlalchemy.org/)