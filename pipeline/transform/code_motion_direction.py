"""
Vote coding, Variable 2: which direction is "pro-development"? Per
docs/03-vote-coding.md ("code the motion, not the vote").

Only `agenda_item_title` is a reliable text field for direction in this
data -- `vote_description` in votes.csv is almost always a terse procedural
label ("Majority required - EX27.2 - Saxe - motion 2"), not the motion's
actual content. The full amendment/motion text lives on each item's page at
secure.toronto.ca/council/agenda-item.do (confirmed reachable via a real
browser session, same as the EFD site), but reading it for every motion on
every development item (500+ motions across 246 items) was out of scope for
this pass -- logged as a follow-up enrichment, not silently skipped.

**Coverage gap, stated plainly:** only 88 of 246 development items (36%)
have explicit approve/refuse/oppose/deny language in the item title. The
other 158 (64%) get `motion_direction="ambiguous"` and are EXCLUDED from
the main specification, with a machine-readable reason, per docs/03's own
rule for deferrals ("Deferrals are genuinely ambiguous... Excluding them is
cleaner than guessing. Report how many were excluded."). The same logic is
applied here to items whose direction can't be read from the title alone --
guessing on the load-bearing variable is worse than a smaller, honest
sample. This 64% exclusion rate is itself a limitation to report on the
methodology page, not a bug to paper over.

Motion-type handling:
  Adopt Item / Adopt Item as Amended -- the item's final decision. Direction
    comes from title-keyword classification (see above).
  Amend Item / Amend Item (Additional) / Amend Item (Two-Thirds) / Amend
    Motion -- direction is UNKNOWABLE from title alone (an amendment could
    tighten or loosen the application; the title never says). Always
    "ambiguous", always excluded. This is the biggest known gap versus
    docs/03's stated method, which gives "reduce height/density/units" as a
    worked example assuming amendment text is available.
  Defer Item / Defer Item Indefinitely / Refer Item / Refer Motion --
    "deferral_or_referral", excluded per docs/03.
  Everything else (Receive Item, Waive Referral, End Debate, procedural
    motion types) -- "procedural", excluded per docs/03.

`Absent` is treated as missing (excluded) per docs/03's main specification.
`Absent(Interest Declared)` is its own excluded category, not folded into
plain absence, per docs/08-decision-log.md 2026-08-02.

Member <-> ward/office attribution uses member_terms.csv joined by name and
vote date (docs/05: "a flat lookup dict will silently misattribute votes").
"""
import csv
import re
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
VOTES_CSV = ROOT / "data" / "interim" / "votes.csv"
AGENDA_ITEMS_CSV = ROOT / "data" / "interim" / "agenda_items.csv"
MEMBER_TERMS_CSV = ROOT / "data" / "interim" / "member_terms.csv"
MOTIONS_OUT = ROOT / "data" / "interim" / "motions.csv"
VOTES_CODED_OUT = ROOT / "data" / "interim" / "votes_coded.csv"

ADOPT_TYPES = {"Adopt Item", "Adopt Item as Amended"}
AMEND_TYPES = {"Amend Item", "Amend Item (Additional)", "Amend Item (Two-Thirds)", "Amend Motion"}
DEFER_REFER_TYPES = {"Defer Item", "Defer Item Indefinitely", "Refer Item", "Refer Motion"}

RESTRICTIVE_PATTERNS = [r"\brefusal\b", r"\brefuse[ds]?\b", r"\bdeny\b", r"\bdenial\b", r"\boppose[ds]?\b"]
SUPPORTIVE_PATTERNS = [r"\bapproval\b", r"\bapprove[ds]?\b"]


def classify_title_direction(title):
    text = (title or "").lower()
    is_restrictive = any(re.search(p, text) for p in RESTRICTIVE_PATTERNS)
    is_supportive = any(re.search(p, text) for p in SUPPORTIVE_PATTERNS)
    if is_restrictive and not is_supportive:
        return "restrictive", "title contains refusal/deny/oppose language"
    if is_supportive and not is_restrictive:
        return "supportive", "title contains approval language"
    if is_restrictive and is_supportive:
        return "ambiguous", "title contains BOTH approval and refusal language -- needs manual read"
    return "ambiguous", "no explicit approve/refuse/oppose language in item title"


def motion_direction_for(motion_type, item_title, is_development):
    if not is_development:
        return "not_applicable", "item is not a development matter", False
    if motion_type in ADOPT_TYPES:
        direction, reason = classify_title_direction(item_title)
        included = direction in ("supportive", "restrictive")
        return direction, reason, included
    if motion_type in AMEND_TYPES:
        return "ambiguous", "amendment content not available in vote record (title-only classification, out of scope for this pass)", False
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
    member_by_name = load_member_terms()

    motions = {}  # motion_key -> motion record
    coded_votes = []
    unmatched_members = set()

    for r in vote_rows:
        item_id = r["agenda_item_number"]
        item = agenda_items.get(item_id)
        is_dev = item["is_development"] == "True" if item else False
        tier = item["classification_tier"] if item else ""
        confidence = item["confidence"] if item else ""

        direction, direction_reason, motion_included = motion_direction_for(
            r["motion_type"], r["agenda_item_title"], is_dev
        )

        motion_key = f"{item_id}|{r['date_time']}|{r['vote_description']}"
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
                   "motion_direction", "direction_basis"]
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
    dev_adopt = [m for m in dev_motions if m["motion_type"] in ADOPT_TYPES]
    dev_adopt_resolved = [m for m in dev_adopt if m["motion_direction"] in ("supportive", "restrictive")]
    included_votes = [v for v in coded_votes if v["included"]]

    print(f"Total motions: {len(motions)} ; on development items: {len(dev_motions)}")
    print(f"Development items' Adopt-type motions: {len(dev_adopt)} ; resolved direction: {len(dev_adopt_resolved)} "
          f"({len(dev_adopt_resolved) / len(dev_adopt):.1%})" if dev_adopt else "no adopt-type dev motions")
    print(f"Coded vote rows: {len(coded_votes)} ; included in main spec: {len(included_votes)} "
          f"({len(included_votes) / len(coded_votes):.1%})")
    print(f"Unmatched member/date combos (no member_terms match): {len(unmatched_members)}")
    if unmatched_members:
        for u in sorted(unmatched_members)[:10]:
            print("  ", u)
    print(f"-> {MOTIONS_OUT}")
    print(f"-> {VOTES_CODED_OUT}")


if __name__ == "__main__":
    main()
