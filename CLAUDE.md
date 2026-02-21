# Conan Librarian — CLAUDE.md

## What it is
AI-powered bookshelf cataloger. Upload a photo of your bookshelf → vision model reads spine text → Open Library enriches metadata → SQLite stores the result. Single-file Python backend, static HTML frontend.

## Stack
- **Backend**: Python 3.12, FastAPI, uvicorn, httpx, sqlite3 (stdlib)
- **Frontend**: Single static `static/index.html` (vanilla JS, no build step)
- **Vision**: Claude `claude-sonnet-4-6` (default) → OpenAI `gpt-4o` → Ollama `llava` (priority order)
- **Metadata**: Open Library search API (free, no key needed)
- **Deployment**: Docker Compose (Alpine-based container)

## Key files
| File | Purpose |
|------|---------|
| `main.py` | Entire backend — config, DB, vision, API routes, static mount |
| `static/index.html` | Full frontend SPA (vanilla JS, no build step) |
| `data/shelfscan.db` | SQLite DB (git-ignored, Docker volume) |
| `uploads/` | Raw uploaded images (git-ignored, Docker volume) |
| `docker-compose.yml` | Production container config, maps port 8000 |
| `Dockerfile` | Alpine-based Python 3, port 8000 |
| `requirements.txt` | fastapi, uvicorn, openai, anthropic, httpx, python-multipart, aiofiles |

## Environment variables
| Var | Default | Notes |
|-----|---------|-------|
| `ANTHROPIC_API_KEY` | `` | **Preferred** — enables Claude vision backend |
| `CLAUDE_MODEL` | `claude-sonnet-4-6` | Any Claude vision-capable model |
| `OPENAI_API_KEY` | `` | Fallback if no Anthropic key |
| `OPENAI_MODEL` | `gpt-4o` | Any OpenAI vision-capable model |
| `USE_OLLAMA` | `false` | Last resort local fallback |
| `OLLAMA_URL` | `http://localhost:11434` | Use `host.docker.internal` in Docker |
| `OLLAMA_MODEL` | `llava` | Any multimodal Ollama model |
| `DB_PATH` | `./data/shelfscan.db` | SQLite file path |
| `UPLOAD_DIR` | `./uploads` | Image upload directory |

## Vision backend priority
`ANTHROPIC_API_KEY` set → Claude → `OPENAI_API_KEY` set → OpenAI → `USE_OLLAMA=true` → Ollama

## API
| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/scan` | Upload image → detect books → enrich → store |
| `GET` | `/api/books` | List library (`?q=` search, `limit`, `offset`) |
| `DELETE` | `/api/books/{id}` | Remove a book |
| `GET` | `/api/export/csv` | Download full library as CSV |
| `GET` | `/api/export/json` | Download full library as JSON |
| `GET` | `/api/health` | Status + vision backend name + book count |

## DB schema
```sql
CREATE TABLE IF NOT EXISTS books (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    title           TEXT NOT NULL,
    author          TEXT,
    isbn            TEXT,
    cover_url       TEXT,
    description     TEXT,
    publisher       TEXT,
    publish_year    INTEGER,
    open_library_key TEXT,
    source_image    TEXT,
    added_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
```

## Deployment
- **Mini path**: `~/conan-librarian`
- **Source**: `~/Projects/conan-librarian` (MacBook)
- **GitHub**: `stephencummins/conan-librarian`
- **URL**: conan.stephen8n.com (:8000, Docker Compose, cloudflared tunnel)
- **Data persists** in Docker volumes: `./data` and `./uploads`

## Deploy workflow
```bash
# MacBook: push changes
git push

# Mini: pull and rebuild (required when requirements.txt or Dockerfile changes)
cd ~/conan-librarian && git pull && docker compose up --build -d

# Mini: restart only (env/code changes, no new dependencies)
cd ~/conan-librarian && git pull && docker compose up -d

# Check health
curl http://localhost:8000/api/health
```

## Running locally
```bash
cp .env.example .env   # add ANTHROPIC_API_KEY
docker compose up --build
# or without Docker:
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

## Notes
- No deduplication — rescanning a shelf adds duplicates. Add a unique index on `isbn` or `(title, author)` if needed.
- Vision prompt returns JSON array; `_parse_book_list()` tolerates extra prose around the array.
- `data/` and `uploads/` are Docker volumes — wipe container safely, data persists.
- Ollama `llava` model is pulled on the Mini (~4.7GB) and available as fallback.
- The `Choose photo` button is a `<label for="fileInput">` — do NOT change to a JS `.click()` call (blocked by browsers behind proxies).
