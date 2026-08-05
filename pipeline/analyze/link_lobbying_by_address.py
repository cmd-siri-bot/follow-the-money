"""
Link lobbyist subject matters to specific council votes by street address --
a second, independent linking mechanism alongside the 2026-08-03 applicant-
identity match (development_applicants.csv), needed because that one only
covers 81 of 241 development items (those with a found Application Data
Sheet). Scoped to development/planning votes only, per 2026-08-03 "how often
do lobbyists get their way" follow-up session.

Why this works without any new scraping: development agenda item titles
almost always lead with the property's street address (e.g. "985 Woodbine
Avenue and 2078, 2086, 2100, 2102 and 2106 Danforth Avenue - Zoning By-law
Amendment..."), and lobbyist_subject_matters.csv's free-text Particulars
field turns out to name the address directly far more often than expected --
checked live: 4,873 of 7,878 development-related subject matter filings
(62%) contain a street-address-shaped string. Matching on (street number,
normalized street name) finds 82 of 241 development items connected to at
least one lobbying subject matter, 39 of them NEW beyond the 81-item
identity-matched population -- using data already in this repo, no scraping.

Confidence, stated honestly: this is a text match, not an identity match
like the applicant/owner org merge. Two tiers:
  - street_type_matched: both sides' street-type suffix (Avenue/Road/Drive/
    etc, normalized) agree -- the stronger tier.
  - street_type_mismatch_or_missing: street number+name agree but type
    differs or wasn't extractable on one side -- weaker; in principle two
    different streets could share a number+name with different types (a
    "Kingston Road" vs a hypothetical "Kingston Avenue"), though this is
    rare in Toronto's street-naming in practice. Not eliminated, flagged.

Output: data/processed/lobbying_address_matches.csv -- one row per
(agenda_item_id, subject_matter_number) match, with registrant/beneficiary
context for the side-classification step (kg_classify_lobbying_side.py).
"""
import csv
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
INTERIM = ROOT / "data" / "interim"
PROCESSED = ROOT / "data" / "processed"
OUT_PATH = PROCESSED / "lobbying_address_matches.csv"

DEV_KEYWORDS = ["Development", "Planning", "Zoning", "Land Use"]

STREET_TYPE_CANON = {
    "street": "st", "st": "st", "st.": "st",
    "avenue": "ave", "ave": "ave", "ave.": "ave",
    "road": "rd", "rd": "rd", "rd.": "rd",
    "drive": "dr", "dr": "dr", "dr.": "dr",
    "boulevard": "blvd", "blvd": "blvd", "blvd.": "blvd",
    "court": "ct", "ct": "ct", "ct.": "ct",
    "crescent": "cres", "cres": "cres", "cres.": "cres",
    "way": "way",
    "lane": "ln", "ln": "ln", "ln.": "ln",
    "place": "pl", "pl": "pl", "pl.": "pl",
    "circle": "circle", "gate": "gate", "terrace": "terrace",
    "trail": "trail", "square": "sq", "sq": "sq", "sq.": "sq",
    "parkway": "pkwy", "pkwy": "pkwy", "pkwy.": "pkwy",
}
STREET_SUFFIX_ALT = "|".join(sorted({re.escape(k) for k in STREET_TYPE_CANON}, key=len, reverse=True))
CHUNK_RE = re.compile(
    r"(?P<nums>\d[\d,\s]*(?:and\s+\d+)?)\s+"
    r"(?P<name>[A-Z][A-Za-z'.-]*(?:\s+[A-Z][A-Za-z'.-]*){0,3}?)\s+"
    rf"(?P<type>{STREET_SUFFIX_ALT})\b",
    re.IGNORECASE,
)
NUM_RE = re.compile(r"\d+")


def address_keys(text):
    """Returns {(number, name): canonical_street_type_or_None}."""
    out = {}
    for m in CHUNK_RE.finditer(text or ""):
        name = re.sub(r"[^a-z]", "", m.group("name").lower())
        if not name:
            continue
        stype = STREET_TYPE_CANON.get(m.group("type").lower().rstrip("."), None)
        for num in NUM_RE.findall(m.group("nums")):
            out[(num, name)] = stype
    return out


def is_dev_related(subject_matter_text):
    t = (subject_matter_text or "").lower()
    return any(kw.lower() in t for kw in DEV_KEYWORDS)


def load_csv(path):
    with path.open("r", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def main():
    items = load_csv(INTERIM / "agenda_items.csv")
    dev_items = [r for r in items if r["is_development"] == "True"]

    subj = load_csv(INTERIM / "lobbyist_subject_matters.csv")
    dev_subj = [r for r in subj if is_dev_related(r.get("SubjectMatter", ""))]

    bene_by_sm = {}
    for r in load_csv(INTERIM / "lobbyist_beneficiaries.csv"):
        bene_by_sm.setdefault(r["subject_matter_number"], []).append(r)

    item_keys = {}
    for r in dev_items:
        title_prefix = r["agenda_item_title"].split(" - ")[0]
        keys = address_keys(title_prefix)
        if keys:
            item_keys[r["agenda_item_id"]] = (keys, r["agenda_item_title"])

    sm_keys = {}
    for r in dev_subj:
        keys = address_keys(r.get("Particulars", ""))
        if keys:
            sm_keys.setdefault(r["SMNumber"], ({}, r))[0].update(keys)

    rows_out = []
    matched_items = set()
    for item_id, (ikeys, title) in item_keys.items():
        for sm, (skeys, sm_row) in sm_keys.items():
            shared = set(ikeys) & set(skeys)
            if not shared:
                continue
            matched_items.add(item_id)
            type_matched = any(
                ikeys[k] and skeys[k] and ikeys[k] == skeys[k]
                for k in shared
            )
            confidence = "street_type_matched" if type_matched else "street_type_mismatch_or_missing"
            beneficiaries = bene_by_sm.get(sm, [])
            bene_names = "; ".join(b.get("Name", "") for b in beneficiaries) or ""
            bene_types = "; ".join(b.get("Type", "") for b in beneficiaries) or ""
            rows_out.append({
                "agenda_item_id": item_id,
                "agenda_item_title": title,
                "matched_address_keys": "; ".join(f"{n} {name}" for n, name in sorted(shared)),
                "confidence": confidence,
                "subject_matter_number": sm,
                "subject_matter_particulars": sm_row.get("Particulars", ""),
                "registrant_type": sm_row.get("registrant_Type", ""),
                "registrant_name": f"{sm_row.get('registrant_FirstName','')} {sm_row.get('registrant_LastName','')}".strip(),
                "beneficiary_names": bene_names,
                "beneficiary_types": bene_types,
            })

    PROCESSED.mkdir(parents=True, exist_ok=True)
    with OUT_PATH.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows_out[0].keys()))
        w.writeheader()
        w.writerows(rows_out)

    n_type_matched = sum(1 for r in rows_out if r["confidence"] == "street_type_matched")
    print(f"Dev items with extractable address: {len(item_keys)} of {len(dev_items)}")
    print(f"Dev-related subject matters with extractable address: {len(sm_keys)} of {len(dev_subj)}")
    print(f"Match rows: {len(rows_out)} ({n_type_matched} street_type_matched, {len(rows_out)-n_type_matched} mismatch_or_missing)")
    print(f"Distinct agenda items matched: {len(matched_items)} of {len(dev_items)}")
    print(f"-> {OUT_PATH}")


if __name__ == "__main__":
    main()
