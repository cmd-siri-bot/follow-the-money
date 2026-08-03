"""
Address normalization -- postal code only.

Per docs/08-decision-log.md (2026-08-02, "Contribution data comes in postal
code, not full address"): the EFD export withholds full street address under
MFIPPA s.14. Postal code is the only geographic signal available, so this
module normalizes postal codes rather than full addresses. Per docs/02, this
makes address clustering (Signal 1) a coarser, supporting signal rather than
a precise one -- a shared 6-character postal code narrows to roughly a single
side of a city block or a single large building, not one household, so it is
a much weaker "same address" claim than a street address would be. That
weakness is surfaced in the `basis` string, not hidden.

Verified 2026-08-02: all 24,005 rows in data/interim/contributions.csv match
the full Canadian postal code pattern (A1A 1A1) -- no malformed values to
handle.
"""
import re

_POSTAL_RE = re.compile(r"^([A-Za-z]\d[A-Za-z])\s?(\d[A-Za-z]\d)$")


def normalize_postal_code(raw_postal: str) -> dict:
    """Returns the full normalized postal code and its Forward Sortation
    Area (FSA, first 3 chars) -- the FSA is a coarser fallback grouping key
    for when the full 6-char code produces clusters too small to be
    meaningful on its own."""
    raw = (raw_postal or "").strip()
    m = _POSTAL_RE.match(raw)
    if not m:
        return {
            "postal_code_raw": raw_postal,
            "postal_code_norm": None,
            "postal_fsa": None,
            "postal_is_valid": False,
        }
    full = f"{m.group(1).upper()}{m.group(2).upper()}"
    return {
        "postal_code_raw": raw_postal,
        "postal_code_norm": full,
        "postal_fsa": full[:3],
        "postal_is_valid": True,
    }
