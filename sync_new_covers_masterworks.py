#!/usr/bin/env python3
"""
Sync the SF Masterworks New Covers edition to Bookr.
- Updates cover_url + isbn for existing SF Masterworks books using the official New Covers ISBNs
- Adds missing books (owned=1 if user has them, owned=0 for wishlist)
Run on the Mini: python3 ~/bookr/sync_new_covers_masterworks.py
"""
import json, re, sqlite3, urllib.request, urllib.error, time
from pathlib import Path

DB_PATH = Path.home() / "bookr/data/shelfscan.db"
API_BASE = "http://localhost:8000"

# (owned, title, author, isbn)
# owned=1 = have it, owned=0 = wishlist
# pb ISBNs used where both hb and pb exist
NEW_COVERS = [
    (0, "The Forever War",                                 "Joe Haldeman",                      "9780575094147"),
    (0, "I Am Legend",                                     "Richard Matheson",                   "9780575094161"),
    (0, "Cities in Flight",                                "James Blish",                        "9780575094178"),
    (0, "Do Androids Dream of Electric Sheep?",            "Philip K. Dick",                     "9780575094185"),
    (0, "The Stars My Destination",                        "Alfred Bester",                      "9780575094192"),
    (0, "Babel-17",                                        "Samuel R. Delany",                   "9780575094208"),
    (0, "Lord of Light",                                   "Roger Zelazny",                      "9780575094215"),
    (0, "The Fifth Head of Cerberus",                      "Gene Wolfe",                         "9780575094222"),
    (0, "Gateway",                                         "Frederik Pohl",                      "9780575094239"),
    (0, "The Rediscovery of Man",                          "Cordwainer Smith",                   "9780575094246"),
    (1, "Inverted World",                                  "Christopher Priest",                 "9780575082106"),
    (0, "Cat's Cradle",                                    "Kurt Vonnegut",                      "9780575081956"),
    (0, "Childhood's End",                                 "Arthur C. Clarke",                   "9780575082359"),
    (0, "The Island of Doctor Moreau",                     "H. G. Wells",                        "9781473217997"),
    (0, "Dhalgren",                                        "Samuel R. Delany",                   "9780575090996"),
    (0, "The Time Machine",                                "H. G. Wells",                        "9781473217973"),
    (0, "Helliconia",                                      "Brian Aldiss",                       "9780575086159"),
    (0, "The Food of the Gods",                            "H. G. Wells",                        "9781473218017"),
    (0, "The Body Snatchers",                              "Jack Finney",                        "9780575085312"),
    (0, "The Female Man",                                  "Joanna Russ",                        "9780575094994"),
    (0, "Arslan",                                          "M. J. Engh",                         "9780575095014"),
    (0, "The Difference Engine",                           "William Gibson",                     "9780575099401"),
    (0, "The Prestige",                                    "Christopher Priest",                 "9780575099418"),
    (0, "Greybeard",                                       "Brian Aldiss",                       "9780575071131"),
    (1, "Sirius",                                          "Olaf Stapledon",                     "9780575099425"),
    (0, "Hyperion",                                        "Dan Simmons",                        "9780575099432"),
    (0, "City",                                            "Clifford D. Simak",                  "9780575105232"),
    (0, "Hellstrom's Hive",                                "Frank Herbert",                      "9780575101081"),
    (0, "Of Men and Monsters",                             "William Tenn",                       "9780575099449"),
    (0, "R.U.R. and War with the Newts",                   "Karel Capek",                        "9780575099456"),
    (1, "The Affirmation",                                 "Christopher Priest",                 "9780575099463"),
    (1, "Floating Worlds",                                 "Cecelia Holland",                    "9780575108233"),
    (0, "Rogue Moon",                                      "Algis Budrys",                       "9780575108004"),
    (1, "Dangerous Visions",                               "Harlan Ellison",                     "9780575108028"),
    (1, "Odd John",                                        "Olaf Stapledon",                     "9780575072244"),
    (1, "The Fall of Hyperion",                            "Dan Simmons",                        "9780575099487"),
    (0, "The Hitchhiker's Guide to the Galaxy",            "Douglas Adams",                      "9780575115347"),
    (0, "The War of the Worlds",                           "H. G. Wells",                        "9781473218024"),
    (1, "Synners",                                         "Pat Cadigan",                        "9780575119543"),
    (0, "Sarah Canary",                                    "Karen Joy Fowler",                   "9780575131361"),
    (1, "Ammonite",                                        "Nicola Griffith",                    "9780575118232"),
    (0, "The Continuous Katherine Mortenhoe",              "D. G. Compton",                      "9780575118317"),
    (0, "Frankenstein",                                    "Mary Shelley",                       "9780575099609"),
    (0, "Roadside Picnic",                                 "Arkady and Boris Strugatsky",        "9780575093133"),
    (0, "Riddley Walker",                                  "Russell Hoban",                      "9780575119512"),
    (0, "Doomsday Book",                                   "Connie Willis",                      "9780575131095"),
    (1, "Unquenchable Fire",                               "Rachel Pollack",                     "9780575118546"),
    (0, "The Caltraps of Time",                            "David I. Masson",                    "9780575118287"),
    (0, "Engine Summer",                                   "John Crowley",                       "9780575082816"),
    (0, "Take Back Plenty",                                "Colin Greenland",                    "9780575119529"),
    (0, "Slow River",                                      "Nicola Griffith",                    "9780575118256"),
    (1, "The Gate to Women's Country",                     "Sheri S. Tepper",                    "9780575131040"),
    (0, "The Sea and Summer",                              "George Turner",                      "9780575118690"),
    (0, "The Invisible Man",                               "H. G. Wells",                        "9781473217980"),
    (0, "A Canticle for Leibowitz",                        "Walter M. Miller",                   "9780575073579"),
    (0, "Wasp",                                            "Eric Frank Russell",                 "9780575129047"),
    (0, "To Say Nothing of the Dog",                       "Connie Willis",                      "9780575113121"),
    (0, "The Gods Themselves",                             "Isaac Asimov",                       "9780575129054"),
    (0, "This Is the Way the World Ends",                  "James Morrow",                       "9780575081185"),
    (0, "The First Men in the Moon",                       "H. G. Wells",                        "9781473218000"),
    (0, "The Deep",                                        "John Crowley",                       "9780575082649"),
    (0, "Time is the Fire: The Best of Connie Willis",     "Connie Willis",                      "9780575131149"),
    (0, "No Enemy But Time",                               "Michael Bishop",                     "9780575093119"),
    (0, "Double Star",                                     "Robert A. Heinlein",                 "9780575122031"),
    (0, "Revelation Space",                                "Alastair Reynolds",                  "9780575129061"),
    (0, "Random Acts of Senseless Violence",               "Jack Womack",                        "9780575132306"),
    (0, "Transfigurations",                                "Michael Bishop",                     "9780575093096"),
    (0, "The Restaurant at the End of the Universe",       "Douglas Adams",                      "9781473200661"),
    (0, "The Door Into Summer",                            "Robert A. Heinlein",                 "9780575120723"),
    (0, "Life, the Universe and Everything",               "Douglas Adams",                      "9781473200678"),
    (0, "Dr. Bloodmoney",                                  "Philip K. Dick",                     "9781473201682"),
    (0, "Half Past Human",                                 "T. J. Bass",                         "9780575129627"),
    (0, "The Long Tomorrow",                               "Leigh Brackett",                     "9780575131569"),
    (0, "The Godwhale",                                    "T. J. Bass",                         "9780575129931"),
    (0, "Jem",                                             "Frederik Pohl",                      "9781473201705"),
    (0, "The Shrinking Man",                               "Richard Matheson",                   "9781473201699"),
    (0, "A Case of Conscience",                            "James Blish",                        "9781473205437"),
    (0, "Her Smoke Rose Up Forever",                       "James Tiptree, Jr.",                 "9781473203242"),
    (0, "Stand on Zanzibar",                               "John Brunner",                       "9781473206373"),
    (0, "Mission of Gravity",                              "Hal Clement",                        "9781473206380"),
    (0, "The Word for World Is Forest",                    "Ursula K. Le Guin",                  "9781473205789"),
    (0, "Downward to the Earth",                           "Robert Silverberg",                  "9781473211926"),
    (1, "Hard to Be a God",                                "Arkady and Boris Strugatsky",        "9781473208292"),
    (0, "Night Lamp",                                      "Jack Vance",                         "9781473208926"),
    (0, "Life During Wartime",                             "Lucius Shepard",                     "9781473211933"),
    (0, "Nova",                                            "Samuel R. Delany",                   "9781473211919"),
    (1, "Monday Begins on Saturday",                       "Arkady and Boris Strugatsky",        "9781473202214"),
    (0, "Dark Benediction",                                "Walter M. Miller Jr.",               "9781473211940"),
    (0, "The Wind's Twelve Quarters and The Compass Rose", "Ursula K. Le Guin",                  "9781473205765"),
    (0, "Dying of the Light",                              "George R. R. Martin",                "9781473212527"),
    (1, "A Fire Upon the Deep",                            "Vernor Vinge",                       "9781473211957"),
    (0, "Norstrilia",                                      "Cordwainer Smith",                   "9781473212534"),
    (0, "Limbo",                                           "Bernard Wolfe",                      "9781473212473"),
    (0, "The Day of the Triffids",                         "John Wyndham",                       "9781473212671"),
    (1, "Fairyland",                                       "Paul J. McAuley",                    "9781473215160"),
    (1, "The Chrysalids",                                  "John Wyndham",                       "9781473212688"),
    (1, "The Man Who Fell to Earth",                       "Walter Tevis",                       "9781473213111"),
    (0, "Always Coming Home",                              "Ursula K. Le Guin",                  "9781473205802"),
    (0, "Feersum Endjinn",                                 "Iain M. Banks",                      "9781473202511"),
    (0, "A Deepness in the Sky",                           "Vernor Vinge",                       "9781473211964"),
    (0, "Starship Troopers",                               "Robert A. Heinlein",                 "9781473217485"),
    (0, "The Midwich Cuckoos",                             "John Wyndham",                       "9781473212695"),
    (0, "Swastika Night",                                  "Murray Constantine",                 "9781473214668"),
    (0, "China Mountain Zhang",                            "Maureen F. McHugh",                  "9781473214620"),
    (0, "The Book of the New Sun Volume 1: Shadow and Claw", "Gene Wolfe",                       "9781473216495"),
    (0, "The Book of the New Sun Volume 2: Sword and Citadel", "Gene Wolfe",                     "9781473212008"),
    (0, "The Left Hand of Darkness",                       "Ursula K. Le Guin",                  "9781473221628"),
    (0, "Neuromancer",                                     "William Gibson",                     "9781473217379"),
    (0, "The Shape of Things to Come",                     "H. G. Wells",                        "9781473221659"),
    (0, "The Doomed City",                                 "Arkady and Boris Strugatsky",        "9781473222281"),
    (0, "Raising the Stones",                              "Sheri S. Tepper",                    "9781473222656"),
    (0, "The Embedding",                                   "Ian Watson",                         "9781473222670"),
    (0, "Cryptozoic",                                      "Brian Aldiss",                       "9781473222731"),
]


