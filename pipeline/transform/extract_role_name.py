"""
Clean applicant/agent/architect/owner names out of Application Data Sheet
free text (development_applicants.csv), which frequently has a mailing
address appended with no consistent delimiter (e.g. "Goldberg Group 2098
Avenue Road Toronto, ON M5M 4A8"). Also classifies the cleaned name as an
organization or a person, for routing into the knowledge graph's existing
org-key merge vs. confidence-scored person identity-linking.

Known, stated limitations (not fixed -- diminishing returns for a bounded
task): a real street name that isn't in STREET_TYPE_WORDS (e.g. "The
Donway", "Kingsway") without a following corp-suffix word can leave the
address unstripped; multi-person owner lists ("A, B and C") and a
person-signing-for-a-firm pattern ("Michael Testaguzza (The Biglieri
Group Ltd)") both get classified as a single org rather than parsed into
individuals. These produce either an inert entity that matches nothing,
or a missed person-match opportunity -- never a false identity assertion.
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from normalize_names import normalize_name  # noqa: E402

POSTAL_RE = re.compile(r"[A-Za-z]\d[A-Za-z]\s?\d[A-Za-z]\d")
STREET_TYPE_RE = re.compile(
    r"\b\d{1,6}[\w\-]*\s+(?:[A-Za-z.]+\s+){0,4}?"
    r"(?:Street|St\.?|Avenue|Ave\.?|Road|Rd\.?|Drive|Dr\.?|Boulevard|Blvd\.?|"
    r"Court|Cres(?:cent)?|Way|Lane|Place|Pl\.?|Circle|Gate|Terrace|Trail|Square|Sq\.?)\b",
    re.IGNORECASE,
)
GENERIC_ADDR_RE = re.compile(r"\b\d{1,6}\s+[A-Za-z]")
CO_RE = re.compile(r"\bc/o\b", re.IGNORECASE)

# Words that, if found immediately after a matched "address", mean the
# match was actually still part of the entity's own name (Toronto
# development companies are routinely named after the property's street
# address, e.g. "48 Grenoble Drive Limited").
CORP_SUFFIX_WORDS = {
    "ltd", "limited", "inc", "incorporated", "corp", "corporation",
    "lp", "llp", "gp", "co", "company", "developments", "holdings",
    "properties", "group", "partnership", "investments", "reit",
}

# Broader than CORP_SUFFIX_WORDS -- used to decide org vs. person, so also
# covers professional-firm words that aren't legal-entity suffixes.
ORG_INDICATOR_WORDS = CORP_SUFFIX_WORDS | {
    "architects", "architect", "planning", "planners", "consulting",
    "studio", "partners", "associates", "church", "housing", "health",
    "centre", "center", "agency", "design", "strategies", "realty",
    "development",
}

SKIP_VALUES = {"", "n/a", "n/a.", "-", "none"}


def _next_tokens_have_corp_suffix(raw, end_idx, n=4):
    rest = raw[end_idx:]
    tokens = re.findall(r"[A-Za-z]+", rest)[:n]
    return any(t.lower() in CORP_SUFFIX_WORDS for t in tokens)


def extract_name_and_postal(raw: str):
    """Returns (clean_name, postal_code). Both '' if raw is empty/placeholder."""
    raw = (raw or "").strip()
    if not raw or raw.lower() in SKIP_VALUES:
        return "", ""

    postal_match = POSTAL_RE.search(raw)
    postal = postal_match.group(0).upper().replace(" ", "") if postal_match else ""

    cut_points = []
    for m in STREET_TYPE_RE.finditer(raw):
        if not _next_tokens_have_corp_suffix(raw, m.end()):
            cut_points.append(m.start())
            break
    m2 = CO_RE.search(raw)
    if m2:
        cut_points.append(m2.start())
    if not cut_points and postal:
        for m in GENERIC_ADDR_RE.finditer(raw):
            if m.start() == 0:
                continue
            if not _next_tokens_have_corp_suffix(raw, m.end()):
                cut_points.append(m.start())
                break

    name = raw[:min(cut_points)] if cut_points else raw
    name = name.strip(" ,.()&")
    return name, postal


def classify_role_name(name: str):
    """Returns 'org', 'person', or None (empty/placeholder)."""
    if not name or name.lower() in SKIP_VALUES:
        return None
    tokens = [t for t in re.split(r"\s+", name.strip()) if t]
    if not tokens:
        return None
    lowered = [re.sub(r"[^a-z]", "", t.lower()) for t in tokens]
    if any(t in ORG_INDICATOR_WORDS for t in lowered):
        return "org"
    if re.search(r"\d", name):
        return "org"
    if len(tokens) == 1 or len(tokens) > 4:
        return "org"
    return "person"


def person_match_key(name: str):
    """Converts a 'First [Middle] Last' role name into the same
    'last, first' match_key space donors.csv / dev_sector_reference.csv
    use, by taking the last token as the surname."""
    tokens = [t for t in re.split(r"\s+", name.strip()) if t]
    if len(tokens) < 2:
        return normalize_name(name)
    last = tokens[-1]
    first_rest = " ".join(tokens[:-1])
    return normalize_name(f"{last}, {first_rest}")
