"""
Skill Graph for Knowledge Graph Operations.

Provides graph operations and integration with PyTorch Geometric
for GNN-based skill embedding enrichment.
"""

from typing import List, Dict, Set, Optional, Tuple, Any
from dataclasses import dataclass
import numpy as np

from app.log.logging import logger
from app.ml.knowledge_graph.taxonomy import SkillTaxonomy, Skill, SkillRelation, RelationType
from app.ml.knowledge_graph.skill_extractor import ExtractedSkill

# Check if torch_geometric is available
try:
    import torch
    from torch_geometric.data import Data, HeteroData
    TORCH_GEOMETRIC_AVAILABLE = True
except ImportError:
    TORCH_GEOMETRIC_AVAILABLE = False
    logger.warning("torch_geometric not available. GNN features will be limited.")


@dataclass
class GraphData:
    """Container for graph data in tensor format."""
    node_features: Any  # torch.Tensor or np.ndarray
    edge_index: Any     # torch.Tensor or np.ndarray
    edge_types: List[int]
    edge_weights: List[float]
    node_ids: List[str]
    id_to_idx: Dict[str, int]


class SkillGraph:
    """
    Skill Knowledge Graph with PyTorch Geometric integration.

    Provides:
    - Graph construction from taxonomy
    - Node feature management
    - Conversion to PyG format for GNN
    - Subgraph extraction
    """

    def __init__(
        self,
        taxonomy: Optional[SkillTaxonomy] = None,
        embedding_dim: int = 256,
    ):
        """
        Initialize the skill graph.

        Args:
            taxonomy: Skill taxonomy to build graph from
            embedding_dim: Dimension for node embeddings
        """
        self.taxonomy = taxonomy or SkillTaxonomy()
        self.embedding_dim = embedding_dim

        # Node embeddings (initialized randomly, updated by GNN)
        self.node_embeddings: Dict[str, np.ndarray] = {}

        # Build graph
        self._build_graph()

        logger.info(
            "SkillGraph initialized",
            nodes=len(self.node_ids),
            edges=len(self.edges),
            embedding_dim=embedding_dim,
        )

    def _build_graph(self):
        """Build graph structure from taxonomy."""
        # Create node list
        self.node_ids = list(self.taxonomy.skills.keys())
        self.id_to_idx = {nid: idx for idx, nid in enumerate(self.node_ids)}

        # Initialize random embeddings
        for node_id in self.node_ids:
            self.node_embeddings[node_id] = np.random.randn(self.embedding_dim).astype(np.float32)
            # Normalize
            self.node_embeddings[node_id] /= np.linalg.norm(self.node_embeddings[node_id])

        # Build edge list
        self.edges: List[Tuple[int, int, int, float]] = []  # (src, dst, type, weight)
        self.edge_type_map = {rt: i for i, rt in enumerate(RelationType)}

        for relation in self.taxonomy.relations:
            if relation.source_id in self.id_to_idx and relation.target_id in self.id_to_idx:
                src_idx = self.id_to_idx[relation.source_id]
                dst_idx = self.id_to_idx[relation.target_id]
                edge_type = self.edge_type_map[relation.relation_type]

                self.edges.append((src_idx, dst_idx, edge_type, relation.weight))

                # Add reverse edge for undirected relations
                if relation.relation_type in [RelationType.RELATED_TO, RelationType.ALTERNATIVE_TO, RelationType.USED_WITH]:
                    self.edges.append((dst_idx, src_idx, edge_type, relation.weight))

    def get_node_features(self) -> np.ndarray:
        """Get node features as numpy array."""
        features = np.zeros((len(self.node_ids), self.embedding_dim), dtype=np.float32)
        for node_id, idx in self.id_to_idx.items():
            features[idx] = self.node_embeddings[node_id]
        return features

    def get_edge_index(self) -> np.ndarray:
        """Get edge indices as numpy array [2, num_edges]."""
        if not self.edges:
            return np.zeros((2, 0), dtype=np.int64)

        src = [e[0] for e in self.edges]
        dst = [e[1] for e in self.edges]
        return np.array([src, dst], dtype=np.int64)

    def get_edge_weights(self) -> np.ndarray:
        """Get edge weights as numpy array."""
        return np.array([e[3] for e in self.edges], dtype=np.float32)

    def get_edge_types(self) -> np.ndarray:
        """Get edge types as numpy array."""
        return np.array([e[2] for e in self.edges], dtype=np.int64)

    def to_pyg_data(self) -> "Data":
        """
        Convert to PyTorch Geometric Data object.

        Returns:
            PyG Data object
        """
        if not TORCH_GEOMETRIC_AVAILABLE:
            raise ImportError("torch_geometric required for to_pyg_data()")

        node_features = torch.tensor(self.get_node_features(), dtype=torch.float)
        edge_index = torch.tensor(self.get_edge_index(), dtype=torch.long)
        edge_weight = torch.tensor(self.get_edge_weights(), dtype=torch.float)
        edge_type = torch.tensor(self.get_edge_types(), dtype=torch.long)

        return Data(
            x=node_features,
            edge_index=edge_index,
            edge_weight=edge_weight,
            edge_type=edge_type,
            num_nodes=len(self.node_ids),
        )

    def update_embeddings(self, embeddings: np.ndarray) -> None:
        """
        Update node embeddings (e.g., from GNN output).

        Args:
            embeddings: New embeddings [num_nodes, embedding_dim]
        """
        if embeddings.shape[0] != len(self.node_ids):
            raise ValueError(f"Expected {len(self.node_ids)} embeddings, got {embeddings.shape[0]}")

        for node_id, idx in self.id_to_idx.items():
            self.node_embeddings[node_id] = embeddings[idx]

    def get_skill_embedding(self, skill_id: str) -> Optional[np.ndarray]:
        """Get embedding for a skill."""
        return self.node_embeddings.get(skill_id)

    def get_skills_embedding(self, skill_ids: List[str]) -> np.ndarray:
        """
        Get aggregated embedding for multiple skills.

        Args:
            skill_ids: List of skill IDs

        Returns:
            Mean embedding of the skills
        """
        embeddings = []
        for sid in skill_ids:
            if sid in self.node_embeddings:
                embeddings.append(self.node_embeddings[sid])

        if not embeddings:
            return np.zeros(self.embedding_dim, dtype=np.float32)

        return np.mean(embeddings, axis=0)

    def extract_subgraph(
        self,
        skill_ids: List[str],
        num_hops: int = 1,
    ) -> "SkillGraph":
        """
        Extract a subgraph around the given skills.

        Args:
            skill_ids: Seed skill IDs
            num_hops: Number of hops to include

        Returns:
            New SkillGraph with the subgraph
        """
        # Find all nodes within num_hops
        included_nodes: Set[str] = set(skill_ids)
        frontier = set(skill_ids)

        for _ in range(num_hops):
            new_frontier = set()
            for node_id in frontier:
                related = self.taxonomy.get_related_skills(node_id, max_depth=1)
                for skill, _ in related:
                    if skill.id not in included_nodes:
                        new_frontier.add(skill.id)
                        included_nodes.add(skill.id)
            frontier = new_frontier

        # Create new taxonomy with subset
        from app.ml.knowledge_graph.taxonomy import SkillTaxonomy

        sub_taxonomy = SkillTaxonomy.__new__(SkillTaxonomy)
        sub_taxonomy.skills = {
            sid: self.taxonomy.skills[sid]
            for sid in included_nodes
            if sid in self.taxonomy.skills
        }
        sub_taxonomy.relations = [
            r for r in self.taxonomy.relations
            if r.source_id in included_nodes and r.target_id in included_nodes
        ]
        sub_taxonomy._name_to_id = {}
        sub_taxonomy._alias_to_id = {}
        sub_taxonomy._category_index = {}
        sub_taxonomy._adjacency = {}

        for skill in sub_taxonomy.skills.values():
            sub_taxonomy._name_to_id[skill.name.lower()] = skill.id
            for alias in skill.aliases:
                sub_taxonomy._alias_to_id[alias.lower()] = skill.id

        for relation in sub_taxonomy.relations:
            if relation.source_id not in sub_taxonomy._adjacency:
                sub_taxonomy._adjacency[relation.source_id] = []
            sub_taxonomy._adjacency[relation.source_id].append(
                (relation.target_id, relation.relation_type, relation.weight)
            )

        # Create subgraph
        subgraph = SkillGraph(
            taxonomy=sub_taxonomy,
            embedding_dim=self.embedding_dim,
        )

        # Copy embeddings
        for node_id in subgraph.node_ids:
            if node_id in self.node_embeddings:
                subgraph.node_embeddings[node_id] = self.node_embeddings[node_id].copy()

        return subgraph

    def compute_graph_features(
        self,
        extracted_skills: List[ExtractedSkill],
    ) -> Dict[str, Any]:
        """
        Compute graph-based features for extracted skills.

        Args:
            extracted_skills: Skills extracted from text

        Returns:
            Dictionary with graph features
        """
        skill_ids = [s.canonical_name for s in extracted_skills if s.canonical_name in self.id_to_idx]

        if not skill_ids:
            return {
                "num_skills": 0,
                "skill_embedding": np.zeros(self.embedding_dim),
                "graph_density": 0.0,
                "avg_degree": 0.0,
            }

        # Get aggregated embedding
        skill_embedding = self.get_skills_embedding(skill_ids)

        # Compute subgraph statistics
        subgraph = self.extract_subgraph(skill_ids, num_hops=1)

        num_nodes = len(subgraph.node_ids)
        num_edges = len(subgraph.edges) // 2  # Undirected

        graph_density = 0.0
        if num_nodes > 1:
            max_edges = num_nodes * (num_nodes - 1) / 2
            graph_density = num_edges / max_edges if max_edges > 0 else 0

        avg_degree = 2 * num_edges / num_nodes if num_nodes > 0 else 0

        return {
            "num_skills": len(skill_ids),
            "skill_embedding": skill_embedding,
            "graph_density": graph_density,
            "avg_degree": avg_degree,
            "matched_skills": skill_ids,
        }

    def get_statistics(self) -> Dict[str, Any]:
        """Get graph statistics."""
        return {
            "num_nodes": len(self.node_ids),
            "num_edges": len(self.edges),
            "num_relation_types": len(RelationType),
            "embedding_dim": self.embedding_dim,
            "avg_degree": len(self.edges) / len(self.node_ids) if self.node_ids else 0,
        }
