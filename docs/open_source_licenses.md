# Open Source License Inventory

Primary open-source dependencies:

- FastAPI, Starlette, Uvicorn, Pydantic, HTTPX, pytest, pytest-asyncio.
- Hermes Agent through the embedded Python `run_agent.AIAgent` SDK path when installed in the API venv.
- React, React DOM, Vite, TypeScript, Vitest, Playwright.
- Framer Motion for AppLink Flight animation.
- lucide-react for interface icons.

PostgreSQL, pgvector, and Redis are declared through Docker Compose for production-style runtime services. The app-protocol package is local source.
