# A-TECH Corporation Backend

Initial FastAPI foundation for the A-TECH Corporation platform.

## Requirements

- Python 3.12+
- Dependencies listed in `requirements.txt`

## Local setup

Create and activate a virtual environment, then install dependencies:

```bash
python -m venv .venv
# Windows PowerShell
.venv\Scripts\Activate.ps1
# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
```

Copy the root `.env.example` to a local `.env` when environment configuration is needed. Never commit real secrets.

## Run the API

From this directory:

```bash
uvicorn app.main:app --reload
```

- Root: `http://127.0.0.1:8000/`
- Health: `http://127.0.0.1:8000/api/v1/health`
- OpenAPI docs: `http://127.0.0.1:8000/docs`

## Tests and lint

```bash
pytest
ruff check app tests
```

These commands are documentation only; no dependencies were installed and no commands were run as part of this repository change.

## Current boundaries

- No database connection or migrations (P1-03).
- No login, session, token, or MFA endpoints (P1-04).
- Password hashing primitives use Argon2id and are not yet wired into authentication.
- Role membership helper is foundational only; authorization policies and enforcement are not yet wired into routes.
- Health status reports process/API health only, not database or downstream dependency readiness.
