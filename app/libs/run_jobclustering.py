import psycopg
import numpy as np
import plotly.express as px
import pandas as pd
from job_clustering import JobClustering, ClusteringConfig
from loguru import logger
import sys

# Set up logging
logger.remove()
logger.add(
    sys.stderr, format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}")


def main():
    """
    Main function to perform job clustering and add cluster_id to Jobs table.
    """
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

        # Initialize clustering with configuration
        config = ClusteringConfig(
            umap_n_components=2,
            umap_n_neighbors=15,
            umap_min_dist=0.1,
            hdbscan_min_cluster_size=5,
            hdbscan_min_samples=3
        )

        # Create clustering object and run pipeline
        clustering = JobClustering(conn, config)
        job_ids, embeddings = clustering.get_embeddings_for_clustering()
        cluster_labels = clustering.perform_clustering(embeddings)

        # Save clusters to Jobs table
        clustering.save_clusters(job_ids, cluster_labels)

        # Optional: Create visualization
        df = pd.DataFrame({
            'UMAP1': embeddings[:, 0],
            'UMAP2': embeddings[:, 1],
            'Cluster': [f'Cluster {c}' if c >= 0 else 'Noise' for c in cluster_labels],
            'Job_ID': job_ids
        })

        fig = px.scatter(
            df,
            x='UMAP1',
            y='UMAP2',
            color='Cluster',
            hover_data=['Job_ID'],
            title='Job Clusters'
        )
        fig.write_html("job_clusters.html")

        # Print summary
        unique_clusters = len(np.unique(cluster_labels[cluster_labels >= 0]))
        noise_points = sum(cluster_labels == -1)

        print("\nClustering Summary:")
        print(f"Total Jobs Processed: {len(job_ids)}")
        print(f"Number of Clusters: {unique_clusters}")
        print(f"Noise Points: {noise_points}")

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
