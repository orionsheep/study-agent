# Open-source NotebookLM Alternatives Evaluation

Snapshot date: 2026-06-05

This evaluation targets self-hostable NotebookLM-like products that can connect to owned LLM APIs, local models, or OpenAI-compatible gateways. It explicitly excludes wrappers that automate or reverse-call Google's hosted NotebookLM service.

Evidence collected:

- GitHub metadata through the GitHub API for all requested repositories.
- Root README plus available `docker-compose.yml` / `compose.yaml`, `.env.example`, `package.json`, `pyproject.toml`, and license files.
- Static Docker Compose config checks for projects with root compose files.
- No full long-running container deployment was started in this pass; the check focused on whether the documented configuration path is coherent enough to adopt or borrow from.

Raw snapshot: `.runtime/notebooklm_eval/repo_snapshot.json`

## Final Ranking

### Most Worth Adopting

1. **Open Notebook** — best primary reference for LearnForge.
   It has the strongest combination of maturity, self-hosting, multi-provider model support, RAG, citations, podcast generation, REST API, MCP integration, Docker deployment, and permissive MIT license.

2. **SurfSense** — strongest reference for enterprise-style retrieval and connectors.
   Its README emphasizes hybrid search, many LLM/embedding providers, local/private model support, inline citations, browser/Slack/Discord/Notion sources, and team use. It is more complex than Open Notebook and should be used as architecture reference, not blindly embedded.

3. **Qiplim Studio** — best education-product reference despite tiny project size.
   It has the most relevant feature map for LearnForge: hybrid search, HyDE, contextual embeddings, reranking, citations, quizzes, podcasts, summaries, flashcards, mind maps, presentations, public API, and MCP. The risk is maturity: GitHub snapshot shows only 1 star and 1 fork.

### Worth Referencing

- **PageLM** — promising education flow with quizzes, flashcards, podcasts, RAG, multiple LLM providers, and Docker. Static compose check failed until `.env` is provided, so setup is less smooth than Open Notebook/Qiplim.
- **tldw_server** — deep research/media/RAG toolbox with BM25 + vector + rerank, local/hosted LLMs, MCP, quiz/flashcard/media support. It is broad and powerful but GPL-3.0 and likely too heavy for LearnForge core.
- **InsightsLM public/local** — useful no-code/Supabase/N8N pattern for fast prototypes and fully-local demos, but less suitable as LearnForge's main engineering base.

### Only as Functional Modules

- **Podcastfy** — strong podcast/audio overview component.
- **Local-NotebookLM** — simple local PDF-to-audio pipeline reference.
- **NotebookLlama** — useful LlamaIndex/LlamaCloud/MCP example, but not ideal as a self-contained NotebookLM replacement because it depends on the Llama stack.

### Not Recommended as Main Base

- **KnowNote** — nice local-first Electron idea, but GPL-3.0 and desktop-first shape make it less aligned with LearnForge's web/canvas architecture.

## Comparison Table

