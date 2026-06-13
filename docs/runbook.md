# Runbook

Install dependencies:

```bash
npm install
python3 -m venv .venv
. .venv/bin/activate
pip install -e 'services/api[test]'
```

Enable embedded Hermes SDK runtime:

```bash
. .venv/bin/activate
pip install 'hermes-agent>=0.14.0'
# For a local Hermes checkout instead:
# pip install -e /absolute/path/to/hermes-agent
```

Run manually:

```bash
. .venv/bin/activate
DATABASE_URL=sqlite:///.data/dev.sqlite uvicorn app.main:app --app-dir services/api --host 127.0.0.1 --port 8000
npm run web:dev
```

Run full validation:

```bash
bash scripts/run_full_validation.sh
```

Write current external readiness proof:

```bash
python scripts/check_external_readiness.py
python scripts/check_hermes_sdk_embedding.py
python scripts/check_external_readiness.py --require-external-ready  # fails until every external provider is ready
```

For PostgreSQL runtime, start `docker compose up -d postgres redis` and set `DATABASE_URL` to the Postgres URL in `.env.example`.
