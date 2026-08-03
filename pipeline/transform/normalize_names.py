"""
Name normalization for donors and candidates.

Per docs/05-pipeline.md: "Names: strip titles, normalize case, handle
'Last, First' vs 'First Last', preserve the original in `name_raw`."

EFD contributor names arrive as free text, mostly "Last, First [Middle]"
but with enough irregularity (organizational-looking entries, embedded
addresses, suffixes) that this stays conservative: it normalizes case and
whitespace and splits on the first comma, but does not attempt to guess at
malformed entries. Anything that doesn't look like "Last, First" is passed
through with a flag so it can be reviewed rather than silently mis-split.
"""
import re
import unicodedata

TITLES = {"mr", "mrs", "ms", "mx", "dr", "prof", "councillor", "mayor"}
SUFFIXES = {"jr", "sr", "ii", "iii", "iv"}

_WS_RE = re.compile(r"\s+")


def normalize_whitespace(s: str) -> str:
    return _WS_RE.sub(" ", s.strip())


def normalize_postal(s: str) -> str:
    """Uppercase, no internal space -- e.g. 'M5T 2C8' and 'm5t2c8' both
    become 'M5T2C8'. Source data is inconsistent on the space (~76% of
    lobbyist_subject_matters.csv's registrant_PostalCode rows have one,
    donors.csv's postal_code column never does), so any postal-code
    equality check across those two sources needs both sides run through
    this first -- comparing raw strings silently drops every
    space-formatted registrant from ever matching a donor."""
    return re.sub(r"\s+", "", (s or "").strip()).upper()


def strip_accents_for_matching(s: str) -> str:
    """Fold to ASCII for fuzzy/lookup matching only -- never for display.
    e.g. 'Bailão' -> 'Bailao'. Preserves the original elsewhere."""
    nfkd = unicodedata.normalize("NFKD", s)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def split_last_first(raw_name: str):
    """Returns (last, first, middle_or_suffix_tail, is_clean_split).

    is_clean_split=False means the value didn't match the expected
    'Last, First [Middle...]' shape (e.g. an organization name, or a name
    with no comma) -- callers should not silently drop these, they need
    the manually_reviewed path per docs/02.
    """
    name = normalize_whitespace(raw_name)
    if "," not in name:
        return name, "", "", False

    last, _, rest = name.partition(",")
    last = normalize_whitespace(last)
    rest = normalize_whitespace(rest)

    parts = rest.split(" ") if rest else []
    parts = [p for p in parts if p.lower().strip(".") not in TITLES]

    first = parts[0] if parts else ""
    tail = " ".join(parts[1:]) if len(parts) > 1 else ""

    is_clean = bool(last) and bool(first)
    return last, first, tail, is_clean


def normalize_name(raw_name: str) -> dict:
    """Full normalization record for a donor or candidate name."""
    raw = raw_name if isinstance(raw_name, str) else ""
    last, first, tail, is_clean = split_last_first(raw)

    name_norm = f"{last}, {first}".strip(", ").lower()
    name_norm = normalize_whitespace(name_norm)
    match_key = strip_accents_for_matching(name_norm)
    match_key = re.sub(r"[^a-z0-9, ]", "", match_key)

    return {
        "name_raw": raw,
        "name_last": last,
        "name_first": first,
        "name_tail": tail,
        "name_norm": name_norm,
        "match_key": match_key,
        "name_is_clean_split": is_clean,
    }
