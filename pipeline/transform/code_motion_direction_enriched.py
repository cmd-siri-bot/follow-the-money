"""
Vote coding, Variable 2, ENRICHED pass -- uses real scraped motion text
(data/interim/motions_with_text.csv, built by parse_motion_text.py from
the secure.toronto.ca scrape) to classify Amend-type motions' direction,
instead of code_motion_direction.py's title-only "always ambiguous" for
this motion-type group.

This is a SEPARATE output, not a replacement. Per docs/04's pre-
registration note ("both versions will be reported side by side, not
just the later one"), code_motion_direction.py and its outputs
(motions.csv, votes_coded.csv) are untouched. This script writes
motions_enriched.csv / votes_coded_enriched.csv alongside them.

Everything EXCEPT Amend-type direction classification is identical to
code_motion_direction.py: Adopt-type motions still use title-keyword
classification (the scrape didn't target those, and docs/03 already
treats title as reliable for a final adopt/refuse decision); Defer/Refer
and procedural types are unchanged.

Amend-type body-text classification follows docs/03's own worked example
literally ("Amend to reduce height/density/units -> yes = anti-
development") plus the parallel supportive case (increase/add/approve),
and generalizes to explicit refuse/restrict language for the same reason
docs/03 accepts "refuse application" as restrictive at the item level.
Same conservative rule as the title classifier: if BOTH restrictive and
supportive language fire, or neither does, the motion stays "ambiguous"
and excluded -- guessing on the primary variable is worse than a smaller
honest sample (docs/02's rule, applied here to Variable 2).
"""
import csv
import re
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
VOTES_CSV = ROOT / "data" / "interim" / "votes.csv"
AGENDA_ITEMS_CSV = ROOT / "data" / "interim" / "agenda_items.csv"
MEMBER_TERMS_CSV = ROOT / "data" / "interim" / "member_terms.csv"
MOTIONS_WITH_TEXT_CSV = ROOT / "data" / "interim" / "motions_with_text.csv"
MOTIONS_OUT = ROOT / "data" / "interim" / "motions_enriched.csv"
VOTES_CODED_OUT = ROOT / "data" / "interim" / "votes_coded_enriched.csv"

ADOPT_TYPES = {"Adopt Item", "Adopt Item as Amended"}
AMEND_TYPES = {"Amend Item", "Amend Item (Additional)", "Amend Item (Two-Thirds)", "Amend Motion"}
DEFER_REFER_TYPES = {"Defer Item", "Defer Item Indefinitely", "Refer Item", "Refer Motion"}

TITLE_RESTRICTIVE_PATTERNS = [r"\brefusal\b", r"\brefuse[ds]?\b", r"\bdeny\b", r"\bdenial\b", r"\boppose[ds]?\b"]
TITLE_SUPPORTIVE_PATTERNS = [r"\bapproval\b", r"\bapprove[ds]?\b"]

SCALE_TERMS = r"(height|density|storey|storeys|story|stories|unit|units|gross floor area|\bGFA\b|floor area)"
# Tight 3-word window (down from an initial 6-word pass that produced real
# false positives on long omnibus amendments -- see docs/08-decision-log.md,
# 2026-08-03 "Enriched motion-direction classifier: two false positives
# caught and fixed before use"). Also gated by MAX_BODY_LEN_FOR_KEYWORD
# below: a proximity regex is not a substitute for reading a multi-page
# policy amendment, and shouldn't be asked to.
BODY_RESTRICTIVE_PATTERNS = [
    rf"\breduc\w*\b(?:\W+\w+){{0,3}}\W+{SCALE_TERMS}",
    rf"{SCALE_TERMS}(?:\W+\w+){{0,3}}\W+\breduc\w*\b",
    rf"\blower\w*\b(?:\W+\w+){{0,3}}\W+{SCALE_TERMS}",
    rf"\bdecreas\w*\b(?:\W+\w+){{0,3}}\W+{SCALE_TERMS}",
    rf"\brefuse[ds]?\b(?:\W+\w+){{0,3}}\W+(the (application|portion of the application))",
    rf"\brestrict\w*\b(?:\W+\w+){{0,3}}\W+(placement|application|permission|{SCALE_TERMS})",
    rf"\bprohibit\w*\b(?:\W+\w+){{0,3}}\W+(placement|application|permission|{SCALE_TERMS})",
    rf"\blimit\w*\b(?:\W+\w+){{0,3}}\W+(placement|{SCALE_TERMS})",
    rf"\bremov\w*\b(?:\W+\w+){{0,3}}\W+(permission|{SCALE_TERMS})",
]
BODY_SUPPORTIVE_PATTERNS = [
    rf"\bincreas\w*\b(?:\W+\w+){{0,3}}\W+{SCALE_TERMS}",
    rf"{SCALE_TERMS}(?:\W+\w+){{0,3}}\W+\bincreas\w*\b",
    rf"\badditional\b(?:\W+\w+){{0,3}}\W+{SCALE_TERMS}",
    rf"\bapprove[ds]?\b(?:\W+\w+){{0,3}}\W+(the (application|portion of the application))",
]
MAX_BODY_LEN_FOR_KEYWORD = 1200


