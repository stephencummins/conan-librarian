# ShelfScan

AI-powered bookshelf cataloger. Upload a photo of your bookshelf and it automatically identifies books, fetches metadata from Open Library, and builds a searchable library.

## Quick start

```bash
cp .env.example .env
# edit .env — add your OPENAI_API_KEY or set USE_OLLAMA=true

docker compose up --build
```

Open http://localhost:8000

## Vision backends

**OpenAI (recommended):** Set `OPENAI_API_KEY=sk-...` in `.env`. Uses `gpt-4o` by default.

**Ollama (local/free):** Install [Ollama](https://ollama.ai), then:
```bash
ollama pull llava
# In .env:
USE_OLLAMA=true
OLLAMA_URL=http://host.docker.internal:11434  # if running in Docker
```

## API

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/scan` | Upload image, returns detected books |
| `GET` | `/api/books` | List library (`?q=` for search) |
| `DELETE` | `/api/books/{id}` | Remove a book |
| `GET` | `/api/export/csv` | Download CSV |
| `GET` | `/api/export/json` | Download JSON |
| `GET` | `/api/health` | Status check |

## Data

- SQLite database at `./data/shelfscan.db`
- Uploaded images saved to `./uploads/`
- Both directories are Docker volumes — data persists across restarts

## Run without Docker

```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # edit as needed
export $(cat .env | grep -v '#' | xargs)
uvicorn main:app --reload --port 8000
```