| Project | Positioning | Self-host | Model Integration | RAG / Citation | Learning Outputs | API / Extensibility | Deployment | License | Maturity | Main Risk |
|---|---|---:|---|---|---|---|---|---|---|---|
| [Open Notebook](https://github.com/lfnovo/open-notebook) | Full NotebookLM alternative | Yes | OpenAI, Anthropic, Ollama, LM Studio, OpenRouter, many more | Full-text + vector; citations described as basic but present | Podcasts, multimodal content, source-grounded answers | REST API, MCP | Docker Compose config OK | MIT | 25,467 stars, pushed 2026-06-04 | Citation quality claims still “will improve” |
| [SurfSense](https://github.com/MODSetter/SurfSense) | Team/private research knowledge base | Yes | OpenAI spec, LiteLLM, Gemini, Ollama, vLLM, many embeddings/rerankers | Hybrid search + citations | Podcast/audio samples, document chat | Browser extension, connectors, API surface | Docs mention Docker; root compose not in initial root snapshot | Apache-2.0 | 14,403 stars, pushed 2026-06-04 | Large system, setup complexity |
| [Qiplim Studio](https://github.com/Qiplim/studio) | Education content generation studio | Yes | OpenAI, Anthropic, Gemini, Mistral BYOK | pgvector + tsvector, HyDE, contextual embeddings, Jina reranking, citations | Podcasts, quizzes, summaries, flashcards, mind maps, presentations | Public API, MCP | Docker Compose config OK | MIT | 1 star, pushed 2026-05-01 | Very early project |
| [PageLM](https://github.com/CaviraOSS/PageLM) | Education NotebookLM | Yes | Gemini, OpenAI, Claude, Grok, MiniMax, Ollama, OpenRouter | RAG/vector features stated | Quizzes, flashcards, notes, podcasts | REST/WebSocket mentioned | Compose needs `.env`; config check failed without it | License file present; GitHub reports NOASSERTION | 1,644 stars, pushed 2026-06-04 | Setup/document consistency |
| [KnowNote](https://github.com/MrSibe/KnowNote) | Local-first desktop knowledge base | Local desktop | OpenAI, DeepSeek, Ollama | RAG with source traceability | Quiz/audio features mentioned | Desktop app/API internals | No Docker required | GPL-3.0 | 1,003 stars, pushed 2026-02-12 | GPL and desktop-first |
| [Podcastfy](https://github.com/souzatharsis/podcastfy) | Podcast/audio module | Yes | 100+ LLMs incl. OpenAI/Gemini/local via LiteLLM style | Not primary RAG product | Podcast/audio conversation | Python package/API | Compose config OK | Apache-2.0 | 6,343 stars, pushed 2026-05-04 | Module only |
| [Local-NotebookLM](https://github.com/Goekdeniz-Guelmez/Local-NotebookLM) | Local PDF-to-audio NotebookLM-like tool | Yes/local | OpenAI, Groq, LM Studio, Ollama, Azure | Basic document processing | Audio/podcast | CLI/web/API modes | Docker mentioned; no root compose in snapshot | Apache-2.0 | 907 stars, pushed 2026-05-08 | Narrow scope |
| [tldw_server](https://github.com/rmusser01/tldw_server) | Research/media multi-tool | Yes | OpenAI-compatible, vLLM, Ollama, llama.cpp, many providers | BM25 + vector + rerank; ChromaDB/pgvector | Quiz, flashcards, media workflows | REST/MCP/extension | No root compose in snapshot; docs-heavy | GPL-3.0 | 1,404 stars, pushed 2026-06-05 | GPL, broad/heavy |
| [InsightsLM public](https://github.com/theaiautomators/insights-lm-public) | Supabase + N8N NotebookLM clone | Yes | OpenAI/Gemini; points to local package for Ollama | Verifiable citations | Podcast generation | N8N workflows + frontend | Docker Compose guide | MIT | 540 stars, pushed 2026-01-16 | Workflow/no-code stack coupling |
| [InsightsLM local](https://github.com/theaiautomators/insights-lm-local-package) | Fully local InsightsLM package | Yes/local | Ollama/Qwen/Whisper/CoquiTTS | Verifiable citations | Local podcast/audio | N8N workflows | Docker local package | MIT | 212 stars, pushed 2025-09-12 | Lower activity |
| [NotebookLlama](https://github.com/run-llama/notebookllama) | LlamaCloud-backed NotebookLM alternative | Partially | OpenAI/Gemini keys; Llama stack | LlamaIndex pipeline | Audio overview | MCP server | Compose config OK with env warnings | MIT | 1,907 stars, pushed 2026-03-02 | LlamaCloud dependency |

## Project Notes

### Open Notebook

Open Notebook is the best main reference because it matches the broad NotebookLM replacement shape: document ingestion, grounded answers, citations, podcast generation, Docker deployment, REST API, and MCP. Its `docker-compose.yml` parsed successfully with `docker compose config`. For LearnForge, copy the product architecture ideas rather than replacing the existing canvas: source model, notebook grouping, citations, podcast jobs, and API boundaries.

### SurfSense

SurfSense is the best retrieval/enterprise reference. Its README explicitly compares itself against NotebookLM with OpenAI-spec/LiteLLM support, many embedding models/rerankers, local LLM support through vLLM/Ollama, hybrid search, and cited answers. It also has external source connectors, which LearnForge can later map into Resource Center imports. Main concern: it is a large product surface and may be too complex to embed directly.

### Qiplim Studio

Qiplim has the closest education feature map to LearnForge: generated quizzes, podcasts, summaries, flashcards, mind maps, presentations, citations, API, and MCP. It also documents an advanced RAG stack: pgvector + tsvector, HyDE, contextual embeddings, and reranking. Its `docker-compose.yml` parsed successfully. Main concern: the project is very young, so use it as design/reference, not dependency.

### PageLM

PageLM is compelling for education workflows and supports Gemini/OpenAI/Ollama/OpenRouter-style usage. It has Docker Compose and an `.env.example`, but `docker compose config` failed in the raw snapshot because the compose file expected a `.env` file and `VITE_BACKEND_URL`. Treat it as a useful product reference, but not the first adoption target.

### KnowNote

KnowNote is attractive for local-first personal knowledge management and simple desktop use. The desktop/Electron path is not a natural fit for LearnForge's browser canvas, and GPL-3.0 is a commercial integration risk. Use it only for UX inspiration around local-first document notes.

### Podcastfy

Podcastfy should be treated as an audio overview module reference. It is mature and Apache-2.0, but it is not a full NotebookLM knowledge base. LearnForge can borrow its podcast pipeline shape later.

### Local-NotebookLM

Local-NotebookLM is a smaller local PDF/audio tool. It is useful for understanding a minimal local audio path, but not enough for LearnForge's structured resource center, citations, and multi-app canvas.

### tldw_server

tldw_server has the richest research-tool surface after Open Notebook/SurfSense: hybrid search, local and hosted LLM support, media processing, MCP, quiz/flashcard features. It is GPL-3.0 and broad, so it is not a good direct base for LearnForge, but it is useful for long-term RAG/media roadmap ideas.

### InsightsLM

InsightsLM is a useful deployment pattern for teams that like Supabase + N8N workflows. The local package proves a fully local version is possible with Ollama and local TTS/STT. It is less suitable as a core LearnForge dependency because workflow orchestration lives heavily in N8N.

### NotebookLlama

NotebookLlama is worth studying for LlamaIndex and MCP patterns, but the LlamaCloud-backed positioning makes it less aligned with the user's requirement for self-hosted, own-model control.

## Recommendation for LearnForge

Fastest NotebookLM replacement:

- Use **Open Notebook** as the main blueprint.
- Keep LearnForge's existing canvas/chat UI, but adopt Open Notebook's source/notebook/RAG/audio/API boundaries.

Enterprise knowledge base:

- Use **SurfSense** as the reference for hybrid retrieval, connectors, reranking, local/private LLM support, and team-source ingestion.

Education learning product:

- Use **Qiplim Studio** and **PageLM** as references for learning outputs: quizzes, flashcards, summaries, mind maps, presentations, and podcasts.

Secondary development reference:

- Open Notebook for maturity and APIs.
- Qiplim for education RAG/product design.
- SurfSense for retrieval architecture.
- Podcastfy for audio overview.

## LearnForge Implementation Delta

Already implemented in this pass:

- Resource Center now supports structured resources, modules, search, tags, roadmap, citation coverage, detail panel, source refs, and feedback actions.
- The math knowledge base now contains the requested math-only AI/data-science prerequisite resources with structured fields, roadmap, tags, and deduped resources.
- The local physics PDF has been imported through Gemini OCR for 111 verified pages so far, with page-level `source_ref`s.
- All 125 current knowledge chunks have Gemini embeddings and hybrid retrieval ranking.
- `custom.html` now allows safe inline scripts and executes them in the sandbox after finalization.

Next architecture step:

- Add notebook/source entities and ingestion jobs modeled after Open Notebook.
- Add retrieval pipeline phases inspired by SurfSense/Qiplim: BM25/text match, vector search, HyDE query expansion, rerank, citation composer.
- Add generated learning artifacts as first-class jobs: summary, study guide, quiz, flashcards, podcast/audio overview, mind map, slide/report.
