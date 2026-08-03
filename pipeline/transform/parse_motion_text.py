"""
Parse the scraped 'Motions' section text (data/raw/agenda_item_motions/
amend_motions_raw.jsonl -- built by a browser-side scrape of
secure.toronto.ca/council/agenda-item.do, per docs/08-decision-log.md's
motion-text-scrape entry) into individual motion blocks, then join each
block's free-text body back onto the matching row(s) in motions.csv.

Scope: only the 83 development items that have at least one AMEND_TYPES
motion (Amend Item / Amend Item (Additional) / Amend Item (Two-Thirds) /
Amend Motion) were scraped -- these are exactly the motions
code_motion_direction.py currently excludes wholesale because title text
alone can't reveal direction (docs/03's own worked example assumes access
to amendment text this pipeline didn't have until now).

Parsing approach: rather than trying to perfectly reconstruct each vote's
metadata (date/result/mover), which the page renders in a genuinely
inconsistent format across eras, this joins on the one string that is
identical in both the scrape and motions.csv: the "Majority Required -
..." / "Two-Thirds Required - ..." line inside each motion's Vote
sub-block, which is the same text (mixed case) as motions.csv's
`vote_description` column. A motion block can contain more than one Vote
sub-block (multi-part motions, revotes) -- the same body text is attached
to every motions.csv row whose vote_description matches any of them.

Output: data/interim/motions_with_text.csv -- motions.csv's existing
columns plus `motion_body_text` (blank where no match found) and
`motion_text_match_basis`.
"""
import csv
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
INTERIM = ROOT / "data" / "interim"
RAW_PATH = ROOT / "data" / "raw" / "agenda_item_motions" / "amend_motions_raw.jsonl"
MOTIONS_PATH = INTERIM / "motions.csv"
OUT_PATH = INTERIM / "motions_with_text.csv"

NUM_RE = re.compile(r"^\d+[a-z]?$")
REQUIRED_RE = re.compile(r"^(Majority Required|Two-Thirds Required)\b", re.IGNORECASE)


def split_motion_blocks(lines):
    """Return list of (start_idx, end_idx) for each motion block in a
    single page section's lines (numbered 'N\n-  Motion' or bare
    'Motion' headers)."""
    starts = []
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if NUM_RE.match(line) and i + 1 < len(lines) and lines[i + 1].strip() == "-  Motion":
            starts.append(i)
            i += 2
            continue
        if line == "Motion":
            starts.append(i)
            i += 1
            continue
        i += 1
    blocks = []
    for idx, start in enumerate(starts):
        end = starts[idx + 1] if idx + 1 < len(starts) else len(lines)
        blocks.append((start, end))
    return blocks


def parse_block(lines, start, end):
    """Returns (body_text, [vote_description_keys])."""
    pos = start
    if NUM_RE.match(lines[pos].strip()) and lines[pos + 1].strip() == "-  Motion":
        pos += 2
    else:
        pos += 1  # bare "Motion" line

    if pos < end:
        pos += 1  # motion_type line (e.g. "to Amend Item (Additional)")
    if pos < end and lines[pos].strip() == "moved by":
        pos += 2  # "moved by" + mover name
    if pos < end and lines[pos].strip().startswith("(") and lines[pos].strip().endswith(")"):
        pos += 1  # result parenthetical, e.g. "(Carried)"

    body_start = pos
    body_end = end
    for i in range(pos, end):
        if lines[i].strip() == "Vote":
            body_end = i
            break
    body = "\n".join(lines[body_start:body_end]).strip()

    vote_keys = []
    for i in range(body_end, end):
        if REQUIRED_RE.match(lines[i].strip()):
            vote_keys.append(lines[i].strip().lower())
    return body, vote_keys


def parse_item_text(raw_text):
    """raw_text may contain multiple '---'-joined page sections (one per
    consideration stage). Returns list of (body_text, [vote_keys])."""
    all_motions = []
    for section in raw_text.split("\n---\n"):
        lines = section.split("\n")
        for start, end in split_motion_blocks(lines):
            body, vote_keys = parse_block(lines, start, end)
            if body and vote_keys:
                all_motions.append((body, vote_keys))
    return all_motions


def main():
    scraped = {}
    with RAW_PATH.open("r", encoding="utf-8") as f:
        for line in f:
            rec = json.loads(line)
            scraped[rec["id"]] = parse_item_text(rec["t"])

    with MOTIONS_PATH.open("r", newline="", encoding="utf-8") as f:
        motions_rows = list(csv.DictReader(f))

    matched = 0
    ambiguous = 0
    for row in motions_rows:
        row["motion_body_text"] = ""
        row["motion_text_match_basis"] = ""
        item_motions = scraped.get(row["agenda_item_id"])
        if not item_motions:
            continue
        vote_desc = row["vote_description"].strip().lower()
        hits = [body for body, keys in item_motions if vote_desc in keys]
        if len(hits) == 1:
            row["motion_body_text"] = hits[0]
            row["motion_text_match_basis"] = "exact vote_description match against scraped 'Majority/Two-Thirds Required' line"
            matched += 1
        elif len(hits) > 1:
            row["motion_body_text"] = hits[0]
            row["motion_text_match_basis"] = f"ambiguous: {len(hits)} scraped motions shared this vote_description, used first"
            ambiguous += 1

    fieldnames = list(motions_rows[0].keys())
    with OUT_PATH.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(motions_rows)

    amend_types = {"Amend Item", "Amend Item (Additional)", "Amend Item (Two-Thirds)", "Amend Motion"}
    amend_dev_rows = [r for r in motions_rows if r["is_development"] == "True" and r["motion_type"] in amend_types]
    amend_matched = sum(1 for r in amend_dev_rows if r["motion_body_text"])

    print(f"Total motions.csv rows: {len(motions_rows)}")
    print(f"Rows matched to scraped text: {matched} (+{ambiguous} ambiguous, used first hit)")
    print(f"Of {len(amend_dev_rows)} dev Amend-type motions (the actual scrape target): {amend_matched} matched ({100*amend_matched/len(amend_dev_rows):.1f}%)")
    unmatched_items = {r["agenda_item_id"] for r in amend_dev_rows if not r["motion_body_text"]}
    print(f"Dev items with at least one unmatched Amend-type motion: {len(unmatched_items)}")
    print(f"-> {OUT_PATH}")


if __name__ == "__main__":
    main()
