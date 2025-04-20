"""Add PostGIS support and update schema

Revision ID: 20250421_postgis
Revises: 8f156762c22b
Create Date: 2025-04-21 00:12:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text
from pgvector.sqlalchemy.vector import VECTOR

# revision identifiers, used by Alembic.
revision: str = "20250421_postgis"
down_revision: Union[str, None] = "8f156762c22b"  # Updated to match current DB version
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # This migration is designed to be idempotent - it will check if elements
    # already exist before creating them
    
    # Check and enable required extensions
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    
    # Check if pg_diskann extension exists before trying to create it
    op.execute("""
    DO $$
    BEGIN
        IF NOT EXISTS (
            SELECT 1 FROM pg_extension WHERE extname = 'pg_diskann'
        ) THEN
            CREATE EXTENSION pg_diskann;
        END IF;
    EXCEPTION
        WHEN OTHERS THEN
            RAISE NOTICE 'Could not create pg_diskann extension: %', SQLERRM;
    END $$;
    """)
    
    # Check if geom column exists before adding it
    op.execute("""
    DO $$
    BEGIN
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_name = 'Locations' AND column_name = 'geom'
        ) THEN
            ALTER TABLE "Locations" ADD COLUMN geom geometry(Point, 4326);
        END IF;
    END $$;
    """)
    
    # Create or replace trigger function
    op.execute("""
    CREATE OR REPLACE FUNCTION update_geom_column()
    RETURNS TRIGGER AS $$
    BEGIN
        IF NEW.latitude IS NOT NULL AND NEW.longitude IS NOT NULL THEN
            NEW.geom = ST_SetSRID(ST_MakePoint(NEW.longitude, NEW.latitude), 4326);
        END IF;
        RETURN NEW;
    END;
    $$ LANGUAGE plpgsql;
    """)
    
    # Check if trigger exists before creating it
    op.execute("""
    DO $$
    BEGIN
        IF NOT EXISTS (
            SELECT 1 FROM pg_trigger
            WHERE tgname = 'update_location_geom'
            AND tgrelid = 'Locations'::regclass
        ) THEN
            CREATE TRIGGER update_location_geom
            BEFORE INSERT OR UPDATE ON "Locations"
            FOR EACH ROW
            EXECUTE FUNCTION update_geom_column();
        END IF;
    END $$;
    """)
    
    # Update existing locations to populate the geom column
    op.execute("""
    UPDATE "Locations"
    SET geom = ST_SetSRID(ST_MakePoint(longitude, latitude), 4326)
    WHERE latitude IS NOT NULL AND longitude IS NOT NULL AND geom IS NULL;
    """)
    
    # Check if spatial index exists before creating it
    op.execute("""
    DO $$
    BEGIN
        IF NOT EXISTS (
            SELECT 1 FROM pg_indexes
            WHERE indexname = 'idx_locations_geom'
        ) THEN
            CREATE INDEX idx_locations_geom ON "Locations" USING GIST(geom);
        END IF;
    END $$;
    """)
    
    # Check if sparse_embeddings column exists before adding it
    op.execute("""
    DO $$
    BEGIN
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_name = 'Jobs' AND column_name = 'sparse_embeddings'
        ) THEN
            ALTER TABLE "Jobs" ADD COLUMN sparse_embeddings vector;
        END IF;
    END $$;
    """)
    
    # Check if cluster_id column exists before adding it
    op.execute("""
    DO $$
    BEGIN
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_name = 'Jobs' AND column_name = 'cluster_id'
        ) THEN
            ALTER TABLE "Jobs" ADD COLUMN cluster_id integer;
        END IF;
    END $$;
    """)
    
    # Check if index exists before creating it
    op.execute("""
    DO $$
    BEGIN
        IF NOT EXISTS (
            SELECT 1 FROM pg_indexes
            WHERE indexname = 'ix_jobs_cluster_id'
        ) THEN
            CREATE INDEX ix_jobs_cluster_id ON "Jobs" (cluster_id);
        END IF;
    END $$;
    """)


def downgrade() -> None:
    # This is a non-destructive downgrade that only removes elements
    # that were explicitly added by this migration
    
    # We don't attempt to drop extensions as they may be used by other parts of the system
    
    # Check if indexes exist before dropping them
    op.execute("""
    DO $$
    BEGIN
        IF EXISTS (
            SELECT 1 FROM pg_indexes
            WHERE indexname = 'ix_jobs_cluster_id'
        ) THEN
            DROP INDEX ix_jobs_cluster_id;
        END IF;
    END $$;
    """)
    
    # We don't drop the spatial index as it may be critical for application functionality
    
    # We don't drop columns or triggers as they may contain important data and functionality