"""
Donor industry-affiliation classification per docs/02-donor-classification.md.

Implements Signals 1-3 only. Signal 4 (occupation) is dropped: contributions.csv
has no occupation field (confirmed, docs/08-decision-log.md 2026-08-02).

Scope: contributions to Councillor and Mayor candidates only (school board
trustees and Third Party Advertisers are out of scope for v1 per docs/01
and docs/08's "Third-party advertisers deferred to v2" decision).

Nets out returned contributions: `amount_net = amount - amount_returned`
(floored at 0) is used for every score computation, clustering total, and
near-limit check. Found during manual adjudication (docs/08-decision-log.md,
2026-08-03): 64 non-self-contribution rows ($80,936 total) had a contribution
fully or partially returned to the donor -- e.g. an over-the-legal-limit
gift the campaign rejected. Using the gross `amount` credited these donors
with money the campaign never actually kept, inflating "top donor" rankings
and cluster totals. The raw `amount` (gross, as originally disclosed) and
`amount_returned` are both preserved in the output alongside `amount_net`
for transparency -- a hostile reviewer should be able to see all three.

Also excludes `contributor_type` in {"Candidate", "Candidate Spouse"} --
found during manual adjudication (docs/08-decision-log.md, 2026-08-03):
these are a candidate funding their own campaign or their spouse doing so,
under a separate (much higher) contribution limit than third-party donors.
They are definitionally not "development industry money" in the sense
STRATEGY.md's thesis is about, and their unusually large dollar amounts
(candidate self-funding isn't capped at $1,200/$2,500 like third-party
giving) were dominating the top of the "top donors by dollar value" audit
list, crowding out genuine third-party donors. 5.2% of total Councillor/
Mayor contribution dollars ($819,648 of $15,724,366) came from this
category.

--- Signal 1: postal-code clustering (per candidate) ---
Per docs/08-decision-log.md (2026-08-02, "Contribution data comes in postal
code, not full address"): the EFD export gives postal code only, not street
address. A shared 6-character Canadian postal code is a much coarser claim
than a shared street address -- roughly one side of a city block or one
large building, not one household. This signal is real but weaker than
docs/02 originally anticipated, and is weighted accordingly (see WEIGHTS
below), with the caveat stated explicitly in every basis string it appears
in.
Threshold (per docs/02, "start at 3+ donors or $3,000+ aggregate"): a
postal code is flagged, for a given candidate, if it received contributions
from 3+ distinct donors OR $3,000+ in aggregate.

**Correction made during testing (see docs/08-decision-log.md, 2026-08-02
"Signal 1 needs a near-limit gate, not just a donor-count gate"):** the
donor-count/aggregate-amount threshold alone flagged clusters with no
resemblance to docs/02's actual signature ("multiple individuals donating
at or very near the contribution limit"). E.g. one flagged cluster was 10
donors averaging $192 each (16% of the councillor limit) -- ordinary small
donors who happen to share a postal code, nothing like the signature.
Another was 8 donors averaging exactly $1,200 (100% of the limit) -- the
real pattern. `near_limit_share` (the fraction of a cluster's contributions
at or above 90% of the office's contribution limit) turned out to be
strongly bimodal across flagged clusters (a distribution check found 415 of
1,066 flagged clusters under 10% near-limit, 391 over 70%, a real valley in
between) -- so it's used both as an additional gate (ADDRESS_NEAR_LIMIT_MIN_SHARE)
and to scale the score continuously within it.

--- Signal 2: temporal clustering (per candidate) ---
Per docs/02 ("Group each candidate's contributions into windows (start with
7 days)"): for each contribution, a symmetric +/-3-day window (7-day span)
around its date is checked for how many distinct donors contributed to the
same candidate in that span. Flagged on the same 3+ distinct donor threshold
as Signal 1, for consistency.
Per docs/02, Signal 1 and Signal 2 co-occurring on the same contribution is
the "coordinated-firm pattern" (tight window, shared address) and is scored
higher than either alone.

**Correction made during testing (see docs/08-decision-log.md, 2026-08-02
"Temporal clustering alone is not a signal"):** an early version of this
script scored Signal 2 alone at the same weight as Signal 1, which fired on
78% of all in-scope contributions -- any campaign with a healthy donor base
has 3+ people giving within *some* 7-day window purely from ordinary
fundraiser timing (a gala, a deadline push near nomination day). Per docs/02
itself, temporal clustering *without* a shared address is explicitly "the
fundraiser-event pattern" -- the benign explanation, not the suspicious one.
Signal 2 alone is now recorded (for audit/cluster-listing purposes) but
contributes ~0 to the score; only its co-occurrence with Signal 1 (the
"coordinated-firm pattern") carries weight.

--- Signal 3: name matching (development-sector reference) ---
Matches donor name_norm against data/interim/dev_sector_reference.csv
(built by build_dev_reference.py from in-house lobbyist registrants on
development-related subject matters). Exact match_key match only -- no
fuzzy matching -- per docs/02's "precision over recall" instruction.
Per docs/02 ("Never classify on name alone"): a name match with no
corroborating Signal 1 or 2 on the same contribution is capped at a low
score band rather than contributing full weight.

--- Score combination ---
    WEIGHTS = {
        "address_cluster": 0.35,      # Signal 1 alone
        "temporal_cluster": 0.35,     # Signal 2 alone
        "both_structural_bonus": 0.15,# Signal 1 AND 2 together (coordinated-firm pattern)
        "name_match_corroborated": 0.35,   # Signal 3, when 1 or 2 also fired
        "name_match_uncorroborated": 0.15, # Signal 3 alone -- capped, flagged for review
    }
score = sum of applicable weights, clipped to [0, 1]. This is the BASE
setting; docs/02's sensitivity analysis (strict/base/permissive across all
three thresholds) is a Phase 3 task, not implemented here -- the threshold
constants below are named and isolated so Phase 3 can vary them.

Output: data/interim/donors.csv (one row per contribution, per docs/05's
schema) and data/interim/donor_clusters.csv (one row per flagged
address/temporal cluster).
"""
import csv
import hashlib
import sys
from bisect import bisect_left, bisect_right
from collections import defaultdict
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from normalize_addresses import normalize_postal_code  # noqa: E402
from normalize_names import normalize_name  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
CONTRIBUTIONS_CSV = ROOT / "data" / "interim" / "contributions.csv"
REFERENCE_CSV = ROOT / "data" / "interim" / "dev_sector_reference.csv"
DONORS_OUT = ROOT / "data" / "interim" / "donors.csv"
CLUSTERS_OUT = ROOT / "data" / "interim" / "donor_clusters.csv"

