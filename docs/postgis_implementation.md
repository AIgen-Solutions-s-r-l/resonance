# PostGIS Implementation in Matching Service

This document provides a comprehensive overview of the PostGIS implementation in the matching service, including setup, usage, and optimization.

## Table of Contents

1. [Overview](#overview)
2. [Database Schema](#database-schema)
3. [Key GIS Functions](#key-gis-functions)
4. [Geospatial Queries](#geospatial-queries)
5. [Performance Optimization](#performance-optimization)
6. [Vector Search Integration](#vector-search-integration)
7. [Maintenance and Monitoring](#maintenance-and-monitoring)
8. [Troubleshooting](#troubleshooting)

## Overview

The matching service uses PostGIS to enable geospatial filtering of job listings. This allows users to search for jobs within a specific radius of their location, enhancing the relevance of search results.

PostGIS is an extension to PostgreSQL that adds support for geographic objects, allowing location queries to be run in SQL. Our implementation uses the following key components:

- PostGIS extension (version 3.3.3)
- Geometry columns for storing location data
- Spatial indexes for efficient querying
- Trigger functions for automatic geometry updates
- Integration with vector search for combined semantic and spatial filtering

## Database Schema

### Locations Table

The `Locations` table stores geographic information with the following structure:

```sql
CREATE TABLE "Locations" (
    location_id SERIAL PRIMARY KEY,
    city VARCHAR(255) NOT NULL,
    country INTEGER NOT NULL REFERENCES "Countries"(country_id),
    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION,
    geom GEOMETRY(Point, 4326),
    record_creation_time TIMESTAMP NOT NULL DEFAULT now(),
    CONSTRAINT unique_city_country UNIQUE (city, country)
);
```

Key components:
- `latitude` and `longitude`: Store the coordinates as floating-point numbers
- `geom`: PostGIS geometry column that stores the point data in the WGS84 coordinate system (SRID 4326)
- `unique_city_country`: Constraint to ensure each city/country combination is unique

### Trigger Function

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

### Spatial Index

A GiST (Generalized Search Tree) index is created on the `geom` column to optimize spatial queries:

```sql
CREATE INDEX idx_locations_geom ON "Locations" USING GIST(geom);
```

## Key GIS Functions

The following PostGIS functions are used in our application:

### ST_MakePoint

Creates a point geometry from longitude and latitude coordinates:

```sql
ST_MakePoint(longitude, latitude)
```

### ST_SetSRID

Sets the Spatial Reference Identifier (SRID) for a geometry:

```sql
ST_SetSRID(geometry, srid)
```

We use SRID 4326, which corresponds to the WGS84 coordinate system used by GPS.

### ST_DWithin

Finds points within a specified distance:

```sql
ST_DWithin(geography1, geography2, distance_in_meters)
```

Note: We cast geometries to geography type (`::geography`) to ensure distance calculations are in meters rather than coordinate system units.

### ST_Distance

Calculates the distance between two points:

```sql
ST_Distance(geography1, geography2)
```

### ST_Transform

Transforms geometries from one coordinate system to another:

```sql
ST_Transform(geometry, target_srid)
```

## Geospatial Queries

### Radius Search

To find jobs within a specific radius of a location:

```sql
SELECT j.*
FROM "Jobs" j
JOIN "Locations" l ON j.location_id = l.location_id
WHERE ST_DWithin(
    l.geom::geography,
    ST_SetSRID(ST_MakePoint($longitude, $latitude), 4326)::geography,
    $radius_in_meters
);
```

### Distance Calculation

To calculate the distance between a job location and a user location:

```sql
SELECT 
    j.*,
    ST_Distance(
        l.geom::geography,
        ST_SetSRID(ST_MakePoint($longitude, $latitude), 4326)::geography
    ) AS distance_in_meters
FROM "Jobs" j
JOIN "Locations" l ON j.location_id = l.location_id
ORDER BY distance_in_meters;
```

## Performance Optimization

### Index Usage

Ensure that spatial queries are using the GiST index by examining query plans:

```sql
EXPLAIN ANALYZE
SELECT COUNT(*) FROM "Locations" 
WHERE ST_DWithin(
    geom::geography,
    ST_SetSRID(ST_MakePoint(-74.0060, 40.7128), 4326)::geography,
    5000
);
```

The query plan should show "Index Scan using idx_locations_geom on Locations".

### Geography vs. Geometry

- Use `geometry` type for storage (more compact)
- Cast to `geography` type for distance calculations (more accurate)
- Example: `geom::geography` in queries

### Limiting Result Sets

Always limit the number of results returned by spatial queries, especially when combined with other filtering criteria:

```sql
SELECT j.*
FROM "Jobs" j
JOIN "Locations" l ON j.location_id = l.location_id
WHERE ST_DWithin(
    l.geom::geography,
    ST_SetSRID(ST_MakePoint($longitude, $latitude), 4326)::geography,
    $radius_in_meters
)
LIMIT 100;
```

## Vector Search Integration

Our implementation combines geospatial filtering with vector similarity search for job matching.

### Combined Query Example

```sql
SELECT 
    j.id,
    j.title,
    j.description,
    j.embedding <=> $embedding::vector AS semantic_score,
    ST_Distance(
        l.geom::geography,
        ST_SetSRID(ST_MakePoint($longitude, $latitude), 4326)::geography
    ) AS distance_in_meters
FROM "Jobs" j
JOIN "Locations" l ON j.location_id = l.location_id
WHERE ST_DWithin(
    l.geom::geography,
    ST_SetSRID(ST_MakePoint($longitude, $latitude), 4326)::geography,
    $radius_in_meters
)
ORDER BY semantic_score
LIMIT 50;
```

### Weighted Scoring

To combine semantic and geographic relevance:

```sql
SELECT 
    j.id,
    j.title,
    (j.embedding <=> $embedding::vector) * 0.7 + 
    (ST_Distance(
        l.geom::geography,
        ST_SetSRID(ST_MakePoint($longitude, $latitude), 4326)::geography
    ) / $radius_in_meters) * 0.3 AS combined_score
FROM "Jobs" j
JOIN "Locations" l ON j.location_id = l.location_id
WHERE ST_DWithin(
    l.geom::geography,
    ST_SetSRID(ST_MakePoint($longitude, $latitude), 4326)::geography,
    $radius_in_meters
)
ORDER BY combined_score
LIMIT 50;
```

## Maintenance and Monitoring

### Verifying PostGIS Setup

Use the `verify_postgis.py` script to check that PostGIS is properly configured:

```bash
python -m app.scripts.verify_postgis
```

### Analyzing GIS Function Usage

Use the `analyze_gis_functions.py` script to identify which PostGIS functions are being used and potential optimizations:

```bash
python -m app.scripts.analyze_gis_functions
```

### Index Maintenance

Regularly rebuild the spatial index to maintain performance:

```sql
REINDEX INDEX idx_locations_geom;
```

### Monitoring Query Performance

Monitor the performance of spatial queries using pg_stat_statements:

```sql
SELECT 
    query,
    calls,
    total_exec_time / calls AS avg_exec_time_ms,
    rows / calls AS avg_rows
FROM pg_stat_statements
WHERE query LIKE '%ST_%'
ORDER BY total_exec_time DESC
LIMIT 10;
```

## Troubleshooting

### Common Issues

1. **Slow Queries**: 
   - Check if the spatial index is being used
   - Verify that the `geom` column is properly populated
   - Consider adding additional indexes on frequently filtered columns

2. **Incorrect Distance Calculations**:
   - Ensure geometries are cast to geography type for distance calculations
   - Verify that the correct SRID (4326) is being used

3. **Missing Geometry Data**:
   - Check that the trigger function is working correctly
   - Verify that latitude and longitude values are valid

### Diagnostic Queries

Check for null geometry values:

```sql
SELECT COUNT(*) FROM "Locations" WHERE geom IS NULL AND (latitude IS NOT NULL AND longitude IS NOT NULL);
```

Verify trigger function:

```sql
SELECT trigger_name, event_manipulation, action_statement 
FROM information_schema.triggers 
WHERE trigger_name = 'update_location_geom';
```

Check spatial index:

```sql
SELECT indexname, indexdef 
FROM pg_indexes 
WHERE indexname = 'idx_locations_geom';