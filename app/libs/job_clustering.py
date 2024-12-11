from dataclasses import dataclass
import numpy as np
from umap import UMAP
from hdbscan import HDBSCAN
from psycopg import Connection
from psycopg.rows import Row
from psycopg.sql import SQL, Identifier
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
        try:
            cursor = self.conn.cursor()

            # Convert job_ids to integers since they're stored as integers in the database
            job_ids_int = [int(job_id) for job_id in job_ids]

            # Convert cluster_labels to integers
            cluster_labels_int = [int(label) if not np.isnan(
                label) else -1 for label in cluster_labels]

            update_query = SQL("""
                WITH updates AS (
                    UPDATE "Jobs" AS j
                    SET cluster_id = c.cluster_id
                    FROM (
                        SELECT UNNEST(%s::integer[]) as job_id,
                               UNNEST(%s::integer[]) as cluster_id
                    ) AS c
                    WHERE j.job_id = c.job_id
                    RETURNING j.job_id
                )
                SELECT COUNT(*) FROM updates;
            """)

            cursor.execute(update_query, (job_ids_int, cluster_labels_int))
            updated_count = cursor.fetchone()[0]

            # Verify the update
            verify_query = SQL("""
                SELECT COUNT(*) 
                FROM "Jobs" 
                WHERE cluster_id IS NOT NULL;
            """)
            cursor.execute(verify_query)
            total_clusters = cursor.fetchone()[0]

            logger.info(f"Updated {updated_count} rows out of {
                        len(job_ids)} jobs")
            logger.info(f"Total rows with cluster_id: {total_clusters}")

            self.conn.commit()
            logger.info(
                "Successfully committed cluster assignments to database")

        except Exception as e:
            self.conn.rollback()
            logger.error(f"Failed to save clusters: {str(e)}")
            raise
        finally:
            cursor.close()

    def run_clustering(self) -> None:
        """Execute complete clustering pipeline."""
        try:
            job_ids, embeddings = self.get_embeddings_for_clustering()
            cluster_labels = self.perform_clustering(embeddings)
            self.save_clusters(job_ids, cluster_labels)
        except Exception as e:
            logger.error(f"Clustering pipeline failed: {str(e)}")
            raise

    def save_clustering_model(self, model_path: str) -> None:
        """
        Save both UMAP and HDBSCAN models to disk using joblib.

        Args:
            model_path (str): Base path where models will be saved
                            (without extension)
        """
        from joblib import dump

        try:
            # Save UMAP model
            umap_path = f"{model_path}_umap.joblib"
            dump(self.umap_reducer, umap_path)

            # Save HDBSCAN model
            hdbscan_path = f"{model_path}_hdbscan.joblib"
            dump(self.clusterer, hdbscan_path)

            logger.info(f"Models saved successfully to {model_path}")

        except Exception as e:
            logger.error(f"Failed to save models: {str(e)}")
            raise
