"""
Manual adjudication worksheets per docs/02-donor-classification.md:
  "Review the top 300 donors by dollar value."
  "Review every record where signals disagree."
  "Review a random sample of 100 low-score records to estimate the false
   negative rate. Report that rate on the methodology page."

Aggregates data/interim/donors.csv (one row per contribution) up to one row
per donor_id (a person can give more than once, sometimes to more than one
candidate) before ranking by dollar value -- "top 300 donors" means top 300
people, not top 300 contributions.

"Signals disagree" is interpreted as two distinct populations worth
separate attention:
  (a) name_match fired with NO structural corroboration (address/temporal) --
      the docs/02 example ("high address score but no name match, or vice
      versa") in its purest form. Small set, reviewed in full.
  (b) strong structural clustering (address+temporal, score 0.75) with NO
      name-match corroboration -- the more numerous case, where the pattern
      looks coordinated but the lobbyist-registry reference list (itself
      incomplete, see docs/08 2026-08-02 "Two docs/02 assumptions don't
      hold") didn't confirm it. Sampled, not reviewed in full (too large).

Output: audit/donor_review.csv, one worksheet with a `review_set` column
identifying which category(ies) each row belongs to.

This produces the worksheet -- it does not substitute for the human sign-off
docs/02 requires before anything naming a private donor is published. See
docs/08-decision-log.md 2026-08-02 for the first-pass review performed on
this worksheet, and its explicit limits.
"""
import csv
import random
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DONORS_CSV = ROOT / "data" / "interim" / "donors.csv"
OUT_PATH = ROOT / "audit" / "donor_review.csv"

TOP_N = 300
RANDOM_LOW_SCORE_N = 100
RANDOM_SEED = 20260802  # fixed per docs/05 "random seeds fixed and logged"


def main():
    with DONORS_CSV.open("r", newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    by_donor = defaultdict(list)
    for r in rows:
        by_donor[r["donor_id"]].append(r)

    donor_summaries = []
    for donor_id, contribs in by_donor.items():
        total = sum(float(c["amount_net"]) for c in contribs)
        max_score = max(float(c["development_affiliation_score"]) for c in contribs)
        signals = set()
        for c in contribs:
            if c["signals_fired"] != "none":
                signals.update(c["signals_fired"].split(";"))
        candidates = sorted({c["candidate"] for c in contribs})
        top_basis = max(contribs, key=lambda c: float(c["development_affiliation_score"]))["basis"]
        donor_summaries.append({
            "donor_id": donor_id,
            "name_raw": contribs[0]["name_raw"],
            "postal_code": contribs[0]["postal_code"],
            "total_amount": round(total, 2),
            "n_contributions": len(contribs),
            "candidates": ";".join(candidates),
            "max_score": max_score,
            "signals_fired": ";".join(sorted(signals)) if signals else "none",
            "basis": top_basis,
        })

    top_by_dollar = sorted(donor_summaries, key=lambda d: -d["total_amount"])[:TOP_N]
    top_ids = {d["donor_id"] for d in top_by_dollar}

    name_match_alone = [d for d in donor_summaries if d["signals_fired"] == "name_match"]

    structural_no_name = [
        d for d in donor_summaries
        if "address_cluster" in d["signals_fired"].split(";")
        and "temporal_cluster" in d["signals_fired"].split(";")
        and "name_match" not in d["signals_fired"].split(";")
    ]
    structural_no_name_sorted = sorted(structural_no_name, key=lambda d: -d["total_amount"])
    structural_sample = structural_no_name_sorted[:50]  # highest-value first
    structural_sample_ids = {d["donor_id"] for d in structural_sample}

    zero_score = [d for d in donor_summaries if d["max_score"] == 0.0]
    rng = random.Random(RANDOM_SEED)
    random_low_score = rng.sample(zero_score, min(RANDOM_LOW_SCORE_N, len(zero_score)))
    random_low_score_ids = {d["donor_id"] for d in random_low_score}

    out_rows = []
    seen = set()
    for label, group in [
        ("top_300_by_dollar", top_by_dollar),
        ("signals_disagree_name_alone", name_match_alone),
        ("signals_disagree_structural_no_name_top50", structural_sample),
        ("random_100_zero_score", random_low_score),
    ]:
        for d in group:
            key = (label, d["donor_id"])
            if key in seen:
                continue
            seen.add(key)
            row = dict(d)
            row["review_set"] = label
            row["reviewer_verdict"] = ""  # for human fill-in: confirm / overturn / uncertain
            row["reviewer_note"] = ""
            out_rows.append(row)

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUT_PATH.open("w", newline="", encoding="utf-8") as f:
        fields = ["review_set", "donor_id", "name_raw", "postal_code", "total_amount",
                   "n_contributions", "candidates", "max_score", "signals_fired", "basis",
                   "reviewer_verdict", "reviewer_note"]
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(out_rows)

    print(f"Distinct donors: {len(donor_summaries)}")
    print(f"Top 300 by dollar value: {len(top_by_dollar)} (min in set: ${top_by_dollar[-1]['total_amount']:,.2f})")
    print(f"Name-match-alone (no structural corroboration): {len(name_match_alone)} (reviewed in full)")
    print(f"Structural-no-name total population: {len(structural_no_name)}; sampled top 50 by dollar value")
    print(f"Zero-score donors: {len(zero_score)}; random sample: {len(random_low_score)} (seed={RANDOM_SEED})")
    print(f"Worksheet rows written: {len(out_rows)}")
    print(f"-> {OUT_PATH}")


if __name__ == "__main__":
    main()
