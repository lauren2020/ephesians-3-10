"""Scripture reference detection + KJV passage resolution (shared by build_site.py)."""
import re
import pythonbible as bible
from pythonbible import Book

# canonical token (lowercase, no spaces/periods) -> Book
def _m(book, *aliases):
    return {a: book for a in aliases}

BOOK_ALIASES = {}
for d in [
    _m(Book.GENESIS, "genesis", "gen", "ge", "gn", "genesys"),
    _m(Book.EXODUS, "exodus", "exod", "exo", "ex"),
    _m(Book.LEVITICUS, "leviticus", "lev", "lv"),
    _m(Book.NUMBERS, "numbers", "num", "nm", "nu"),
    _m(Book.DEUTERONOMY, "deuteronomy", "deut", "deu", "dt"),
    _m(Book.JOSHUA, "joshua", "josh", "jos"),
    _m(Book.JUDGES, "judges", "judg", "jdg"),
    _m(Book.RUTH, "ruth", "rth", "ru"),
    _m(Book.SAMUEL_1, "1samuel", "1sam", "1sa", "1sm"),
    _m(Book.SAMUEL_2, "2samuel", "2sam", "2sa", "2sm"),
    _m(Book.KINGS_1, "1kings", "1kgs", "1ki", "1kin"),
    _m(Book.KINGS_2, "2kings", "2kgs", "2ki", "2kin"),
    _m(Book.CHRONICLES_1, "1chronicles", "1chron", "1chr", "1ch"),
    _m(Book.CHRONICLES_2, "2chronicles", "2chron", "2chr", "2ch"),
    _m(Book.EZRA, "ezra", "ezr"),
    _m(Book.NEHEMIAH, "nehemiah", "neh", "ne"),
    _m(Book.ESTHER, "esther", "esth", "est"),
    _m(Book.JOB, "job", "jb"),
    _m(Book.PSALMS, "psalms", "psalm", "psa", "ps", "pslm", "pss"),
    _m(Book.PROVERBS, "proverbs", "prov", "prv", "pro", "pr"),
    _m(Book.ECCLESIASTES, "ecclesiastes", "eccl", "ecc", "eccles", "qoh"),
    _m(Book.SONG_OF_SONGS, "songofsolomon", "song", "sos", "canticles", "ss"),
    _m(Book.ISAIAH, "isaiah", "isa", "is"),
    _m(Book.JEREMIAH, "jeremiah", "jer", "je"),
    _m(Book.LAMENTATIONS, "lamentations", "lam", "la"),
    _m(Book.EZEKIEL, "ezekiel", "ezek", "eze", "ezk"),
    _m(Book.DANIEL, "daniel", "dan", "dn"),
    _m(Book.HOSEA, "hosea", "hos", "ho"),
    _m(Book.JOEL, "joel", "jl"),
    _m(Book.AMOS, "amos", "am"),
    _m(Book.OBADIAH, "obadiah", "obad", "oba", "ob"),
    _m(Book.JONAH, "jonah", "jon", "jnh"),
    _m(Book.MICAH, "micah", "mic", "mc"),
    _m(Book.NAHUM, "nahum", "nah", "na"),
    _m(Book.HABAKKUK, "habakkuk", "hab", "hb"),
    _m(Book.ZEPHANIAH, "zephaniah", "zeph", "zep", "zp"),
    _m(Book.HAGGAI, "haggai", "hag", "hg"),
    _m(Book.ZECHARIAH, "zechariah", "zech", "zec", "zc"),
    _m(Book.MALACHI, "malachi", "mal", "ml"),
    _m(Book.MATTHEW, "matthew", "matt", "mat", "mt", "mathew"),
    _m(Book.MARK, "mark", "mrk", "mar", "mk", "mr"),
    _m(Book.LUKE, "luke", "luk", "lk", "lu"),
    _m(Book.JOHN, "john", "joh", "jhn", "jn"),
    _m(Book.ACTS, "acts", "act", "ac"),
    _m(Book.ROMANS, "romans", "rom", "ro", "rm"),
    _m(Book.CORINTHIANS_1, "1corinthians", "1cor", "1co", "1corthians"),
    _m(Book.CORINTHIANS_2, "2corinthians", "2cor", "2co", "2corthians"),
    _m(Book.GALATIANS, "galatians", "gal", "ga"),
    _m(Book.EPHESIANS, "ephesians", "eph", "ephes"),
    _m(Book.PHILIPPIANS, "philippians", "phil", "php", "pp"),
    _m(Book.COLOSSIANS, "colossians", "col", "co"),
    _m(Book.THESSALONIANS_1, "1thessalonians", "1thess", "1thes", "1th"),
    _m(Book.THESSALONIANS_2, "2thessalonians", "2thess", "2thes", "2th"),
    _m(Book.TIMOTHY_1, "1timothy", "1tim", "1ti", "1tm"),
    _m(Book.TIMOTHY_2, "2timothy", "2tim", "2ti", "2tm"),
    _m(Book.TITUS, "titus", "tit", "ti"),
    _m(Book.PHILEMON, "philemon", "philem", "phlm", "phm", "pmn"),
    _m(Book.HEBREWS, "hebrews", "heb", "hb"),
    _m(Book.JAMES, "james", "jas", "jam", "jm"),
    _m(Book.PETER_1, "1peter", "1pet", "1pe", "1pt"),
    _m(Book.PETER_2, "2peter", "2pet", "2pe", "2pt"),
    _m(Book.JOHN_1, "1john", "1jn", "1jo", "1joh"),
    _m(Book.JOHN_2, "2john", "2jn", "2jo", "2joh"),
    _m(Book.JOHN_3, "3john", "3jn", "3jo", "3joh"),
    _m(Book.JUDE, "jude", "jud", "jd"),
    _m(Book.REVELATION, "revelation", "rev", "re", "revelations", "rv"),
]:
    BOOK_ALIASES.update(d)

