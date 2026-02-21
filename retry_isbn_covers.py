#!/usr/bin/env python3
"""
Retry fetching correct Gollancz New Covers artwork for SF Masterworks books
that have New Covers ISBNs but are currently showing generic OL id/ covers.
Run on the Mini: python3 ~/bookr/retry_isbn_covers.py
"""
import json, sqlite3, urllib.request, time
from pathlib import Path

DB_PATH = Path.home() / "bookr/data/shelfscan.db"


def check_cover(url):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "bookr/1.0"})
        with urllib.request.urlopen(req, timeout=12) as resp:
            ct = resp.headers.get("Content-Type", "")
            data = resp.read(512)
            cl = int(resp.headers.get("Content-Length", 99999))
            return ct.startswith("image/") and data[:3] == b"\xff\xd8\xff" and cl > 2000
    except Exception:
        return False


def google_books_cover(isbn):
    url = f"https://www.googleapis.com/books/v1/volumes?q=isbn:{isbn}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "bookr/1.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
        items = data.get("items", [])
        if not items:
            return None
        links = items[0].get("volumeInfo", {}).get("imageLinks", {})
        for sz in ("extraLarge", "large", "medium", "small", "thumbnail"):
            img = links.get(sz)
            if img:
                return img.replace("http://", "https://").replace("&edge=curl", "")
    except Exception as e:
        print(f"    GB error: {e}")
    return None


conn = sqlite3.connect(str(DB_PATH))
conn.row_factory = sqlite3.Row

rows = conn.execute("""
    SELECT id, title, isbn, cover_url
    FROM books
    WHERE section='SF Masterworks'
      AND cover_url LIKE '%/b/id/%'
      AND isbn IS NOT NULL AND isbn != ''
    ORDER BY title
""").fetchall()

print(f"Books with New Covers ISBNs but generic id/ cover: {len(rows)}\n")
fixed = failed = 0

for row in rows:
    isbn = row["isbn"]
    title = row["title"]

    # 1. Try OL ISBN cover (OL cover DB is updated regularly)
    ol_url = f"https://covers.openlibrary.org/b/isbn/{isbn}-L.jpg"
    if check_cover(ol_url):
        conn.execute("UPDATE books SET cover_url=? WHERE id=?", (ol_url, row["id"]))
        conn.commit()
        print(f"  ✓ [OL]  {title}")
        fixed += 1
        time.sleep(0.3)
        continue

    # 2. Fall back to Google Books — generous delay to avoid rate limiting
    time.sleep(4)
    gb_url = google_books_cover(isbn)
    if gb_url:
        conn.execute("UPDATE books SET cover_url=? WHERE id=?", (gb_url, row["id"]))
        conn.commit()
        print(f"  ✓ [GB]  {title}")
        fixed += 1
    else:
        print(f"  ✗       {title} (keeping existing cover)")
        failed += 1
    time.sleep(1)

conn.close()
print(f"\nDone — {fixed} upgraded to edition-specific cover, {failed} unchanged")
