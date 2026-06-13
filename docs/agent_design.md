# Agent Design

The agent topology implements the required 11 agents:

- Orchestrator Agent routes tutor turns, streams trace events, and prepares Hermes skills through the embedded `run_agent.AIAgent` SDK path.
- Profile Agent extracts 8+ student dimensions and writes EduMem0 profile evidence.
- Knowledge Agent retrieves seed course chunks and prerequisite graph edges.
- Planner Agent creates personalized learning paths and writes path memory.
- Recommender Agent scores resources by profile, weakness, goal, and feedback.
- Tutor Agent streams grounded teacher-like text and explains App events.
- App Canvas Agent creates/focuses CanvasApps and persists AppLink events.
- Evaluator Agent grades quizzes and updates mastery/misconception memory.
- Verifier Agent checks source grounding, quiz consistency, safety, and fit.
- Memory Agent coordinates extraction, retrieval, update, decay, and conflict policies.
- Resource Bundle Agent generates 5+ resource types through Skills.

See `docs/agents/` for per-agent trace and test mappings.