IN_SCOPE_OFFICES = {"Councillor", "Mayor"}
EXCLUDED_CONTRIBUTOR_TYPES = {"Candidate", "Candidate Spouse"}

ADDRESS_CLUSTER_MIN_DONORS = 3
ADDRESS_CLUSTER_MIN_AMOUNT = 3000.0
ADDRESS_NEAR_LIMIT_MIN_SHARE = 0.3  # min fraction of a cluster's donations that must be near-limit to fire
TEMPORAL_WINDOW_DAYS = 3  # +/- this many days = 7-day span
TEMPORAL_CLUSTER_MIN_DONORS = 3
NEAR_LIMIT_FRACTION = 0.9
CONTRIBUTION_LIMITS = {"Councillor": 1200.0, "Mayor": 2500.0}

WEIGHTS = {
    "address_cluster": 0.35,
    "temporal_cluster_alone": 0.0,       # ordinary fundraiser-event pattern, not scored -- see module docstring
    "coordinated_firm_bonus": 0.40,      # Signal 1 AND 2 together -- the actual pattern docs/02 describes
    "name_match_corroborated": 0.35,
    "name_match_uncorroborated": 0.15,
}


def make_donor_id(name_norm: str, postal_code_norm: str) -> str:
    key = f"{name_norm}|{postal_code_norm or ''}"
    return hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]


