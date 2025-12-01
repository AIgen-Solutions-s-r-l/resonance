<div align="center">

# Resonance

### Vector-powered talent matching that finds the signal in the noise

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-4169E1?style=for-the-badge&logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Redis](https://img.shields.io/badge/Redis-DC382D?style=for-the-badge&logo=redis&logoColor=white)](https://redis.io/)
[![License](https://img.shields.io/badge/License-Proprietary-red.svg?style=for-the-badge)](#license)

<br />

[Getting Started](#-quick-start) •
[Documentation](docs/README.md) •
[API Reference](#-api) •
[Contributing](#-contributing)

<br />

</div>

---

## What is Resonance?

Resonance is a high-performance semantic matching engine that connects talent with opportunity using 1024-dimensional vector embeddings. It goes beyond keyword matching to understand the true fit between candidates and positions.

```
Resume → Vector Embedding → Multi-Metric Similarity → Ranked Matches
```

<br />

## Architecture

```mermaid
flowchart TB
    subgraph Client
        A[API Request]
    end

    subgraph Gateway["API Layer"]
        B[FastAPI Router]
        C[JWT Auth]
    end

    subgraph Core["Matching Engine"]
        D[Vector Matcher]
        E[Query Builder]
        F[Similarity Searcher]
    end

    subgraph Storage["Data Layer"]
        G[(PostgreSQL<br/>pgvector)]
        H[(MongoDB<br/>Resumes)]
        I[(Redis<br/>Cache)]
    end

    A --> B
    B --> C
    C --> D
    D --> E
    D --> F
    E --> G
    F --> G
    D <--> H
    D <--> I

    style Gateway fill:#009688,color:#fff
    style Core fill:#3776AB,color:#fff
    style Storage fill:#4169E1,color:#fff
```

<br />

## How It Works

```mermaid
sequenceDiagram
    participant C as Client
    participant R as Resonance
    participant PG as PostgreSQL
    participant MG as MongoDB
    participant RD as Redis

    C->>R: GET /jobs/match
    R->>RD: Check cache
    alt Cache hit
        RD-->>R: Cached results
    else Cache miss
        R->>MG: Fetch resume embedding
        MG-->>R: 1024-dim vector
        R->>PG: Vector similarity search
        Note over R,PG: L2 + Cosine + Inner Product
        PG-->>R: Ranked candidates
        R->>RD: Store in cache
    end
    R-->>C: Matched jobs (scored & ranked)
```

<br />

## Resonance v2: ML Pipeline

Resonance v2 implements a **four-phase ML evolution** for state-of-the-art matching accuracy:

```mermaid
flowchart LR
    subgraph "Stage 1: Retrieval"
        R[Resume] --> BE[Bi-Encoder<br/>Contrastive Learning]
        BE --> ANN[(pgvector<br/>Top-100)]
    end

    subgraph "Stage 2: Enrichment"
        ANN --> SKG[Skill Knowledge<br/>Graph + GNN]
    end

    subgraph "Stage 3: Reranking"
        SKG --> CE[Cross-Encoder<br/>Pairwise Scoring]
        CE --> TOP[Top-25]
    end

    subgraph "Stage 4: Explain"
        TOP --> EXP[Explainability<br/>Module]
        EXP --> OUT[Ranked Results<br/>+ Explanations]
    end

    style BE fill:#3776AB,color:#fff
    style SKG fill:#47A248,color:#fff
    style CE fill:#DC382D,color:#fff
    style EXP fill:#9333EA,color:#fff
```

### Pipeline Phases

| Phase | Component | Purpose | Improvement |
|-------|-----------|---------|-------------|
| **1** | Hard Negative Mining | Quality training data with challenging negatives | Foundation |
| **2** | Contrastive Learning | Domain-specific bi-encoder fine-tuning | +15-20% nDCG |
| **3** | Skill Knowledge Graph | Transitive skill relationships via GNN | +5-10% nDCG |
| **4** | Cross-Encoder Reranking | High-precision pairwise scoring | +5-10% nDCG |

### Score Fusion

```mermaid
pie showData
    title Final Score Composition
    "Cross-Encoder" : 50
    "Bi-Encoder" : 30
    "Skill Graph" : 20
```

| Component | Weight | What It Captures |
|-----------|--------|------------------|
| **Cross-Encoder** | 50% | Deep semantic match with cross-attention |
| **Bi-Encoder** | 30% | Efficient vector similarity |
| **Skill Graph** | 20% | Transitive skill relationships |

### Explainable Results

Every match includes human-readable explanations:

```json
{
  "score": 0.94,
  "explanation": {
    "highlights": [
      "Matches 5 required skills: Python, AWS, Docker",
      "Experience level (senior) meets requirements"
    ],
    "concerns": [
      "Missing 1 required skill: Kubernetes"
    ],
    "skills": {
      "matched": ["Python", "AWS", "Docker"],
      "missing": ["Kubernetes"],
      "related": [{"resume": "Docker", "job": "Kubernetes", "similarity": 0.72}]
    }
  }
}
```

<br />

## Similarity Scoring (v1)

The base vector matching combines three distance metrics:

```mermaid
pie showData
    title Base Similarity Weights
    "L2 Distance" : 40
    "Cosine Similarity" : 40
    "Inner Product" : 20
```

| Metric | Weight | Best For |
|--------|--------|----------|
| **L2 Distance** | 40% | Magnitude-sensitive matching |
| **Cosine Similarity** | 40% | Direction-based semantic alignment |
| **Inner Product** | 20% | Combined magnitude + direction |

<br />

## Quick Start

### Docker (Recommended)

```bash
# Clone and run
git clone https://github.com/AIgen-Solutions-s-r-l/resonance.git
cd resonance
docker-compose up -d

# Verify
curl http://localhost:8000/health
```

### Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env

# Run
uvicorn app.main:app --reload --port 8000
```

<br />

## API

### Get Matched Jobs

```bash
curl -X GET "http://localhost:8000/jobs/match?country=Germany&keywords=python" \
  -H "Authorization: Bearer $TOKEN"
```

<details>
<summary><b>Response</b></summary>

```json
{
  "jobs": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "title": "Senior Python Engineer",
      "company_name": "TechCorp",
      "score": 0.94,
      "location": "Berlin, Germany",
      "workplace_type": "Hybrid",
      "posted_date": "2025-01-15T10:00:00Z"
    }
  ],
  "total": 127,
  "cached": true
}
```
</details>

### Trigger New Matching

```bash
curl -X POST "http://localhost:8000/jobs/match" \
  -H "Authorization: Bearer $TOKEN"
```

<details>
<summary><b>Response</b></summary>

```json
{
  "task_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
  "status": "processing",
  "estimated_time_ms": 1500
}
```
</details>

### Query Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `keywords` | `string[]` | Required keywords in job title/description |
| `country` | `string` | Hard filter — excludes all jobs outside country |
| `city` | `string` | Soft filter — keeps remote jobs |
| `experience` | `string` | `Entry-level` \| `Mid-level` \| `Senior-level` \| `Executive-level` |
| `is_remote_only` | `bool` | Only remote positions |
| `latitude` | `float` | Center point for radius search |
| `longitude` | `float` | Center point for radius search |
| `radius_km` | `int` | Search radius in kilometers |
| `sort_type` | `string` | `RECOMMENDED` \| `DATE` |

<br />

## Tech Stack

<table>
<tr>
<td align="center" width="150">

**Runtime**

![Python](https://img.shields.io/badge/-Python-3776AB?style=flat-square&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/-FastAPI-009688?style=flat-square&logo=fastapi&logoColor=white)
![Uvicorn](https://img.shields.io/badge/-Uvicorn-499848?style=flat-square&logo=gunicorn&logoColor=white)

</td>
<td align="center" width="150">

**Data**

![PostgreSQL](https://img.shields.io/badge/-PostgreSQL-4169E1?style=flat-square&logo=postgresql&logoColor=white)
![MongoDB](https://img.shields.io/badge/-MongoDB-47A248?style=flat-square&logo=mongodb&logoColor=white)
![Redis](https://img.shields.io/badge/-Redis-DC382D?style=flat-square&logo=redis&logoColor=white)

</td>
<td align="center" width="150">

**ML/Vector**

![PyTorch](https://img.shields.io/badge/-PyTorch-EE4C2C?style=flat-square&logo=pytorch&logoColor=white)
![pgvector](https://img.shields.io/badge/-pgvector-4169E1?style=flat-square&logo=postgresql&logoColor=white)
![HuggingFace](https://img.shields.io/badge/-Transformers-FFD21E?style=flat-square&logo=huggingface&logoColor=black)

</td>
<td align="center" width="150">

**Infrastructure**

![Docker](https://img.shields.io/badge/-Docker-2496ED?style=flat-square&logo=docker&logoColor=white)
![PostGIS](https://img.shields.io/badge/-PostGIS-4169E1?style=flat-square&logo=postgresql&logoColor=white)
![Prometheus](https://img.shields.io/badge/-Prometheus-E6522C?style=flat-square&logo=prometheus&logoColor=white)

</td>
</tr>
</table>

<br />

## Performance

| Metric | v1 | v2 (Full Pipeline) |
|--------|-----|---------------------|
| **Vector dimensions** | 1024 | 1024 |
| **Index type** | DiskANN | DiskANN |
| **Retrieval latency** | < 50ms | < 20ms |
| **Full pipeline P99** | N/A | < 100ms |
| **Cache TTL** | 300s | 300s |

### v2 Latency Breakdown

| Stage | Latency | Cumulative |
|-------|---------|------------|
| Bi-Encoder + ANN | 15ms | 15ms |
| Skill Graph (optional) | 10ms | 25ms |
| Cross-Encoder (100 pairs) | 50ms | 75ms |
| Explainability | 10ms | 85ms |

<br />

## Configuration

<details>
<summary><b>Environment Variables</b></summary>

```bash
# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/resonance
MONGODB=mongodb://localhost:27017/resonance

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_CACHE_TTL=300

# Vector Search
VECTOR_INDEX_TYPE=hnsw  # or ivfflat
VECTOR_HNSW_M=16
VECTOR_HNSW_EF_SEARCH=64

# Auth
SECRET_KEY=your-secret-key
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
```
</details>

<br />

## Project Structure

```
resonance/
├── app/
│   ├── core/              # Config, auth, security
│   ├── libs/
│   │   └── job_matcher/   # Vector matching engine (v1)
│   ├── ml/                # Resonance v2 ML Pipeline
│   │   ├── models/        # BiEncoder, CrossEncoder, Explainer
│   │   ├── knowledge_graph/  # Skill taxonomy + GNN
│   │   ├── training/      # Hard negatives, contrastive learning
│   │   └── pipeline.py    # End-to-end orchestrator
│   ├── routers/           # API endpoints
│   ├── services/          # Business logic
│   ├── schemas/           # Pydantic models
│   └── main.py
├── docs/                  # Documentation (ADRs, HLDs, Runbooks)
├── tests/                 # Test suite
└── docker-compose.yaml
```

<br />

## Documentation

| Document | Description |
|----------|-------------|
| [CLAUDE.md](CLAUDE.md) | Developer guide & architecture deep-dive |
| [docs/README.md](docs/README.md) | Full documentation index |
| [docs/hld/](docs/hld/) | High-Level Designs (Resonance v2 ML Pipeline) |
| [docs/adr/](docs/adr/) | Architecture Decision Records |
| [docs/runbooks/](docs/runbooks/) | Operational procedures |

<br />

## Contributing

```bash
# Fork, clone, and install
git clone https://github.com/YOUR_USERNAME/resonance.git
cd resonance
pip install -r requirements.txt

# Run tests
pytest -q

# Create a branch and submit a PR
git checkout -b feature/amazing-feature
```

Please read [CLAUDE.md](CLAUDE.md) for development guidelines.

<br />

## License

Proprietary © [AIgen Solutions S.r.l.](https://github.com/AIgen-Solutions-s-r-l) — All rights reserved.

---

<div align="center">

**[Documentation](docs/README.md)** · **[Report Bug](https://github.com/AIgen-Solutions-s-r-l/resonance/issues)** · **[Request Feature](https://github.com/AIgen-Solutions-s-r-l/resonance/issues)**

Built with focus by the AIgen team

</div>
