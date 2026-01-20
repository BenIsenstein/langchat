# LangChat Backend

This is a fastAPI server to deliver the functionality of an agentic chat experience.

## Standalone local dev

To run this backend on your local machine, setup a virtual environment:

```sh
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

To run the service with hot reload:

```sh
uvicorn app.main:app --host "::" --port 8000 --reload
```

## Local dev within docker compose

If you run docker compose from the repo root, it will just work.

Just the backend:

```sh
docker compose up backend
```

Entire stack:

```sh
docker compose up
```