def load_contributions():
    with CONTRIBUTIONS_CSV.open("r", newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    return [
        r for r in rows
        if r["office"] in IN_SCOPE_OFFICES
        and r["contributor_type"] not in EXCLUDED_CONTRIBUTOR_TYPES
    ]


def load_reference():
    with REFERENCE_CSV.open("r", newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    by_key = defaultdict(list)
    for r in rows:
        by_key[r["match_key"]].append(r)
    return by_key


def enrich(rows):
    for r in rows:
        name = normalize_name(r["contributor"])
        postal = normalize_postal_code(r["postal_code"])
        r["_name"] = name
        r["_postal"] = postal
        r["_donor_id"] = make_donor_id(name["name_norm"], postal["postal_code_norm"])
        try:
            r["_date"] = datetime.strptime(r["date_received"], "%Y-%m-%d").date()
        except (ValueError, KeyError):
            r["_date"] = None
        try:
            r["_amount"] = float(r["amount"]) if r["amount"] else 0.0
        except ValueError:
            r["_amount"] = 0.0
        try:
            returned = float(r["amount_returned"]) if r["amount_returned"] else 0.0
        except ValueError:
            returned = 0.0
        r["_amount_returned"] = returned
        r["_amount_net"] = max(r["_amount"] - returned, 0.0)
    return rows


def compute_address_clusters(rows):
    """Returns (flagged_contribution_scale, cluster_records).

    flagged_contribution_scale maps row index -> near_limit_share (the
    continuous scale factor applied to WEIGHTS["address_cluster"]), only for
    rows that clear both the count/amount gate AND the near-limit gate.
    """
    groups = defaultdict(list)
    for i, r in enumerate(rows):
        if not r["_postal"]["postal_is_valid"]:
            continue
        key = (r["candidate"], r["_postal"]["postal_code_norm"])
        groups[key].append(i)

    flagged = {}
    clusters = []
    for (candidate, postal), idxs in groups.items():
        donor_ids = {rows[i]["_donor_id"] for i in idxs}
        total_amount = sum(rows[i]["_amount_net"] for i in idxs)
        if len(donor_ids) < ADDRESS_CLUSTER_MIN_DONORS and total_amount < ADDRESS_CLUSTER_MIN_AMOUNT:
            continue

        near_limit_count = 0
        for i in idxs:
            limit = CONTRIBUTION_LIMITS.get(rows[i]["office"], 1200.0)
            if rows[i]["_amount_net"] >= NEAR_LIMIT_FRACTION * limit:
                near_limit_count += 1
        near_limit_share = near_limit_count / len(idxs)

        if near_limit_share < ADDRESS_NEAR_LIMIT_MIN_SHARE:
            continue  # looks like ordinary neighbours, not the docs/02 signature -- not flagged

        for i in idxs:
            flagged[i] = near_limit_share
        clusters.append({
            "cluster_type": "address",
            "cluster_key": f"{candidate}|{postal}",
            "candidate": candidate,
            "postal_code": postal,
            "window_start": "",
            "window_end": "",
            "distinct_donors": len(donor_ids),
            "total_amount": round(total_amount, 2),
            "member_donor_ids": ";".join(sorted(donor_ids)),
            "rationale": (
                f"{len(donor_ids)} distinct donor(s) totalling ${total_amount:,.2f} "
                f"shared postal code {postal} in {candidate}'s campaign; "
                f"{near_limit_count}/{len(idxs)} ({near_limit_share:.0%}) of these "
                f"contributions at/near the office's contribution limit. "
                f"NOTE: postal code only (no street address available) -- "
                f"this is a coarser claim than a shared address, roughly a "
                f"block or large building, not necessarily one household."
            ),
        })
    return flagged, clusters


def compute_temporal_clusters(rows):
    by_candidate = defaultdict(list)
    for i, r in enumerate(rows):
        if r["_date"] is None:
            continue
        by_candidate[r["candidate"]].append(i)

    flagged = {}  # idx -> (distinct_donors_in_window, near_limit_count)
    clusters = []
    seen_windows = set()

    for candidate, idxs in by_candidate.items():
        idxs.sort(key=lambda i: rows[i]["_date"])
        dates = [rows[i]["_date"].toordinal() for i in idxs]

        for pos, i in enumerate(idxs):
            d = dates[pos]
            lo = bisect_left(dates, d - TEMPORAL_WINDOW_DAYS)
            hi = bisect_right(dates, d + TEMPORAL_WINDOW_DAYS)
            window_idxs = idxs[lo:hi]
            donor_ids = {rows[j]["_donor_id"] for j in window_idxs}

            if len(donor_ids) >= TEMPORAL_CLUSTER_MIN_DONORS:
                limit = CONTRIBUTION_LIMITS.get(rows[i]["office"], 1200.0)
                near_limit = sum(
                    1 for j in window_idxs
                    if rows[j]["_amount_net"] >= NEAR_LIMIT_FRACTION * limit
                )
                flagged[i] = (len(donor_ids), near_limit)

                window_key = (candidate, dates[lo], dates[hi - 1] if hi > lo else d)
                if window_key not in seen_windows:
                    seen_windows.add(window_key)
                    start_d = min(rows[j]["_date"] for j in window_idxs)
                    end_d = max(rows[j]["_date"] for j in window_idxs)
                    total_amount = sum(rows[j]["_amount_net"] for j in window_idxs)
                    clusters.append({
                        "cluster_type": "temporal",
                        "cluster_key": f"{candidate}|{start_d}|{end_d}",
                        "candidate": candidate,
                        "postal_code": "",
                        "window_start": str(start_d),
                        "window_end": str(end_d),
                        "distinct_donors": len(donor_ids),
                        "total_amount": round(total_amount, 2),
                        "member_donor_ids": ";".join(sorted(donor_ids)),
                        "rationale": (
                            f"{len(donor_ids)} distinct donor(s) totalling ${total_amount:,.2f} "
                            f"contributed to {candidate} between {start_d} and {end_d} "
                            f"({near_limit} of {len(window_idxs)} contributions in this window "
                            f"at/near the contribution limit)."
                        ),
                    })
    return flagged, clusters


def match_name(reference_by_key, match_key):
    return reference_by_key.get(match_key, [])


def classify(rows, reference_by_key):
    address_flagged, address_clusters = compute_address_clusters(rows)
    temporal_flagged, temporal_clusters = compute_temporal_clusters(rows)

    for i, r in enumerate(rows):
        signals_fired = []
        basis_parts = []
        score = 0.0

        has_address = i in address_flagged
        has_temporal = i in temporal_flagged
        near_limit_share = address_flagged.get(i, 0.0)

        if has_address:
            score += WEIGHTS["address_cluster"] * near_limit_share
            signals_fired.append("address_cluster")
            basis_parts.append(
                f"shares postal code {r['_postal']['postal_code_norm']} with "
                f"2+ other donors to {r['candidate']} ({near_limit_share:.0%} of "
                f"that cluster's donations at/near the limit; postal code only, "
                f"not a full address)"
            )
        if has_temporal:
            signals_fired.append("temporal_cluster")
            donor_ct, near_limit_ct = temporal_flagged[i]
            if has_address:
                score += WEIGHTS["coordinated_firm_bonus"] * near_limit_share
                basis_parts.append(
                    f"one of {donor_ct} distinct donors to {r['candidate']} within a "
                    f"7-day window ({near_limit_ct} at/near the contribution limit) "
                    f"AT THE SAME shared postal code -- coordinated-firm pattern per docs/02"
                )
            else:
                basis_parts.append(
                    f"one of {donor_ct} distinct donors to {r['candidate']} within a "
                    f"7-day window ({near_limit_ct} at/near the contribution limit), "
                    f"but at distinct postal codes -- this is the ordinary "
                    f"fundraiser-event pattern per docs/02, not scored as a signal"
                )

        ref_matches = match_name(reference_by_key, r["_name"]["match_key"])
        if ref_matches and r["_name"]["name_is_clean_split"]:
            m = ref_matches[0]
            signals_fired.append("name_match")
            if has_address or has_temporal:
                score += WEIGHTS["name_match_corroborated"]
                corrob = "corroborated by clustering above"
            else:
                score += WEIGHTS["name_match_uncorroborated"]
                corrob = "NOT corroborated by any other signal -- capped, needs manual review"
            firm = f" ({m['firm_name']})" if m["firm_name"] else ""
            basis_parts.append(
                f"name matches In-house lobbyist registrant '{m['name_raw']}', "
                f"{m['position_title']}{firm}, subject matter {m['subject_matter_number']} "
                f"({corrob})"
            )

        score = min(round(score, 4), 1.0)

        r["donor_id"] = r["_donor_id"]
        r["name_raw"] = r["_name"]["name_raw"]
        r["name_norm"] = r["_name"]["name_norm"]
        r["address_raw"] = ""  # not available -- postal code only, see postal_code_raw
        r["address_norm"] = ""
        r["postal_code"] = r["_postal"]["postal_code_norm"] or r["postal_code"]
        r["amount_returned"] = r["_amount_returned"]
        r["amount_net"] = r["_amount_net"]
        r["development_affiliation_score"] = score
        r["signals_fired"] = ";".join(signals_fired) if signals_fired else "none"
        r["basis"] = "; ".join(basis_parts) if basis_parts else (
            "no signals fired -- no shared postal code cluster, no temporal "
            "cluster, no development-sector lobbyist name match"
        )
        r["manually_reviewed"] = "False"
        r["reviewer_note"] = ""

    return rows, address_clusters + temporal_clusters


def write_donors(rows):
    fields = [
        "donor_id", "name_raw", "name_norm", "address_raw", "address_norm",
        "postal_code", "amount", "amount_returned", "amount_net",
        "date_received", "contribution_type",
        "candidate", "office", "development_affiliation_score",
        "signals_fired", "basis", "manually_reviewed", "reviewer_note",
    ]
    DONORS_OUT.parent.mkdir(parents=True, exist_ok=True)
    with DONORS_OUT.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def write_clusters(clusters):
    fields = [
        "cluster_type", "cluster_key", "candidate", "postal_code",
        "window_start", "window_end", "distinct_donors", "total_amount",
        "member_donor_ids", "rationale",
    ]
    with CLUSTERS_OUT.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(clusters)


def main():
    rows = load_contributions()
    print(f"Loaded {len(rows)} in-scope (Councillor/Mayor) contributions")
    reference_by_key = load_reference()
    rows = enrich(rows)
    rows, clusters = classify(rows, reference_by_key)
    write_donors(rows)
    write_clusters(clusters)

    scores = [r["development_affiliation_score"] for r in rows]
    fired = sum(1 for s in scores if s > 0)
    print(f"Rows with score > 0: {fired} ({fired / len(scores):.1%})")
    print(f"Score >= 0.5: {sum(1 for s in scores if s >= 0.5)}")
    print(f"Score >= 0.85: {sum(1 for s in scores if s >= 0.85)}")
    print(f"Clusters written: {len(clusters)}")
    print(f"-> {DONORS_OUT}")
    print(f"-> {CLUSTERS_OUT}")


if __name__ == "__main__":
    main()
