"""Add PostGIS support and update schema

Revision ID: 20250421_postgis
Revises: 3c2fdab096e8
Create Date: 2025-04-21 00:06:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text
from pgvector.sqlalchemy.vector import VECTOR

# revision identifiers, used by Alembic.
revision: str = "20250421_postgis"
down_revision: Union[str, None] = "3c2fdab096e8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Enable PostGIS extension
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")
    
    # Add geometry column to Locations table
    op.execute("""
    ALTER TABLE "Locations" 
    ADD COLUMN IF NOT EXISTS geom geometry(Point, 4326)
    """)
    
    # Create trigger function to automatically update geometry column
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
    
    # Create trigger on Locations table
    op.execute("""
    DROP TRIGGER IF EXISTS update_location_geom ON "Locations";
    CREATE TRIGGER update_location_geom
    BEFORE INSERT OR UPDATE ON "Locations"
    FOR EACH ROW
    EXECUTE FUNCTION update_geom_column();
    """)
    
    # Update existing locations to populate the geom column
    op.execute("""
    UPDATE "Locations"
    SET geom = ST_SetSRID(ST_MakePoint(longitude, latitude), 4326)
    WHERE latitude IS NOT NULL AND longitude IS NOT NULL AND geom IS NULL;
    """)
    
    # Create GiST index on geom column for spatial queries
    op.execute("""
    CREATE INDEX IF NOT EXISTS idx_locations_geom ON "Locations" USING GIST(geom);
    """)
    
    # Add sparse_embeddings and cluster_id columns to Jobs table
    op.add_column('Jobs', sa.Column('sparse_embeddings', VECTOR(), nullable=True))
    op.add_column('Jobs', sa.Column('cluster_id', sa.Integer(), nullable=True))
    
    # Create index on cluster_id for faster filtering
    op.create_index(op.f('ix_jobs_cluster_id'), 'Jobs', ['cluster_id'], unique=False)


def downgrade() -> None:
    # Remove indexes
    op.drop_index(op.f('ix_jobs_cluster_id'), table_name='Jobs')
    op.execute("DROP INDEX IF EXISTS idx_locations_geom")
    
    # Remove trigger
    op.execute("DROP TRIGGER IF EXISTS update_location_geom ON \"Locations\"")
    op.execute("DROP FUNCTION IF EXISTS update_geom_column()")
    
    # Remove columns
    op.drop_column('Jobs', 'cluster_id')
    op.drop_column('Jobs', 'sparse_embeddings')
    op.execute("ALTER TABLE \"Locations\" DROP COLUMN IF EXISTS geom")
    
    # Note: We don't drop the PostGIS extension in downgrade as it might be used by other tables