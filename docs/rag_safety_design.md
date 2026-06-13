# RAG Safety Design

The seed course is `人工智能导论`. It includes course documents, chunks, source_refs, knowledge points, and prerequisite edges. Retrieval returns chunks with source_refs for generated academic resources.

Verifier gates check:

- schema shape;
- source_refs presence and shape;
- quiz answer/explanation consistency;
- code safety;
- image prompt safety;
- content/prompt-injection guard;
- personalized fit.

Resources without source_refs fail. Valid RAG-grounded resources pass with source coverage and verifier score.
