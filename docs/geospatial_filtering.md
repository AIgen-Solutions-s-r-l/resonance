# Filtering Geospatial Data with PostGIS: A Comprehensive Guide

## Introduction

This document explains the logic and implementation of geospatial filtering using PostGIS with latitude and longitude coordinates. We'll explore different filtering techniques, optimization strategies, and practical examples with visual diagrams.

## Table of Contents

1. [PostGIS Fundamentals](#postgis-fundamentals)
2. [Coordinate Systems and Spatial References](#coordinate-systems)
3. [Creating Spatial Indexes](#spatial-indexes)
4. [Basic Point Filtering](#basic-point-filtering)
5. [Advanced Filtering Techniques](#advanced-filtering)
6. [Performance Optimization](#performance-optimization)
7. [Real-world Examples](#real-world-examples)

## PostGIS Fundamentals

PostGIS extends PostgreSQL with geospatial capabilities. Let's understand the core components:

```mermaid
graph TD
    A[PostgreSQL Database] --> B[PostGIS Extension]
    B --> C[Spatial Data Types]
    B --> D[Spatial Functions]
    B --> E[Spatial Operators]
    B --> F[Spatial Indexes]
    
    C --> G[Point]
    C --> H[LineString]
    C --> I[Polygon]
    C --> J[MultiPoint]
    C --> K[MultiLineString]
    C --> L[MultiPolygon]
    
    D --> M[ST_Distance]
    D --> N[ST_DWithin]
    D --> O[ST_Contains]
    D --> P[ST_Intersects]
```

## Coordinate Systems and Spatial References

```mermaid
graph LR
    A[Coordinate Systems] --> B[Geographic - WGS84/EPSG:4326]
    A --> C[Projected - Web Mercator/EPSG:3857]
    
    B --> D[Latitude/Longitude]
    C --> E[Meters]
    
    D --> F[ST_SetSRID]
    D --> G[ST_Transform]
```

## Creating Spatial Indexes

```mermaid
sequenceDiagram
    participant User
    participant PostgreSQL
    participant PostGIS
    
    User->>PostgreSQL: CREATE TABLE locations (id SERIAL, name TEXT, geom GEOMETRY(Point, 4326))
    User->>PostgreSQL: CREATE INDEX idx_locations_geom ON locations USING GIST(geom)
    User->>PostgreSQL: INSERT INTO locations VALUES (1, 'Eiffel Tower', ST_SetSRID(ST_MakePoint(2.2945, 48.8584), 4326))
    User->>PostgreSQL: SELECT * FROM locations WHERE ST_DWithin(geom, ST_SetSRID(ST_MakePoint(2.3, 48.86), 4326), 0.01)
    PostgreSQL->>PostGIS: Process spatial query using index
    PostGIS->>User: Return filtered results
```

## Basic Point Filtering

```mermaid
flowchart TD
    A[Start] --> B[Create Point from Lat/Long]
    B --> C{Choose Filter Type}
    C --> D[Distance-based]
    C --> E[Bounding Box]
    C --> F[Polygon Containment]
    
    D --> G["ST_DWithin(geom, point, distance)"]
    E --> H["geom && ST_MakeEnvelope(lon1, lat1, lon2, lat2, 4326)"]
    F --> I["ST_Contains(polygon, point)"]
    
    G --> J[Return Results]
    H --> J
    I --> J
```

## Advanced Filtering Techniques

### Radius Search

```mermaid
graph TD
    A[Input: Center Point + Radius] --> B[Convert to PostGIS Point]
    B --> C[Choose Distance Unit]
    C --> D[Degrees - Geographic]
    C --> E[Meters - Projected]
    
    D --> F["ST_DWithin(geom, center_point, radius_degrees)"]
    E --> G["ST_DWithin(ST_Transform(geom, 3857), ST_Transform(center_point, 3857), radius_meters)"]
    
    F --> H[Apply Filter]
    G --> H
    H --> I[Return Results]
```

### Polygon Filtering

```mermaid
sequenceDiagram
    participant Client
    participant Database
    
    Client->>Database: Define polygon from points
    Note right of Database: ST_MakePolygon(ST_MakeLine(ARRAY[point1, point2, ...]))
    Client->>Database: Query points inside polygon
    Note right of Database: SELECT * FROM points WHERE ST_Contains(polygon, geom)
    Database->>Client: Return filtered points
```

## Performance Optimization

```mermaid
graph TD
    A[Performance Optimization] --> B[Spatial Indexing]
    A --> C[Query Structure]
    A --> D[Coordinate System Choice]
    
    B --> E[GiST Index]
    B --> F[BRIN Index for Large Datasets]
    
    C --> G[Filter by Bounding Box First]
    C --> H[Then Apply Exact Filters]
    
    D --> I[Use Appropriate SRID]
    D --> J[Consider Transformations]
    
    G --> K["geom && ST_MakeEnvelope(...)"]
    H --> L["AND ST_DWithin(...)"]
```

## Real-world Examples

### Finding Nearby Points of Interest

```sql
-- Create a spatial table
CREATE TABLE pois (
    id SERIAL PRIMARY KEY,
    name TEXT,
    category TEXT,
    geom GEOMETRY(Point, 4326)
);

-- Add spatial index
CREATE INDEX idx_pois_geom ON pois USING GIST(geom);

-- Insert some data
INSERT INTO pois (name, category, geom) VALUES
    ('Eiffel Tower', 'landmark', ST_SetSRID(ST_MakePoint(2.2945, 48.8584), 4326)),
    ('Louvre Museum', 'museum', ST_SetSRID(ST_MakePoint(2.3376, 48.8606), 4326)),
    ('Notre-Dame', 'religious', ST_SetSRID(ST_MakePoint(2.3499, 48.8530), 4326));

-- Find POIs within 2km of a point
SELECT name, category, 
       ST_Distance(
           ST_Transform(geom, 3857),
           ST_Transform(ST_SetSRID(ST_MakePoint(2.3, 48.86), 4326), 3857)
       ) AS distance_meters
FROM pois
WHERE ST_DWithin(
    ST_Transform(geom, 3857),
    ST_Transform(ST_SetSRID(ST_MakePoint(2.3, 48.86), 4326), 3857),
    2000
)
ORDER BY distance_meters;
```

```mermaid
sequenceDiagram
    participant User
    participant Database
    
    User->>Database: Define current location (lat/long)
    User->>Database: Specify search radius (2km)
    Database->>Database: Transform coordinates to projected system
    Database->>Database: Apply spatial index for efficient filtering
    Database->>Database: Calculate distances
    Database->>User: Return sorted POIs by distance
```

### Filtering Points Within Administrative Boundaries

```mermaid
graph TD
    A[Start] --> B[Load Administrative Boundaries]
    B --> C[Convert User Coordinates to Point]
    C --> D[Query Points Within Boundary]
    D --> E["SELECT * FROM points WHERE ST_Contains((SELECT geom FROM boundaries WHERE name='District'), points.geom)"]
    E --> F[Return Filtered Results]
```

## Conclusion

This guide demonstrates the power and flexibility of PostGIS for geospatial filtering using latitude and longitude coordinates. By leveraging spatial indexes and appropriate query techniques, you can efficiently filter and analyze location data for various applications.

## Implementation in Our Project

In our matching service, we've implemented geospatial filtering using PostGIS to find job listings within a specified radius of a location. The implementation:

1. Uses the `ST_DWithin` function to find jobs within a radius of a given point
2. Accepts latitude, longitude, and radius parameters from the frontend
3. Uses a default radius of 50 kilometers if no radius is specified
4. Optimizes performance with spatial indices
5. Handles both kilometers (radius_km) and meters (radius) units, with meters taking precedence

The core of our implementation is in the `_build_location_filters` method in the `JobQueryBuilder` class, which constructs the SQL query with the appropriate PostGIS functions.