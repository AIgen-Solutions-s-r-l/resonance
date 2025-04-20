# PostGIS Implementation in the Matching Service

## Overview

This document provides a detailed explanation of how PostGIS is implemented in the matching service for geospatial functionality. It covers the database schema, migrations, functions, and usage patterns.

## Table of Contents

1. [Database Schema](#database-schema)
2. [PostGIS Extension](#postgis-extension)
3. [Geospatial Columns and Indexes](#geospatial-columns-and-indexes)
4. [Trigger Functions](#trigger-functions)
5. [Spatial Queries](#spatial-queries)
6. [Alembic Migrations](#alembic-migrations)
7. [Verification and Testing](#verification-and-testing)

## Database Schema

The matching service uses PostgreSQL with the PostGIS extension for geospatial functionality. The main tables involved in geospatial operations are:

- **Locations**: Stores location data including city, country, latitude, longitude, and a geometry column for spatial operations
- **Jobs**: References locations and includes vector embeddings for similarity searches
- **Countries**: Stores country information referenced by locations

## PostGIS Extension

PostGIS extends PostgreSQL with geospatial capabilities, allowing for:

- Storage of geographic and geometric data types
- Spatial indexing for efficient queries
- Geospatial functions for distance calculations, containment tests, etc.
- Coordinate system transformations

The extension is enabled in the database with:

```sql
CREATE EXTENSION IF NOT EXISTS postgis;
```

## Geospatial Columns and Indexes

### Geometry Column

The `Locations` table includes a `geom` column of type `geometry(Point, 4326)`:

```sql
ALTER TABLE "Locations" 
ADD COLUMN IF NOT EXISTS geom geometry(Point, 4326);
```

This column stores points in the WGS84 coordinate system (SRID 4326), which is the standard for GPS coordinates (latitude/longitude).

### Spatial Index

A GiST (Generalized Search Tree) index is created on the `geom` column to optimize spatial queries:

```sql
CREATE INDEX idx_locations_geom ON "Locations" USING GIST(geom);
```

This index significantly improves the performance of spatial operations like distance calculations and containment tests.

## Trigger Functions

A trigger function automatically updates the `geom` column whenever latitude and longitude values are inserted or updated:

```sql
CREATE OR REPLACE FUNCTION update_geom_column()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.latitude IS NOT NULL AND NEW.longitude IS NOT NULL THEN
        NEW.geom = ST_SetSRID(ST_MakePoint(NEW.longitude, NEW.latitude), 4326);
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_location_geom
BEFORE INSERT OR UPDATE ON "Locations"
FOR EACH ROW
EXECUTE FUNCTION update_geom_column();
```

This ensures that the geometry column is always in sync with the latitude and longitude values, maintaining data consistency.

## Spatial Queries

### Distance-Based Searches

The matching service uses `ST_DWithin` for radius-based searches around a point:

```sql
SELECT * FROM "Jobs" j
JOIN "Locations" l ON j.location_id = l.location_id
WHERE ST_DWithin(
    l.geom::geography,
    ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geography,
    %s
)
```

Parameters:
- `%s, %s`: Longitude and latitude of the center point
- `%s`: Radius in meters

The `::geography` cast ensures that distances are calculated in meters on the spheroid, not in degrees.

### Performance Optimization

For better performance, the query includes:
- The `l.city = 'remote'` condition to include remote jobs
- Proper indexing on the `geom` column
- Type casting to ensure correct distance calculations

## Alembic Migrations

The PostGIS functionality is added through Alembic migrations:

1. **Initial Migration**: Creates the base tables (Companies, Countries, Locations, Jobs)
2. **PostGIS Migration**: Adds the PostGIS extension, geometry column, trigger function, and spatial index

The migration file `20250421_add_postgis_support.py` handles:
- Enabling the PostGIS extension
- Adding the `geom` column to the Locations table
- Creating the trigger function and trigger
- Creating the spatial index
- Adding additional columns to the Jobs table (sparse_embeddings, cluster_id)

## Verification and Testing

The `verify_postgis.py` script checks that:
1. The PostGIS extension is installed
2. The geometry column exists in the Locations table
3. The trigger function and trigger are working correctly
4. Spatial queries return expected results

Unit tests in `test_geo_matching.py` verify:
- Location filtering with geographic parameters
- Radius-based searches in both kilometers and meters
- Proper handling of incomplete geographic data

## Usage in the Application

The `JobQueryBuilder` class in `query_builder.py` constructs SQL queries with PostGIS functions:

```python
def _build_location_filters(self, location: LocationFilter) -> Tuple[List[str], List[Any]]:
    # ...
    if has_geo_coordinates:
        where_clauses.append("""
        (
            l.city = 'remote'
            OR ST_DWithin(
                ST_MakePoint(l.longitude::DOUBLE PRECISION, l.latitude::DOUBLE PRECISION)::geography,
                ST_MakePoint(%s, %s)::geography,
                %s
            )
        )
        """)
        query_params.append(float(location.longitude))
        query_params.append(float(location.latitude))
        query_params.append(radius_meters)
    # ...
```

This allows the application to filter jobs based on geographic proximity to a specified location.