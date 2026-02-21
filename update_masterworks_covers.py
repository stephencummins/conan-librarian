#!/usr/bin/env python3
"""
Update SF Masterworks covers to use the specific Masterworks edition covers
from Open Library's ISBN cover API.
Run on the Mini: python3 ~/bookr/update_masterworks_covers.py
"""
import sqlite3, urllib.request, urllib.error, time
from pathlib import Path

DB_PATH = Path.home() / "bookr/data/shelfscan.db"
conn = sqlite3.connect(str(DB_PATH))
conn.row_factory = sqlite3.Row

books = conn.execute(
    "SELECT id, title, isbn FROM books WHERE section='SF Masterworks' AND isbn IS NOT NULL"
).fetchall()
print(f"Checking covers for {len(books)} SF Masterworks books...\n")

updated = skipped = failed = 0

for book in books:
    isbn = (book["isbn"] or "").replace("-", "").replace(" ", "")
    if not isbn:
        continue

    cover_url = f"https://covers.openlibrary.org/b/isbn/{isbn}-L.jpg"
    try:
        req = urllib.request.Request(cover_url, headers={"User-Agent": "bookr/1.0"})
        with urllib.request.urlopen(req, timeout=12) as resp:
            content_type = resp.headers.get("Content-Type", "")
            # Read first 512 bytes to check if it's a real image
            data = resp.read(512)
            # JPEG magic bytes: FF D8 FF
            is_real = content_type.startswith("image/") and data[:3] == b"\xff\xd8\xff"
            # OL "no cover" placeholder is ~807 bytes — check size too
            content_length = int(resp.headers.get("Content-Length", 99999))

        if is_real and content_length > 2000:
            conn.execute("UPDATE books SET cover_url=? WHERE id=?", (cover_url, book["id"]))
            conn.commit()
            print(f"  ✓  {book['title']}")
            updated += 1
        else:
            print(f"  –  {book['title']} (no ISBN cover, keeping existing)")
            skipped += 1
    except urllib.error.HTTPError as e:
        print(f"  ✗  {book['title']} — HTTP {e.code}")
        failed += 1
    except Exception as e:
        print(f"  ✗  {book['title']} — {e}")
        failed += 1

    time.sleep(0.3)  # be nice to Open Library

conn.close()
print(f"\nDone — {updated} updated, {skipped} skipped (no ISBN cover), {failed} failed")