def normalize(s):
    s = s.lower().strip()
    s = re.sub(r"[*?.,!'\-\u2019]", "", s)
    s = re.sub(r"\s+", " ", s)
    return s


def check_cover(isbn):
    url = f"https://covers.openlibrary.org/b/isbn/{isbn}-L.jpg"
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


conn = sqlite3.connect(str(DB_PATH))
conn.row_factory = sqlite3.Row

rows = conn.execute(
    "SELECT id, title FROM books WHERE section='SF Masterworks'"
).fetchall()
existing = {normalize(r["title"]): r["id"] for r in rows}

updated = added = cover_miss = 0

print(f"Existing SF Masterworks in DB: {len(existing)}")
print(f"Books in New Covers list: {len(NEW_COVERS)}\n")

for owned, title, author, isbn in NEW_COVERS:
    norm = normalize(title)
    cover_url = f"https://covers.openlibrary.org/b/isbn/{isbn}-L.jpg"

    if norm in existing:
        book_id = existing[norm]
        if check_cover(isbn):
            conn.execute(
                "UPDATE books SET isbn=?, cover_url=? WHERE id=?",
                (isbn, cover_url, book_id),
            )
            conn.commit()
            print(f"  ✓  {title}")
            updated += 1
        else:
            conn.execute("UPDATE books SET isbn=? WHERE id=?", (isbn, book_id))
            conn.commit()
            print(f"  ~  {title} (ISBN updated, no OL cover found)")
            cover_miss += 1
        time.sleep(0.2)
    else:
        payload = json.dumps({
            "title": title,
            "author": author,
            "isbn": isbn,
            "section": "SF Masterworks",
            "owned": owned,
        }).encode()
        req = urllib.request.Request(
            f"{API_BASE}/api/books",
            data=payload,
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                json.loads(resp.read())
                status = "owned" if owned else "wishlist"
                print(f"  +  {title} ({status})")
                added += 1
        except Exception as e:
            print(f"  ✗  {title} — {e}")
        time.sleep(0.5)

conn.close()
print(f"\nDone — {updated} covers updated, {added} books added, {cover_miss} ISBN-only (no OL cover)")
