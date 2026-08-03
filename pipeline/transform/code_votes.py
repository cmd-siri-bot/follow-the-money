"""
Vote coding, Variable 1: is this agenda item a development matter?
Per docs/03-vote-coding.md.

Tier 1 (direct join to development_applications.csv) is NOT available --
confirmed, not assumed. See docs/08-decision-log.md (2026-08-02, "docs/03's
Tier 1 vote<->development-application join does not exist"): the two
datasets share no common identifier format.

Tier 2 (committee provenance) uses the body-abbreviation code embedded in
the middle segment of `agenda_item_number` (e.g. "PH" in "2023.PH1.9"),
NOT the `committee` column in votes.csv -- the `committee` column shows
where a vote was *cast* (93.8% of all votes show committee="City Council",
because most items get their final recorded vote at Council regardless of
origin), not where the item *originated*. The abbreviation code survives
that and was verified live against secure.toronto.ca/council for the
higher-volume/ambiguous codes (see decision log for the full table).

  PH (Planning and Housing Committee) and PB (Toronto Preservation Board,
  heritage designations) -> blanket Tier 2, high confidence.
  NY/TE/SC/EY (the 4 Community Councils) -> per docs/03's own phrasing
  ("Community Council *planning* items"), these still go through Tier 3
  keyword classification rather than a blanket flag -- community councils
  handle plenty of non-planning local business.
  Everything else -> Tier 3.

No code corresponds to "Committee of Adjustment appeals" (the third
category docs/03 names) -- Committee of Adjustment is a delegated
quasi-judicial body whose decisions aren't voted on by Council directly, so
this docs/03 category has no matching population in the vote record.

Tier 3 (text classification) runs keyword matching against
`agenda_item_title` for the development-matter categories docs/03 lists,
and against a small exclude list for the categories docs/03 explicitly
carves out (capital budget lines, transit planning, unrelated parkland
acquisition) so an incidental keyword collision doesn't misfire.

Confidence:
  Tier 2 blanket (PH/PB): 0.95
  Tier 3, 2+ distinct keyword categories matched: 0.80
  Tier 3, 1 keyword category matched: 0.55  (below REVIEW_THRESHOLD -> flagged)
  Tier 3, no match: 0.90 confidence in is_development=False (absence of any
    development keyword in the title is decent but imperfect evidence)
REVIEW_THRESHOLD = 0.6 -- anything below goes to manual review per docs/03
("Anything below threshold goes to manual review, and the reviewed set
gets published").
"""
import csv
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
VOTES_CSV = ROOT / "data" / "interim" / "votes.csv"
OUT_PATH = ROOT / "data" / "interim" / "agenda_items.csv"

TIER2_BLANKET_CODES = {"PH", "PB"}
TIER2_TEXT_FILTERED_CODES = {"NY", "TE", "SC", "EY"}  # community councils

REVIEW_THRESHOLD = 0.6

# Each entry: (category_label, [regex patterns])
DEV_KEYWORD_CATEGORIES = [
    ("zoning_amendment", [r"\bzoning\s+by-?law\s+amendment", r"\brezoning\b"]),
    ("official_plan_amendment", [r"\bofficial\s+plan\s+amendment"]),
    ("site_plan", [r"\bsite\s+plan\s+(approval|control)"]),
    ("subdivision", [r"\bplan\s+of\s+subdivision", r"\bsubdivision\s+approval"]),
    ("demolition", [r"\bdemolition\s+(permit|control)\b"]),
    ("heritage", [r"\bheritage\s+designat", r"\bheritage\s+easement",
                  r"\bheritage\s+conservation\s+district", r"\bontario\s+heritage\s+act"]),
    ("section_37_cbc", [r"\bsection\s+37\b", r"\bcommunity\s+benefits?\s+charge",
                         r"\bsection\s+42\b"]),
    ("olt_appeal", [r"\bontario\s+land\s+tribunal", r"\bolt\s+appeal", r"\blocal\s+planning\s+appeal\s+tribunal",
                     r"\block?pat\b"]),
    ("inclusionary_zoning", [r"\binclusionary\s+zoning"]),
    ("rental_replacement", [r"\brental\s+replacement", r"\brental\s+housing\s+demolition"]),
]

