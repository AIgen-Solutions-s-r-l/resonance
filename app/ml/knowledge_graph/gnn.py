"""
Graph Neural Network for Skill Embedding Enrichment.

Uses GNN to propagate information through the skill graph,
enriching skill embeddings with relational information.
"""

from typing import Optional, List, Dict, Any, Tuple
import numpy as np

from app.log.logging import logger
from app.ml.config import ml_config

# Check if torch and torch_geometric are available
try:
    import torch
    import torch.nn as nn
    import torch.nn.functional as F
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False

try:
    from torch_geometric.nn import GCNConv, GATConv, SAGEConv, MessagePassing
    from torch_geometric.data import Data
    TORCH_GEOMETRIC_AVAILABLE = True
except ImportError:
    TORCH_GEOMETRIC_AVAILABLE = False


if TORCH_AVAILABLE and TORCH_GEOMETRIC_AVAILABLE:

    class SkillGNN(nn.Module):
        """
        Graph Neural Network for skill embedding enrichment.

        Supports multiple GNN architectures:
        - GCN: Graph Convolutional Networks
        - GAT: Graph Attention Networks
        - SAGE: GraphSAGE

        Reference architectures:
        - LinkSAGE (LinkedIn): Uses SAGE for job marketplace graph
        - HRGraph: Uses GCN/GAT for HR knowledge graphs
        """

        def __init__(
            self,
            input_dim: int = 256,
            hidden_dim: int = 256,
            output_dim: int = 256,
            num_layers: int = 2,
            gnn_type: str = "gat",
            heads: int = 4,
            dropout: float = 0.2,
            use_edge_weight: bool = True,
        ):
            """
            Initialize the Skill GNN.

            Args:
                input_dim: Input feature dimension
                hidden_dim: Hidden layer dimension
                output_dim: Output embedding dimension
                num_layers: Number of GNN layers
                gnn_type: Type of GNN ("gcn", "gat", "sage")
                heads: Number of attention heads (for GAT)
                dropout: Dropout rate
                use_edge_weight: Whether to use edge weights
            """
            super().__init__()

            self.input_dim = input_dim
            self.hidden_dim = hidden_dim
            self.output_dim = output_dim
            self.num_layers = num_layers
            self.gnn_type = gnn_type
            self.dropout = dropout
            self.use_edge_weight = use_edge_weight

            # Build layers
            self.convs = nn.ModuleList()
            self.norms = nn.ModuleList()

            for i in range(num_layers):
                in_channels = input_dim if i == 0 else hidden_dim
                out_channels = output_dim if i == num_layers - 1 else hidden_dim

                if gnn_type == "gcn":
                    self.convs.append(GCNConv(in_channels, out_channels))
                elif gnn_type == "gat":
                    # For GAT, output is out_channels * heads for hidden layers
                    if i < num_layers - 1:
                        self.convs.append(GATConv(in_channels, hidden_dim // heads, heads=heads))
                        out_channels = hidden_dim
                    else:
                        self.convs.append(GATConv(hidden_dim, output_dim, heads=1))
                elif gnn_type == "sage":
                    self.convs.append(SAGEConv(in_channels, out_channels))
                else:
                    raise ValueError(f"Unknown GNN type: {gnn_type}")

                self.norms.append(nn.LayerNorm(out_channels))

            logger.info(
                f"SkillGNN initialized: {gnn_type}",
                layers=num_layers,
                hidden_dim=hidden_dim,
                output_dim=output_dim,
            )

        def forward(
            self,
            x: torch.Tensor,
            edge_index: torch.Tensor,
            edge_weight: Optional[torch.Tensor] = None,
        ) -> torch.Tensor:
            """
            Forward pass through the GNN.

            Args:
                x: Node features [num_nodes, input_dim]
                edge_index: Edge indices [2, num_edges]
                edge_weight: Optional edge weights [num_edges]

            Returns:
                Enriched node embeddings [num_nodes, output_dim]
            """
            for i, (conv, norm) in enumerate(zip(self.convs, self.norms)):
                # Convolution
                if self.gnn_type == "gcn" and self.use_edge_weight and edge_weight is not None:
                    x = conv(x, edge_index, edge_weight)
                else:
                    x = conv(x, edge_index)

                # Normalization
                x = norm(x)

                # Activation (except last layer)
                if i < self.num_layers - 1:
                    x = F.relu(x)
                    x = F.dropout(x, p=self.dropout, training=self.training)

            return x

        def get_embeddings(
            self,
            data: Data,
            node_ids: Optional[List[int]] = None,
        ) -> torch.Tensor:
            """
            Get embeddings for specific nodes or all nodes.

            Args:
                data: PyG Data object
                node_ids: Optional list of node indices

            Returns:
                Node embeddings
            """
            self.eval()
            with torch.no_grad():
                all_embeddings = self.forward(
                    data.x,
                    data.edge_index,
                    data.edge_weight if hasattr(data, "edge_weight") else None,
                )

            if node_ids is not None:
                return all_embeddings[node_ids]
            return all_embeddings


    class GraphEnrichedEncoder(nn.Module):
        """
        Encoder that combines text embeddings with graph-enriched skill embeddings.

        Architecture:
        1. Text encoder produces base embedding
        2. Skill extractor identifies skills in text
        3. GNN produces skill embeddings from graph
        4. Fusion layer combines text + skill embeddings
        """

        def __init__(
            self,
            text_encoder: nn.Module,
            skill_gnn: SkillGNN,
            text_dim: int = 1024,
            skill_dim: int = 256,
            output_dim: int = 1024,
            fusion_type: str = "concat",
        ):
            """
            Initialize the graph-enriched encoder.

            Args:
                text_encoder: Pre-trained text encoder (e.g., BiEncoder)
                skill_gnn: Trained skill GNN
                text_dim: Dimension of text embeddings
                skill_dim: Dimension of skill embeddings
                output_dim: Final output dimension
                fusion_type: How to fuse embeddings ("concat", "add", "gate")
            """
            super().__init__()

            self.text_encoder = text_encoder
            self.skill_gnn = skill_gnn
            self.text_dim = text_dim
            self.skill_dim = skill_dim
            self.output_dim = output_dim
            self.fusion_type = fusion_type

            # Skill embedding projection
            self.skill_projection = nn.Linear(skill_dim, skill_dim)

            # Fusion layer
            if fusion_type == "concat":
                self.fusion = nn.Linear(text_dim + skill_dim, output_dim)
            elif fusion_type == "add":
                self.skill_to_text = nn.Linear(skill_dim, text_dim)
                self.fusion = nn.Linear(text_dim, output_dim)
            elif fusion_type == "gate":
                self.gate = nn.Sequential(
                    nn.Linear(text_dim + skill_dim, text_dim),
                    nn.Sigmoid(),
                )
                self.skill_transform = nn.Linear(skill_dim, text_dim)
                self.fusion = nn.Linear(text_dim, output_dim)
            else:
                raise ValueError(f"Unknown fusion type: {fusion_type}")

            # Output normalization
            self.output_norm = nn.LayerNorm(output_dim)

            logger.info(
                f"GraphEnrichedEncoder initialized",
                fusion_type=fusion_type,
                output_dim=output_dim,
            )

        def forward(
            self,
            text_embedding: torch.Tensor,
            skill_node_indices: List[List[int]],
            graph_data: Data,
        ) -> torch.Tensor:
            """
            Forward pass combining text and skill embeddings.

            Args:
                text_embedding: Text embeddings [batch_size, text_dim]
                skill_node_indices: List of skill node indices per sample
                graph_data: PyG Data with graph structure

            Returns:
                Enriched embeddings [batch_size, output_dim]
            """
            batch_size = text_embedding.size(0)
            device = text_embedding.device

            # Get all skill embeddings from GNN
            all_skill_embeddings = self.skill_gnn(
                graph_data.x.to(device),
                graph_data.edge_index.to(device),
                graph_data.edge_weight.to(device) if hasattr(graph_data, "edge_weight") else None,
            )

            # Aggregate skill embeddings for each sample
            skill_embeddings = torch.zeros(batch_size, self.skill_dim, device=device)

            for i, indices in enumerate(skill_node_indices):
                if indices:
                    sample_skills = all_skill_embeddings[indices]
                    # Mean pooling over skills
                    skill_embeddings[i] = sample_skills.mean(dim=0)

            # Project skill embeddings
            skill_embeddings = self.skill_projection(skill_embeddings)

            # Fusion
            if self.fusion_type == "concat":
                combined = torch.cat([text_embedding, skill_embeddings], dim=-1)
                output = self.fusion(combined)

            elif self.fusion_type == "add":
                skill_transformed = self.skill_to_text(skill_embeddings)
                combined = text_embedding + skill_transformed
                output = self.fusion(combined)

            elif self.fusion_type == "gate":
                combined_for_gate = torch.cat([text_embedding, skill_embeddings], dim=-1)
                gate_values = self.gate(combined_for_gate)

                skill_transformed = self.skill_transform(skill_embeddings)
                gated = text_embedding + gate_values * skill_transformed
                output = self.fusion(gated)

            # Normalize output
            output = self.output_norm(output)
            output = F.normalize(output, p=2, dim=-1)

            return output

        def encode(
            self,
            texts: List[str],
            skill_indices: List[List[int]],
            graph_data: Data,
            batch_size: int = 32,
        ) -> torch.Tensor:
            """
            Encode texts with skill enrichment.

            Args:
                texts: List of texts to encode
                skill_indices: Skill node indices per text
                graph_data: Skill graph data
                batch_size: Encoding batch size

            Returns:
                Enriched embeddings
            """
            device = next(self.parameters()).device
            self.eval()

            all_embeddings = []

            with torch.no_grad():
                for i in range(0, len(texts), batch_size):
                    batch_texts = texts[i:i + batch_size]
                    batch_skills = skill_indices[i:i + batch_size]

                    # Get text embeddings
                    text_emb = self.text_encoder.encode(batch_texts, device=device)

                    # Enrich with skills
                    enriched = self.forward(text_emb, batch_skills, graph_data)
                    all_embeddings.append(enriched.cpu())

            return torch.cat(all_embeddings, dim=0)


else:
    # Dummy classes when torch_geometric is not available

    class SkillGNN:
        """Placeholder for SkillGNN when torch_geometric is not available."""

        def __init__(self, *args, **kwargs):
            raise ImportError(
                "torch and torch_geometric are required for SkillGNN. "
                "Install with: pip install torch torch_geometric"
            )


    class GraphEnrichedEncoder:
        """Placeholder for GraphEnrichedEncoder when torch_geometric is not available."""

        def __init__(self, *args, **kwargs):
            raise ImportError(
                "torch and torch_geometric are required for GraphEnrichedEncoder. "
                "Install with: pip install torch torch_geometric"
            )
