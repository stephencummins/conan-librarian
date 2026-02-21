import base64
import csv
import io
import json
import os
import sqlite3
import time
from pathlib import Path
from typing import Optional

import httpx
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", "./uploads"))
DB_PATH = Path(os.getenv("DB_PATH", "./data/shelfscan.db"))
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llava")
USE_OLLAMA = os.getenv("USE_OLLAMA", "false").lower() == "true"
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-6")

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------
app = FastAPI(title="ShelfScan", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------
SCHEMA = """
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
    section         TEXT,
    source_image    TEXT,
    added_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
"""


def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    conn = get_db()
    conn.execute(SCHEMA)
    conn.commit()
    conn.close()


def migrate_db() -> None:
    conn = get_db()
    try:
        conn.execute("ALTER TABLE books ADD COLUMN section TEXT")
        conn.commit()
    except sqlite3.OperationalError:
        pass  # column already exists
    conn.close()


init_db()
migrate_db()

# ---------------------------------------------------------------------------
# Vision: extract book list from image
# ---------------------------------------------------------------------------
VISION_PROMPT = (
    "Examine this bookshelf image carefully. "
    "List every book title and author name you can read on the spines. "
    "Return ONLY a valid JSON array — no other text, no markdown, no explanation. "
    'Format: [{"title": "Book Title", "author": "Author Name"}, ...] '
    "Use null for author when unreadable."
)


def _parse_book_list(text: str) -> list[dict]:
    """Extract JSON array from model response, tolerating extra prose."""
    text = text.strip()
    start = text.find("[")
    end = text.rfind("]") + 1
    if start == -1 or end == 0:
        return []
    try:
        items = json.loads(text[start:end])
        return [i for i in items if isinstance(i, dict) and i.get("title")]
    except json.JSONDecodeError:
        return []


async def _extract_via_openai(image_bytes: bytes, content_type: str) -> list[dict]:
    from openai import AsyncOpenAI

    b64 = base64.b64encode(image_bytes).decode()
    data_url = f"data:{content_type};base64,{b64}"
    client = AsyncOpenAI(api_key=OPENAI_API_KEY)
    response = await client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": data_url, "detail": "high"}},
                    {"type": "text", "text": VISION_PROMPT},
                ],
            }
        ],
        max_tokens=1500,
    )
    return _parse_book_list(response.choices[0].message.content or "")


async def _extract_via_ollama(image_bytes: bytes) -> list[dict]:
    b64 = base64.b64encode(image_bytes).decode()
    async with httpx.AsyncClient(timeout=180) as client:
        resp = await client.post(
            f"{OLLAMA_URL}/api/generate",
            json={"model": OLLAMA_MODEL, "prompt": VISION_PROMPT, "images": [b64], "stream": False},
        )
        resp.raise_for_status()
        return _parse_book_list(resp.json().get("response", ""))


async def _extract_via_claude(image_bytes: bytes, content_type: str) -> list[dict]:
    import anthropic
    b64 = base64.b64encode(image_bytes).decode()
    client = anthropic.AsyncAnthropic(api_key=ANTHROPIC_API_KEY)
    response = await client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=1500,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {"type": "base64", "media_type": content_type, "data": b64},
                    },
                    {"type": "text", "text": VISION_PROMPT},
                ],
            }
        ],
    )
    return _parse_book_list(response.content[0].text)


async def extract_books(image_bytes: bytes, content_type: str) -> list[dict]:
    if USE_OLLAMA:
        return await _extract_via_ollama(image_bytes)
    if ANTHROPIC_API_KEY:
        return await _extract_via_claude(image_bytes, content_type)
    if OPENAI_API_KEY:
        return await _extract_via_openai(image_bytes, content_type)
    raise ValueError("No vision backend configured. Set ANTHROPIC_API_KEY, OPENAI_API_KEY, or USE_OLLAMA=true in .env")


# ---------------------------------------------------------------------------
# Open Library metadata lookup
# ---------------------------------------------------------------------------
async def lookup_metadata(title: str, author: Optional[str]) -> dict:
    params: dict = {"title": title, "limit": 1}
    if author:
        params["author"] = author

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get("https://openlibrary.org/search.json", params=params)
            resp.raise_for_status()
            docs = resp.json().get("docs", [])
    except Exception:
        return {"title": title, "author": author}

    if not docs:
        return {"title": title, "author": author}

    doc = docs[0]
    cover_id = doc.get("cover_i")
    isbn_list = doc.get("isbn", [])

    first_sentence = doc.get("first_sentence")
    description = None
    if isinstance(first_sentence, dict):
        description = first_sentence.get("value")
    elif isinstance(first_sentence, str):
        description = first_sentence

    return {
        "title": doc.get("title") or title,
        "author": (doc.get("author_name") or [author])[0],
        "isbn": isbn_list[0] if isbn_list else None,
        "cover_url": f"https://covers.openlibrary.org/b/id/{cover_id}-M.jpg" if cover_id else None,
        "description": description,
        "publisher": (doc.get("publisher") or [None])[0],
        "publish_year": doc.get("first_publish_year"),
        "open_library_key": doc.get("key"),
    }


# ---------------------------------------------------------------------------
# API routes
# ---------------------------------------------------------------------------
@app.get("/api/health")
async def health():
    backend = "ollama" if USE_OLLAMA else ("claude" if ANTHROPIC_API_KEY else ("openai" if OPENAI_API_KEY else "none"))
    conn = get_db()
    total = conn.execute("SELECT COUNT(*) FROM books").fetchone()[0]
    conn.close()
    return {"status": "ok", "vision_backend": backend, "total_books": total}


