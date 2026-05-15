# tiny-tokenizer

Interactive tokenizer playground — visualize, compare, and price LLM tokenizers.

## Repo layout

```
tiny-tokenizer/
├── tokenizer/        # Python BPE tokenizer (the foundation of this project)
│   ├── tiny.py       # the class
│   ├── cli.py        # `python -m tokenizer.cli ...`
│   └── data/         # corpus + trained model
├── backend/          # FastAPI service
│   └── app/
│       ├── main.py
│       ├── routes.py
│       ├── tokenizers/   # adapter registry (tiny, tiktoken, hf, anthropic, gemini)
│       ├── middleware.py # request logging, security headers
│       ├── session.py    # anonymous fingerprint + signed cookie
│       ├── rate_limit.py
│       ├── analytics.py  # server-side PostHog
│       └── metrics.py    # Prometheus
├── frontend/         # Vite + React 19 + TS + Tailwind v4 + GSAP + shadcn-style
│   └── src/
│       ├── pages/        # Playground, Learn
│       ├── components/   # TokenStrip, Button, ErrorBoundary
│       └── lib/          # api, fingerprint, posthog, logger
└── Makefile
```

## Requirements

- **Python 3.12+** (`brew install python@3.12`)
- **Node 22.12+** (the older 22.3 works but Vite warns)
- macOS / Linux

## Quick start

```bash
make install     # creates venv, runs `pip install -e .`, installs frontend
make dev         # backend on :8765, frontend on :5173
```

Open <http://localhost:5173>.

After `make install`, you can also run the backend directly:

```bash
. venv/bin/activate
python -m app.main          # equivalent to `make backend`
```

> Don't run `python backend/app/main.py` — the relative imports won't resolve
> because the script isn't aware of the package layout. Use the module form
> (`python -m app.main`) or the Makefile target.

### Train a fresh TinyTokenizer

```bash
make train-tiny
# or with custom args:
. venv/bin/activate
python -m tokenizer.cli "your text here" --vocab-size 2048 --save tokenizer/data/tok.json
```

## Cross-cutting concerns (already wired)

- **Structured logging** — `structlog` JSON output, one line per request with `request_id`, latency, status
- **Observability** — `/metrics` Prometheus endpoint; PostHog (client + server) when keys are set
- **Anonymous auth** — signed session cookie + browser fingerprint header (no passwords)
- **Rate limiting** — `slowapi`, 60/min on `/tokenize`, keyed on cookie or IP
- **Security headers** — strict CSP, HSTS in prod, no-sniff, no-frame
- **Input/output validation** — Pydantic on every endpoint with `extra="forbid"`
- **Error handling** — global handlers; no silent failures; pre-commit gitleaks for secrets
- **CORS** — explicit allowlist of frontend origins

## Environment

All env files (`.env`, `.env.local`, `.env.example`, etc.) are gitignored.
Create the ones you need locally — every variable is optional in dev. The
canonical reference for each setting is the corresponding config module
([`backend/app/config.py`](backend/app/config.py),
[`frontend/src/lib/env.ts`](frontend/src/lib/env.ts)).

### `backend/.env` (read by `pydantic-settings`)

| Variable | Default | Purpose |
|---|---|---|
| `ENV` | `development` | `development` \| `staging` \| `production` |
| `LOG_LEVEL` | `INFO` | structlog level |
| `ALLOWED_ORIGINS` | `["http://localhost:5173","http://127.0.0.1:5173"]` | CORS allowlist (JSON array) |
| `SESSION_SECRET` | dev-only string | sign anonymous session cookies — set a strong value in prod (`python -c "import secrets; print(secrets.token_urlsafe(48))"`) |
| `COOKIE_NAME` | `tt_session` | session cookie name |
| `COOKIE_SECURE` | `false` | set to `true` in prod (HTTPS) |
| `MAX_PROMPT_CHARS` | `100000` | hard cap on `/tokenize` input length |
| `RATE_LIMIT_PER_MINUTE` | `100` | default rate-limit ceiling |
| `ANTHROPIC_API_KEY` | _(blank)_ | enables Anthropic count_tokens proxy when set |
| `GEMINI_API_KEY` | _(blank)_ | enables Gemini token count proxy when set |
| `PAID_COUNT_DAILY_CAP` | `10000` | daily safety cap on paid `count_tokens` calls |
| `POSTHOG_API_KEY` | _(blank)_ | enables server-side PostHog when set |
| `POSTHOG_HOST` | `https://us.i.posthog.com` | PostHog ingest host |

### `frontend/.env.local` (Vite, only `VITE_` vars reach the browser)

| Variable | Default | Purpose |
|---|---|---|
| `VITE_API_BASE_URL` | `http://127.0.0.1:8765` | backend URL |
| `VITE_POSTHOG_KEY` | _(blank)_ | enables client-side PostHog when set |
| `VITE_POSTHOG_HOST` | `https://us.i.posthog.com` | PostHog ingest host |

## Pre-commit hooks

```bash
pip install pre-commit && pre-commit install
```

Gitleaks blocks accidental secret commits. Ruff lints and formats Python.

## License

MIT
