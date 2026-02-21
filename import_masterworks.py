#!/usr/bin/env python3
"""
One-time import script: SF Masterworks collection → Conan Librarian
Run on the Mini: python3 ~/conan-librarian/import_masterworks.py
"""
import json, time, urllib.request, urllib.error

API = "http://localhost:8000"
SECTION = "SF Masterworks"

BOOKS = [
    {"title": "The Forever War", "author": "Joe Haldeman", "isbn": "1857988086"},
    {"title": "I Am Legend", "author": "Richard Matheson", "isbn": "1857988094"},
    {"title": "Cities in Flight", "author": "James Blish", "isbn": "1857988116"},
    {"title": "Do Androids Dream of Electric Sheep?", "author": "Philip K. Dick", "isbn": "1857988132"},
    {"title": "The Stars My Destination", "author": "Alfred Bester", "isbn": "1857988140"},
    {"title": "Babel-17", "author": "Samuel R. Delany", "isbn": "1857988051"},
    {"title": "Lord of Light", "author": "Roger Zelazny", "isbn": "1857988205"},
    {"title": "The Fifth Head of Cerberus", "author": "Gene Wolfe", "isbn": "1857988175"},
    {"title": "Gateway", "author": "Frederik Pohl", "isbn": "1857988183"},
    {"title": "The Rediscovery of Man", "author": "Cordwainer Smith", "isbn": "1857988191"},
    {"title": "Earth Abides", "author": "George R. Stewart", "isbn": "1857988213"},
    {"title": "The Demolished Man", "author": "Alfred Bester", "isbn": "1857988221"},
    {"title": "A Scanner Darkly", "author": "Philip K. Dick", "isbn": "1857988477"},
    {"title": "Behold the Man", "author": "Michael Moorcock", "isbn": "1857988485"},
    {"title": "The Book of Skulls", "author": "Robert Silverberg", "isbn": "1857989147"},
    {"title": "The Time Machine and The War of the Worlds", "author": "H. G. Wells", "isbn": "1857988876"},
    {"title": "Flowers for Algernon", "author": "Daniel Keyes", "isbn": "1857989384"},
    {"title": "Man Plus", "author": "Frederik Pohl", "isbn": "1857989465"},
    {"title": "A Case of Conscience", "author": "James Blish", "isbn": "1857989244"},
    {"title": "Non-Stop", "author": "Brian Aldiss", "isbn": "1857989988"},
    {"title": "The Fountains of Paradise", "author": "Arthur C. Clarke", "isbn": "1857987217"},
    {"title": "Pavane", "author": "Keith Roberts", "isbn": "1857989376"},
    {"title": "Now Wait for Last Year", "author": "Philip K. Dick", "isbn": "1857987012"},
    {"title": "Nova", "author": "Samuel R. Delany", "isbn": "185798742X"},
    {"title": "The First Men in the Moon", "author": "H. G. Wells", "isbn": "1857987462"},
    {"title": "Blood Music", "author": "Greg Bear", "isbn": "1857987624"},
    {"title": "Jem", "author": "Frederik Pohl", "isbn": "1857987896"},
    {"title": "Flow My Tears, the Policeman Said", "author": "Philip K. Dick", "isbn": "1857983416"},
    {"title": "The Invisible Man", "author": "H. G. Wells", "isbn": "185798949X"},
    {"title": "Grass", "author": "Sheri S. Tepper", "isbn": "1857987985"},
    {"title": "The Shrinking Man", "author": "Richard Matheson", "isbn": "0575074639"},
    {"title": "The Three Stigmata of Palmer Eldritch", "author": "Philip K. Dick", "isbn": "0575074809"},
    {"title": "The Dancers at the End of Time", "author": "Michael Moorcock", "isbn": "0575074760"},
    {"title": "The Space Merchants", "author": "Frederik Pohl", "isbn": "0575075287"},
    {"title": "The Simulacra", "author": "Philip K. Dick", "isbn": "0575074604"},
    {"title": "Ringworld", "author": "Larry Niven", "isbn": "0575077026"},
    {"title": "A Maze of Death", "author": "Philip K. Dick", "isbn": "0575074612"},
    {"title": "Tau Zero", "author": "Poul Anderson", "isbn": "0575077328"},
    {"title": "Life During Wartime", "author": "Lucius Shepard", "isbn": "0575077344"},
    {"title": "Roadside Picnic", "author": "Arkady and Boris Strugatsky", "isbn": "0575079789"},
    {"title": "Mockingbird", "author": "Walter Tevis", "isbn": "0575079150"},
    {"title": "Dune", "author": "Frank Herbert", "isbn": "0575081503"},
    {"title": "The Moon Is a Harsh Mistress", "author": "Robert A. Heinlein", "isbn": "0575082410"},
    {"title": "A Canticle for Leibowitz", "author": "Walter M. Miller Jr.", "isbn": "0575072202"},
]

ok, failed = 0, []
for i, book in enumerate(BOOKS, 1):
    payload = json.dumps({**book, "section": SECTION}).encode()
    req = urllib.request.Request(
        f"{API}/api/books",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read())
            print(f"[{i:2}/{len(BOOKS)}] ✓ {result.get('title')} ({result.get('publish_year', '?')})")
            ok += 1
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        print(f"[{i:2}/{len(BOOKS)}] ✗ {book['title']} — HTTP {e.code}: {body}")
        failed.append(book["title"])
    except Exception as e:
        print(f"[{i:2}/{len(BOOKS)}] ✗ {book['title']} — {e}")
        failed.append(book["title"])
    time.sleep(0.5)  # be nice to Open Library

print(f"\nDone: {ok} added, {len(failed)} failed")
if failed:
    print("Failed:", failed)
