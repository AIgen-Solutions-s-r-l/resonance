import psycopg
from psycopg.sql import SQL
from loguru import logger
import sys
from job_clustering import JobClustering, ClusteringConfig

# Set up logging
logger.remove()
logger.add(
    sys.stderr, format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}")


def add_cluster_column(conn):
    """Explicitly add cluster_id column to Jobs table"""
    try:
        with conn.cursor() as cursor:
            # First check if column exists
            cursor.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'Jobs' 
                AND column_name = 'cluster_id';
            """)

            if not cursor.fetchone():
                # Add the column if it doesn't exist
                cursor.execute(SQL("""
                    ALTER TABLE "Jobs"
                    ADD COLUMN cluster_id INTEGER;
                """))
                conn.commit()
                logger.info(
                    "Successfully added cluster_id column to Jobs table")
            else:
                logger.info("cluster_id column already exists")

            # Verify the column was added
            cursor.execute("""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_name = 'Jobs' 
                AND column_name = 'cluster_id';
            """)
            result = cursor.fetchone()
            if result:
                logger.info(f"Verified column: {
                            result[0]} with type {result[1]}")
            else:
                raise Exception("Failed to verify cluster_id column")

    except Exception as e:
        logger.error(f"Error adding cluster column: {str(e)}")
        raise


def main():
    """Add column and run clustering"""
    try:
        # Connect to database
        conn = psycopg.connect(
            dbname="matching",
            user="testuser",
            password="testpassword",
            host="localhost",
            port=5432
        )
        logger.info("Connected to database")

        # Add cluster_id column
        add_cluster_column(conn)

        # Initialize and run clustering
        config = ClusteringConfig(
            umap_n_components=2,
            umap_n_neighbors=15,
            umap_min_dist=0.1,
            hdbscan_min_cluster_size=5,
            hdbscan_min_samples=3
        )

        clustering = JobClustering(conn, config)
        job_ids, embeddings = clustering.get_embeddings_for_clustering()
        cluster_labels = clustering.perform_clustering(embeddings)
        clustering.save_clusters(job_ids, cluster_labels)

        # Verify some rows were updated
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT COUNT(*) 
                FROM "Jobs" 
                WHERE cluster_id IS NOT NULL;
            """)
            count = cursor.fetchone()[0]
            logger.info(f"Number of jobs with cluster assignments: {count}")

        logger.info("Clustering completed successfully")

    except Exception as e:
        logger.error(f"Error during clustering: {str(e)}")
        raise
    finally:
        if 'conn' in locals():
            conn.close()
            logger.info("Database connection closed")


if __name__ == "__main__":
    main()
