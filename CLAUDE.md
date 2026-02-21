# ShelfScan — CLAUDE.md

## What it is
AI-powered bookshelf cataloger. Upload a photo of your bookshelf → vision model reads spine text → Open Library enriches metadata → SQLite stores the result. Single-file Python backend, static HTML frontend.

## Stack
- **Backend**: Python 3.12, FastAPI, uvicorn, httpx, sqlite3 (stdlib)
- **Frontend**: Single static `static/index.html` (vanilla JS, no build step)
- **Vision**: OpenAI `gpt-4o` (default) or Ollama `llava` (local)
- **Metadata**: Open Library search API (free, no key needed)
- **Deployment**: Docker Compose

## Key files
| File | Purpose |
|------|---------|
| `main.py` | Entire backend — config, DB, vision, API routes, static mount |
| `static/index.html` | Full frontend SPA |
| `data/shelfscan.db` | SQLite DB (git-ignored, Docker volume) |
| `uploads/` | Raw uploaded images (git-ignored, Docker volume) |
| `docker-compose.yml` | Production container config |
| `Dockerfile` | python:3.12-slim, port 8000 |
| `requirements.txt` | fastapi, uvicorn, openai, httpx, python-multipart, aiofiles |

## Environment variables
| Var | Default | Notes |
|-----|---------|-------|
| `OPENAI_API_KEY` | `` | Required unless USE_OLLAMA=true |
| `OPENAI_MODEL` | `gpt-4o` | Any vision-capable OpenAI model |
| `USE_OLLAMA` | `false` | Set to `true` to use local Ollama |
| `OLLAMA_URL` | `http://localhost:11434` | Use `host.docker.internal` in Docker |
| `OLLAMA_MODEL` | `llava` | Any multimodal Ollama model |
| `DB_PATH` | `./data/shelfscan.db` | SQLite file path |
| `UPLOAD_DIR` | `./uploads` | Image upload directory |

## API
| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/scan` | Upload image → detect books → enrich → store |
| `GET` | `/api/books` | List library (`?q=` search, `limit`, `offset`) |
| `DELETE` | `/api/books/{id}` | Remove a book |
| `GET` | `/api/export/csv` | Download full library as CSV |
| `GET` | `/api/export/json` | Download full library as JSON |
| `GET` | `/api/health` | Status + vision backend + book count |

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

## Running locally
```bash
cp .env.example .env   # add OPENAI_API_KEY or set USE_OLLAMA=true
docker compose up --build
# or without Docker:
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

## GitHub repo
`stephencummins/conan-librarian`

## Notes
- No deduplication — rescanning a shelf adds duplicates. Add a unique index on `isbn` or `(title, author)` if needed.
- Vision prompt returns JSON array; `_parse_book_list()` tolerates extra prose around the array.
- `data/` and `uploads/` are Docker volumes — wipe container safely, data persists.
