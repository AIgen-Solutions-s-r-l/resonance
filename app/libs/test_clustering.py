import psycopg
import plotly.express as px
import pandas as pd
from job_clustering import JobClustering, ClusteringConfig


def visualize_clusters(job_ids, embeddings, cluster_labels):
    """Create and display a visualization of the clusters."""
    # Create DataFrame for plotting
    df = pd.DataFrame({
        'UMAP1': embeddings[:, 0],
        'UMAP2': embeddings[:, 1],
        'Cluster': [f'Cluster {c}' if c >= 0 else 'Noise' for c in cluster_labels],
        'job_id': job_ids
    })

    # Plot with Plotly
    fig = px.scatter(
        df,
        x='UMAP1',
        y='UMAP2',
        color='Cluster',
        hover_data=['job_id'],
        title='Job Clusters Visualization'
    )

    fig.show()


def main():
    try:
        # Connect to database
        conn = psycopg.connect(
            dbname="matching",
            user="testuser",
            password="testpassword",
            host="localhost",
            port=5432
        )

        # Initialize clustering with custom config if needed
        config = ClusteringConfig(
            umap_n_components=2,  # Ensure 2D for visualization
            umap_n_neighbors=15,
            umap_min_dist=0.1,
            hdbscan_min_cluster_size=5,
            hdbscan_min_samples=3
        )

        clustering = JobClustering(conn, config)

        # Get data and perform clustering
        job_ids, embeddings = clustering.get_embeddings_for_clustering()
        cluster_labels = clustering.perform_clustering(embeddings)

        # Visualize the results
        visualize_clusters(job_ids, embeddings, cluster_labels)

        # Save clusters to database
        clustering.save_clusters(job_ids, cluster_labels)

    except Exception as e:
        print(f"Error during clustering: {str(e)}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