DISPLAY = {  # canonical display name per book
    b: b.title for b in set(BOOK_ALIASES.values())
}

# Reference regex: optional leading 1-3 (+opt space), Book word starting uppercase,
# optional period, chapter:verse, optional -verse range, optional ff.
REF_RE = re.compile(
    r"(?:([1-3])\s?)?([A-Z][A-Za-z]+)\.?\s*(\d{1,3}):\s*(\d{1,3})"
    r"(?:\s*[-–]\s*(\d{1,3}))?(ff?\.?)?"
)

def _token(g1, g2):
    return ((g1 or "") + g2).lower()

def find_refs(text):
    """Yield (match, book, chapter, vstart, vend) for valid references in text."""
    for m in REF_RE.finditer(text):
        g1, g2, ch, vs, ve, ff = m.groups()
        book = BOOK_ALIASES.get(_token(g1, g2))
        if not book:
            continue
        ch = int(ch); vs = int(vs); ve = int(ve) if ve else vs
        if ve < vs:
            ve = vs
        yield m, book, ch, vs, ve

def key_for(book, ch, vs, ve):
    return f"{book.value}.{ch}.{vs}.{ve}"

def passage(book, ch, vs, ve, context=2):
    """Build a passage dict with context verses; None if out of range."""
    try:
        n = bible.get_number_of_verses(book, ch)
    except Exception:
        return None
    if n is None or vs > n:
        return None
    ve = min(ve, n)
    lo = max(1, vs - context)
    hi = min(n, ve + context)
    verses = []
    for v in range(lo, hi + 1):
        vid = book.value * 1_000_000 + ch * 1000 + v
        try:
            txt = bible.get_verse_text(vid, version=bible.Version.KING_JAMES)
        except Exception:
            txt = ""
        verses.append({"n": v, "t": txt, "hl": vs <= v <= ve})
    label = f"{DISPLAY[book]} {ch}:{vs}" + (f"–{ve}" if ve != vs else "")
    return {"label": label, "book": DISPLAY[book], "chapter": ch, "verses": verses}

def bookmap_js():
    """token -> book number, for the browser parser."""
    return {tok: b.value for tok, b in BOOK_ALIASES.items()}