def classify_title_direction(title):
    text = (title or "").lower()
    is_restrictive = any(re.search(p, text) for p in TITLE_RESTRICTIVE_PATTERNS)
    is_supportive = any(re.search(p, text) for p in TITLE_SUPPORTIVE_PATTERNS)
    if is_restrictive and not is_supportive:
        return "restrictive", "title contains refusal/deny/oppose language"
    if is_supportive and not is_restrictive:
        return "supportive", "title contains approval language"
    if is_restrictive and is_supportive:
        return "ambiguous", "title contains BOTH approval and refusal language -- needs manual read"
    return "ambiguous", "no explicit approve/refuse/oppose language in item title"


def classify_body_direction(body_text):
    if len(body_text or "") > MAX_BODY_LEN_FOR_KEYWORD:
        return "ambiguous", (f"motion text too long ({len(body_text)} chars) for reliable keyword "
                              "classification -- likely a multi-part omnibus amendment, not a focused "
                              "clause; needs a human read, not a proximity regex")
    text = (body_text or "").lower()
    is_restrictive = any(re.search(p, text) for p in BODY_RESTRICTIVE_PATTERNS)
    is_supportive = any(re.search(p, text) for p in BODY_SUPPORTIVE_PATTERNS)
    if is_restrictive and not is_supportive:
        return "restrictive", "motion text: reduce/refuse/restrict scale or permission language"
    if is_supportive and not is_restrictive:
        return "supportive", "motion text: increase/additional/approve scale or permission language"
    if is_restrictive and is_supportive:
        return "ambiguous", "motion text contains BOTH restrictive and supportive language -- needs manual read"
    return "ambiguous", "motion text has no resolvable restrictive/supportive language"


def motion_direction_for(motion_type, item_title, is_development, motion_body_text):
    if not is_development:
        return "not_applicable", "item is not a development matter", False
    if motion_type in ADOPT_TYPES:
        direction, reason = classify_title_direction(item_title)
        included = direction in ("supportive", "restrictive")
        return direction, reason, included
    if motion_type in AMEND_TYPES:
        if motion_body_text:
            direction, reason = classify_body_direction(motion_body_text)
            included = direction in ("supportive", "restrictive")
            return direction, reason, included
        return "ambiguous", "amendment content not available (item not in the scraped 83-item Amend-type population, or vote_description didn't join)", False
    if motion_type in DEFER_REFER_TYPES:
        return "deferral_or_referral", "deferred or referred, not a decision on the item (docs/03)", False
    return "procedural", f"procedural motion type ({motion_type}), not a substantive decision (docs/03)", False