@app.post("/api/scan")
async def scan_image(file: UploadFile = File(...)):
    if not (file.content_type or "").startswith("image/"):
        raise HTTPException(400, "File must be an image")

    image_bytes = await file.read()

    # Save upload for reference
    filename = f"{int(time.time())}_{file.filename}"
    (UPLOAD_DIR / filename).write_bytes(image_bytes)

    # Vision extraction
    try:
        detected = await extract_books(image_bytes, file.content_type or "image/jpeg")
    except ValueError as e:
        raise HTTPException(503, str(e))
    except Exception as e:
        raise HTTPException(502, f"Vision API error: {e}")

    if not detected:
        return {"books_added": 0, "detected": 0, "books": [], "message": "No books detected in image"}

    # Metadata + DB insert
    added = []
    conn = get_db()
    for item in detected:
        title = (item.get("title") or "").strip()
        author = (item.get("author") or "").strip() or None
        if not title:
            continue

        meta = await lookup_metadata(title, author)
        cursor = conn.execute(
            """INSERT INTO books
               (title, author, isbn, cover_url, description, publisher, publish_year, open_library_key, section, source_image)
               VALUES (:title, :author, :isbn, :cover_url, :description, :publisher, :publish_year, :open_library_key, :section, :source_image)""",
            {
                "title": meta["title"],
                "author": meta.get("author"),
                "isbn": meta.get("isbn"),
                "cover_url": meta.get("cover_url"),
                "description": meta.get("description"),
                "publisher": meta.get("publisher"),
                "publish_year": meta.get("publish_year"),
                "open_library_key": meta.get("open_library_key"),
                "section": None,
                "source_image": filename,
            },
        )
        conn.commit()
        row = dict(meta)
        row["id"] = cursor.lastrowid
        row["source_image"] = filename
        added.append(row)

    conn.close()
    return {"books_added": len(added), "detected": len(detected), "books": added}


@app.get("/api/sections")
async def list_sections():
    conn = get_db()
    rows = conn.execute(
        "SELECT DISTINCT section FROM books WHERE section IS NOT NULL AND section != '' ORDER BY section"
    ).fetchall()
    conn.close()
    return {"sections": [r[0] for r in rows]}


@app.post("/api/books")
async def add_book(data: dict):
    title = (data.get("title") or "").strip()
    if not title:
        raise HTTPException(400, "title required")
    author = (data.get("author") or "").strip() or None
    isbn = (data.get("isbn") or "").strip() or None
    section = (data.get("section") or "").strip() or None

    meta = await lookup_metadata(title, author)
    conn = get_db()
    cursor = conn.execute(
        """INSERT INTO books
           (title, author, isbn, cover_url, description, publisher, publish_year, open_library_key, section)
           VALUES (:title, :author, :isbn, :cover_url, :description, :publisher, :publish_year, :open_library_key, :section)""",
        {
            "title": meta.get("title") or title,
            "author": meta.get("author") or author,
            "isbn": meta.get("isbn") or isbn,
            "cover_url": meta.get("cover_url"),
            "description": meta.get("description"),
            "publisher": meta.get("publisher"),
            "publish_year": meta.get("publish_year"),
            "open_library_key": meta.get("open_library_key"),
            "section": section,
        },
    )
    conn.commit()
    row = dict(meta)
    row["id"] = cursor.lastrowid
    row["section"] = section
    conn.close()
    return row


@app.get("/api/books")
async def list_books(q: Optional[str] = None, section: Optional[str] = None, limit: int = 200, offset: int = 0):
    conn = get_db()
    filters, params = [], []
    if q:
        filters.append("(title LIKE ? OR author LIKE ?)")
        like = f"%{q}%"
        params += [like, like]
    if section:
        filters.append("section = ?")
        params.append(section)
    where = ("WHERE " + " AND ".join(filters)) if filters else ""
    rows = conn.execute(
        f"SELECT * FROM books {where} ORDER BY added_at DESC LIMIT ? OFFSET ?",
        params + [limit, offset],
    ).fetchall()
    total = conn.execute(f"SELECT COUNT(*) FROM books {where}", params).fetchone()[0]
    conn.close()
    return {"total": total, "books": [dict(r) for r in rows]}


@app.delete("/api/books/{book_id}")
async def delete_book(book_id: int):
    conn = get_db()
    result = conn.execute("DELETE FROM books WHERE id = ?", (book_id,))
    conn.commit()
    conn.close()
    if result.rowcount == 0:
        raise HTTPException(404, "Book not found")
    return {"ok": True}


@app.get("/api/export/csv")
async def export_csv():
    conn = get_db()
    rows = [dict(r) for r in conn.execute("SELECT * FROM books ORDER BY added_at DESC").fetchall()]
    conn.close()

    output = io.StringIO()
    fields = ["id", "title", "author", "isbn", "publisher", "publish_year",
              "description", "cover_url", "open_library_key", "source_image", "added_at"]
    writer = csv.DictWriter(output, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(rows)
    output.seek(0)

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=shelfscan-library.csv"},
    )


@app.get("/api/export/json")
async def export_json():
    conn = get_db()
    rows = [dict(r) for r in conn.execute("SELECT * FROM books ORDER BY added_at DESC").fetchall()]
    conn.close()
    return StreamingResponse(
        iter([json.dumps(rows, indent=2)]),
        media_type="application/json",
        headers={"Content-Disposition": "attachment; filename=shelfscan-library.json"},
    )


# ---------------------------------------------------------------------------
# Serve frontend (must be last)
# ---------------------------------------------------------------------------
app.mount("/", StaticFiles(directory="static", html=True), name="static")
