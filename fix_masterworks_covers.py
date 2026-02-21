#!/usr/bin/env python3
"""
Verify and fix SF Masterworks cover images.
For each book, checks if the current cover URL returns a real image.
Falls back to Google Books API for any missing or placeholder covers.
Run on the Mini: python3 ~/bookr/fix_masterworks_covers.py
"""
import json, sqlite3, urllib.request, urllib.error, time
from pathlib import Path

DB_PATH = Path.home() / "bookr/data/shelfscan.db"


def check_cover(url):
    """Returns True if URL resolves to a real JPEG image (not OL placeholder)."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "bookr/1.0"})
        with urllib.request.urlopen(req, timeout=12) as resp:
            content_type = resp.headers.get("Content-Type", "")
            data = resp.read(512)
            content_length = int(resp.headers.get("Content-Length", 99999))
            return (content_type.startswith("image/") and
                    data[:3] == b"\xff\xd8\xff" and
                    content_length > 2000)
    except Exception:
        return False


def google_books_cover(isbn):
    """Try Google Books API for a cover image by ISBN."""
    url = f"https://www.googleapis.com/books/v1/volumes?q=isbn:{isbn}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "bookr/1.0"})
        with urllib.request.urlopen(req, timeout=12) as resp:
            data = json.loads(resp.read())
            items = data.get("items", [])
            if not items:
                return None
            links = items[0].get("volumeInfo", {}).get("imageLinks", {})
            for size in ("extraLarge", "large", "medium", "small", "thumbnail"):
                img_url = links.get(size)
                if img_url:
                    return img_url.replace("http://", "https://").replace("&edge=curl", "")
    except Exception:
        pass
    return None


def ol_isbn_cover(isbn):
    """Returns the OL ISBN cover URL (cleaned)."""
    clean = isbn.replace("-", "").replace(" ", "")
    return f"https://covers.openlibrary.org/b/isbn/{clean}-L.jpg" if clean else None


conn = sqlite3.connect(str(DB_PATH))
conn.row_factory = sqlite3.Row

rows = conn.execute(
    "SELECT id, title, isbn, cover_url FROM books WHERE section='SF Masterworks' ORDER BY title"
).fetchall()

print(f"Checking {len(rows)} SF Masterworks books...\n")
updated = good = no_cover = 0

for row in rows:
    isbn = (row["isbn"] or "").replace("-", "").replace(" ", "")
    current_url = row["cover_url"] or ""

    # 1 — Is the current cover a real image?
    if current_url and check_cover(current_url):
        good += 1
        print(f"  ✓  {row['title']}")
        time.sleep(0.15)
        continue

    # 2 — Try OL ISBN cover (if isbn differs from what's in current_url)
    new_url = None
    if isbn:
        ol_url = ol_isbn_cover(isbn)
        if ol_url != current_url and check_cover(ol_url):
            new_url = ol_url

    # 3 — Fall back to Google Books
    if not new_url and isbn:
        gb_url = google_books_cover(isbn)
        if gb_url:
            new_url = gb_url

    if new_url:
        conn.execute("UPDATE books SET cover_url=? WHERE id=?", (new_url, row["id"]))
        conn.commit()
        source = "GB" if "google" in new_url else "OL"
        print(f"  ↻  [{source}] {row['title']}")
        updated += 1
    else:
        print(f"  ✗  {row['title']} (no cover found)")
        no_cover += 1

    time.sleep(0.3)

conn.close()
print(f"\nDone — {good} already good, {updated} fixed, {no_cover} still missing")
