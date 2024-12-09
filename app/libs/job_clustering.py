from dataclasses import dataclass
import numpy as np
from umap import UMAP
from hdbscan import HDBSCAN
from psycopg import Connection
from psycopg.rows import Row
from psycopg.sql import SQL
from typing import List, Tuple
from loguru import logger


@dataclass
class ClusteringConfig:
    umap_n_components: int = 2
    umap_n_neighbors: int = 15
    umap_min_dist: float = 0.1
    hdbscan_min_cluster_size: int = 5
    hdbscan_min_samples: int = 3


class JobClustering:
    def __init__(self, db_connection: Connection, config: ClusteringConfig = ClusteringConfig()):
        self.conn = db_connection
        self.config = config

    def get_embeddings_for_clustering(self) -> Tuple[List[str], np.ndarray]:
        """Fetch embeddings and job IDs from database."""
        with self.conn.cursor() as cursor:
            query = SQL("""
                WITH normalized_embeddings AS (
                    SELECT 
                        job_id,
                        embedding
                    FROM "Jobs"
                    WHERE embedding IS NOT NULL
                )
                SELECT 
                    job_id,
                    string_to_array(
                        trim(both '[]' from embedding::text),
                        ','
                    )::float[] as embedding
                FROM normalized_embeddings;
            """)

            cursor.execute(query)
            results = cursor.fetchall()

            if not results:
                raise ValueError("No embeddings found in database")

            job_ids = [row[0] for row in results]
            embeddings = np.array([row[1] for row in results])

            if embeddings.size == 0:
                raise ValueError("Empty embeddings array")

            logger.info(f"Retrieved {len(job_ids)} embeddings for clustering")
            return job_ids, embeddings

    def perform_clustering(self, embeddings: np.ndarray) -> np.ndarray:
        """Apply UMAP dimensionality reduction and HDBSCAN clustering."""
        if embeddings.shape[0] < self.config.hdbscan_min_cluster_size:
            raise ValueError(
                f"Number of samples ({embeddings.shape[0]}) is less than "
                f"min_cluster_size ({self.config.hdbscan_min_cluster_size})"
            )

        try:
            umap_reducer = UMAP(
                n_components=self.config.umap_n_components,
                n_neighbors=self.config.umap_n_neighbors,
                min_dist=self.config.umap_min_dist,
                random_state=42
            )
            umap_embeddings = umap_reducer.fit_transform(embeddings)

            clusterer = HDBSCAN(
                min_cluster_size=self.config.hdbscan_min_cluster_size,
                min_samples=self.config.hdbscan_min_samples,
                metric='euclidean'
            )
            cluster_labels = clusterer.fit_predict(umap_embeddings)

            logger.info(
                f"Identified {len(np.unique(cluster_labels))} clusters")
            return cluster_labels
        except Exception as e:
            logger.error(f"Clustering failed: {str(e)}")
            raise

    def save_clusters(self, job_ids: List[str], cluster_labels: np.ndarray) -> None:
        """Save cluster assignments back to database."""
        with self.conn.cursor() as cursor:
            create_column_query = SQL("""
                DO $$ 
                BEGIN 
                    IF NOT EXISTS (
                        SELECT 1 
                        FROM information_schema.columns 
                        WHERE table_name='Jobs' AND column_name='cluster_id'
                    ) THEN 
                        ALTER TABLE "Jobs" ADD COLUMN cluster_id INTEGER;
                    END IF;
                END $$;
            """)
            cursor.execute(create_column_query)

            for job_id, cluster_label in zip(job_ids, cluster_labels):
                update_query = SQL("""
                    UPDATE "Jobs"
                    SET cluster_id = %s
                    WHERE job_id = %s;
                """)
                cursor.execute(update_query, (int(cluster_label), job_id))

            logger.info("Successfully saved cluster assignments to database")

    def run_clustering(self) -> None:
        """Execute complete clustering pipeline."""
        try:
            job_ids, embeddings = self.get_embeddings_for_clustering()
            cluster_labels = self.perform_clustering(embeddings)
            self.save_clusters(job_ids, cluster_labels)
        except Exception as e:
            logger.error(f"Clustering pipeline failed: {str(e)}")
            raise