def load_member_terms():
    with MEMBER_TERMS_CSV.open("r", newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    by_name = {}
    for r in rows:
        by_name.setdefault(r["member_name"], []).append(r)
    return by_name


def find_member_term(member_by_name, full_name, vote_date):
    terms = member_by_name.get(full_name)
    if not terms:
        return None
    for t in terms:
        start = datetime.strptime(t["start_date"], "%Y-%m-%d").date()
        end = datetime.strptime(t["end_date"], "%Y-%m-%d").date() if t["end_date"] else None
        if vote_date >= start and (end is None or vote_date <= end):
            return t
    return None


def main():
    with VOTES_CSV.open("r", newline="", encoding="utf-8") as f:
        vote_rows = list(csv.DictReader(f))
    with AGENDA_ITEMS_CSV.open("r", newline="", encoding="utf-8") as f:
        agenda_items = {r["agenda_item_id"]: r for r in csv.DictReader(f)}
    with MOTIONS_WITH_TEXT_CSV.open("r", newline="", encoding="utf-8") as f:
        body_text_by_key = {r["motion_key"]: r["motion_body_text"] for r in csv.DictReader(f)}
    member_by_name = load_member_terms()

    motions = {}
    coded_votes = []
    unmatched_members = set()

    for r in vote_rows:
        item_id = r["agenda_item_number"]
        item = agenda_items.get(item_id)
        is_dev = item["is_development"] == "True" if item else False
        tier = item["classification_tier"] if item else ""
        confidence = item["confidence"] if item else ""

        motion_key = f"{item_id}|{r['date_time']}|{r['vote_description']}"
        motion_body_text = body_text_by_key.get(motion_key, "")

        direction, direction_reason, motion_included = motion_direction_for(
            r["motion_type"], r["agenda_item_title"], is_dev, motion_body_text
        )

        if motion_key not in motions:
            motions[motion_key] = {
                "motion_key": motion_key,
                "agenda_item_id": item_id,
                "agenda_item_title": r["agenda_item_title"],
                "motion_type": r["motion_type"],
                "vote_description": r["vote_description"],
                "meeting_date": r["date_time"],
                "is_development": is_dev,
                "motion_direction": direction,
                "direction_basis": direction_reason,
                "had_scraped_text": bool(motion_body_text),
            }

        full_name = f"{r['first_name']} {r['last_name']}"
        try:
            vote_date = datetime.strptime(r["date_time"][:10], "%Y-%m-%d").date()
        except ValueError:
            vote_date = None

        term = find_member_term(member_by_name, full_name, vote_date) if vote_date else None
        if term is None:
            unmatched_members.add((full_name, r["date_time"]))
            ward, office = "", ""
        else:
            ward, office = term["ward_number"], term["office"]

        raw_vote = r["vote"]
        included = motion_included
        exclusion_reason = "" if included else direction_reason
        pro_dev_vote = ""

        if raw_vote == "Absent":
            included = False
            exclusion_reason = "absent (missing per docs/03 main specification)"
        elif raw_vote == "Absent(Interest Declared)":
            included = False
            exclusion_reason = "declared conflict of interest (distinct category per docs/03, not plain absence)"
        elif included:
            pro_dev_vote = (raw_vote == "Yes") != (direction == "restrictive")

        coded_votes.append({
            "vote_id": f"{item_id}|{r['date_time']}|{full_name}",
            "member_id": full_name,
            "member_name": full_name,
            "ward": ward,
            "office": office,
            "agenda_item_id": item_id,
            "meeting_date": r["date_time"],
            "committee": r["committee"],
            "motion_type": r["motion_type"],
            "motion_direction": direction,
            "raw_vote": raw_vote,
            "pro_dev_vote": pro_dev_vote,
            "is_development": is_dev,
            "classification_tier": tier,
            "confidence": confidence,
            "included": included,
            "exclusion_reason": exclusion_reason,
        })

    MOTIONS_OUT.parent.mkdir(parents=True, exist_ok=True)
    with MOTIONS_OUT.open("w", newline="", encoding="utf-8") as f:
        fields = ["motion_key", "agenda_item_id", "agenda_item_title", "motion_type",
                   "vote_description", "meeting_date", "is_development",
                   "motion_direction", "direction_basis", "had_scraped_text"]
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(motions.values())

    with VOTES_CODED_OUT.open("w", newline="", encoding="utf-8") as f:
        fields = ["vote_id", "member_id", "member_name", "ward", "office",
                   "agenda_item_id", "meeting_date", "committee", "motion_type",
                   "motion_direction", "raw_vote", "pro_dev_vote", "is_development",
                   "classification_tier", "confidence", "included", "exclusion_reason"]
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(coded_votes)

    dev_motions = [m for m in motions.values() if m["is_development"]]
    dev_amend = [m for m in dev_motions if m["motion_type"] in AMEND_TYPES]
    dev_amend_resolved = [m for m in dev_amend if m["motion_direction"] in ("supportive", "restrictive")]
    dev_adopt = [m for m in dev_motions if m["motion_type"] in ADOPT_TYPES]
    dev_adopt_resolved = [m for m in dev_adopt if m["motion_direction"] in ("supportive", "restrictive")]
    dev_all_resolved = [m for m in dev_motions if m["motion_direction"] in ("supportive", "restrictive")]
    included_votes = [v for v in coded_votes if v["included"]]

    print(f"Total motions: {len(motions)} ; on development items: {len(dev_motions)}")
    print(f"Dev Amend-type motions: {len(dev_amend)} ; resolved (enriched): {len(dev_amend_resolved)} "
          f"({len(dev_amend_resolved)/len(dev_amend):.1%})" if dev_amend else "no amend-type dev motions")
    print(f"Dev Adopt-type motions: {len(dev_adopt)} ; resolved (unchanged, title-only): {len(dev_adopt_resolved)} "
          f"({len(dev_adopt_resolved)/len(dev_adopt):.1%})" if dev_adopt else "no adopt-type dev motions")
    print(f"ALL dev motions resolved: {len(dev_all_resolved)} of {len(dev_motions)} ({len(dev_all_resolved)/len(dev_motions):.1%})")
    print(f"Coded vote rows: {len(coded_votes)} ; included in enriched spec: {len(included_votes)} "
          f"({len(included_votes)/len(coded_votes):.1%})")
    print(f"-> {MOTIONS_OUT}")
    print(f"-> {VOTES_CODED_OUT}")


if __name__ == "__main__":
    main()
