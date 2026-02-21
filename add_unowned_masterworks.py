#!/usr/bin/env python3
"""
Add unowned SF Masterworks books to Bookr as wishlist items (owned=0).
Run on the Mini: python3 ~/bookr/add_unowned_masterworks.py
"""
import json, urllib.request, urllib.error, time

API = "http://localhost:8000"

UNOWNED = [
    {"title": "Last and First Men", "author": "Olaf Stapledon"},
    {"title": "Martian Time-Slip", "author": "Philip K. Dick"},
    {"title": "Stand on Zanzibar", "author": "John Brunner"},
    {"title": "The Dispossessed", "author": "Ursula K. Le Guin"},
    {"title": "The Drowned World", "author": "J.G. Ballard"},
    {"title": "The Sirens of Titan", "author": "Kurt Vonnegut"},
    {"title": "Emphyrio", "author": "Jack Vance"},
    {"title": "Star Maker", "author": "Olaf Stapledon"},
    {"title": "Ubik", "author": "Philip K. Dick"},
    {"title": "Timescape", "author": "Gregory Benford"},
    {"title": "More Than Human", "author": "Theodore Sturgeon"},
    {"title": "The Centauri Device", "author": "M. John Harrison"},
    {"title": "Dr. Bloodmoney", "author": "Philip K. Dick"},
    {"title": "The City and the Stars", "author": "Arthur C. Clarke"},
    {"title": "Bring the Jubilee", "author": "Ward Moore"},
    {"title": "VALIS", "author": "Philip K. Dick"},
    {"title": "The Lathe of Heaven", "author": "Ursula K. Le Guin"},
    {"title": "The Complete Roderick", "author": "John Sladek"},
    {"title": "A Fall of Moondust", "author": "Arthur C. Clarke"},
    {"title": "Eon", "author": "Greg Bear"},
    {"title": "Time Out of Joint", "author": "Philip K. Dick"},
    {"title": "Downward to the Earth", "author": "Robert Silverberg"},
    {"title": "The Penultimate Truth", "author": "Philip K. Dick"},
    {"title": "Dying Inside", "author": "Robert Silverberg"},
    {"title": "The Child Garden", "author": "Geoff Ryman"},
    {"title": "Mission of Gravity", "author": "Hal Clement"},
    {"title": "Rendezvous with Rama", "author": "Arthur C. Clarke"},
    {"title": "Where Late the Sweet Birds Sang", "author": "Kate Wilhelm"},
    {"title": "Dark Benediction", "author": "Walter M. Miller Jr."},
    {"title": "The Man in the High Castle", "author": "Philip K. Dick"},
    {"title": "The Left Hand of Darkness", "author": "Ursula K. Le Guin"},
    {"title": "Childhood's End", "author": "Arthur C. Clarke"},
    {"title": "The Day of the Triffids", "author": "John Wyndham"},
]

print(f"Adding {len(UNOWNED)} unowned SF Masterworks books as wishlist...\n")
added = failed = 0

for book in UNOWNED:
    payload = json.dumps({
        "title": book["title"],
        "author": book["author"],
        "section": "SF Masterworks",
        "owned": 0,
    }).encode()
    req = urllib.request.Request(
        f"{API}/api/books",
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            json.loads(resp.read())
            print(f"  ✓  {book['title']}")
            added += 1
    except Exception as e:
        print(f"  ✗  {book['title']} — {e}")
        failed += 1
    time.sleep(0.5)

print(f"\nDone — {added} added, {failed} failed")