# Explicitly carved out by docs/03 even if a stray word might overlap.
EXCLUDE_KEYWORD_PATTERNS = [
    r"\bcapital\s+budget\b",
    r"\boperating\s+budget\b",
    r"\btransit\s+(planning|project|expansion)\b",
    r"\bparkland\s+acquisition\b",
]

_ws = re.compile(r"\s+")


def normalize_text(s):
    return _ws.sub(" ", (s or "")).strip().lower()


def extract_code(agenda_item_number):
    m = re.match(r"^\d{4}\.([A-Za-z]+)\d", agenda_item_number or "")
    return m.group(1) if m else None


def classify_text(title):
    text = normalize_text(title)
    matched_categories = [
        label for label, patterns in DEV_KEYWORD_CATEGORIES
        if any(re.search(p, text) for p in patterns)
    ]
    excluded = any(re.search(p, text) for p in EXCLUDE_KEYWORD_PATTERNS)

    if excluded and not matched_categories:
        return False, 0.85, [], "excluded (capital budget / transit planning / parkland acquisition keyword, no development keyword)"

    if matched_categories:
        confidence = 0.80 if len(matched_categories) >= 2 else 0.55
        return True, confidence, matched_categories, f"matched: {', '.join(matched_categories)}"

    return False, 0.90, [], "no development keyword matched in title"


def main():
    with VOTES_CSV.open("r", newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    # One row per distinct agenda item (votes.csv is one row per member per
    # item -- classification is per item, not per vote).
    items = {}
    for r in rows:
        item_id = r["agenda_item_number"]
        if not item_id or item_id in items:
            continue
        items[item_id] = r

    out_rows = []
    tier_counts = {"2_blanket": 0, "3_keyword": 0}
    for item_id, r in items.items():
        code = extract_code(item_id)

        if code in TIER2_BLANKET_CODES:
            is_dev, confidence, tier = True, 0.95, "2_blanket"
            basis = f"Tier 2: originating body code '{code}' (Planning and Housing Committee / Toronto Preservation Board)"
            matched = []
        else:
            is_dev, confidence, matched, text_basis = classify_text(r["agenda_item_title"])
            tier = "3_keyword"
            if code in TIER2_TEXT_FILTERED_CODES:
                basis = f"Tier 3 (community council code '{code}', text-filtered per docs/03): {text_basis}"
            else:
                basis = f"Tier 3: {text_basis}"

        tier_counts[tier] += 1
        out_rows.append({
            "agenda_item_id": item_id,
            "meeting_date": r["date_time"],
            "committee": r["committee"],
            "originating_code": code or "",
            "agenda_item_title": r["agenda_item_title"],
            "is_development": is_dev,
            "classification_tier": tier,
            "confidence": round(confidence, 2),
            "matched_categories": ";".join(matched),
            "basis": basis,
            "needs_manual_review": confidence < REVIEW_THRESHOLD,
        })

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUT_PATH.open("w", newline="", encoding="utf-8") as f:
        fields = ["agenda_item_id", "meeting_date", "committee", "originating_code",
                   "agenda_item_title", "is_development", "classification_tier",
                   "confidence", "matched_categories", "basis", "needs_manual_review"]
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(out_rows)

    n_dev = sum(1 for r in out_rows if r["is_development"])
    n_review = sum(1 for r in out_rows if r["needs_manual_review"])
    print(f"Distinct agenda items: {len(out_rows)}")
    print(f"Classified as development: {n_dev} ({n_dev / len(out_rows):.1%})")
    print(f"Tier breakdown: {tier_counts}")
    print(f"Needs manual review (confidence < {REVIEW_THRESHOLD}): {n_review}")
    print(f"-> {OUT_PATH}")


if __name__ == "__main__":
    main()
