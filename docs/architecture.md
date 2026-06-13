# LearnForge V2 Architecture

LearnForge V2 is a two-pane AI learning product: a left Spatial Learning App Canvas and a right Tutor Chat. The backend is a FastAPI service with persistent local development storage, PostgreSQL/pgvector schema support, real provider gateways, EduMem0 memory, RAG retrieval, agents, skills, and validation gates.

Core flow:

```text
Tutor Chat -> Hermes Orchestrator boundary -> Agents/Skills -> RAG + EduMem0 + Verifier -> Canvas Apps + Dashboard
```

The product uses deterministic local learning logic for non-external flows and real MiMo/image2/Hermes integration paths for provider readiness. Health endpoints report `blocked_*` when credentials or runtime checks are unavailable.
