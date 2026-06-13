# Orchestrator Agent

File: `services/api/app/agents/orchestrator_agent.py`

Routes tutor turns into profile, knowledge, planner, resource, app canvas, memory, verifier, and tutor steps. It prepares Hermes profile assets, records `agent_runs` and `agent_steps`, and streams `AgentStreamEvent` variants to the frontend.

Tests: `services/api/tests/test_agents_and_skills.py`, `services/api/tests/test_streaming_events.py`.
