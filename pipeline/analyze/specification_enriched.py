"""
Phase 3 primary specification, ENRICHED pass -- identical to
specification.py in every respect except it reads
data/interim/votes_coded_enriched.csv (from the motion-text scrape +
code_motion_direction_enriched.py) instead of votes_coded.csv.

Per docs/04's pre-registration note ("both versions will be reported side
by side, not just the later one") and docs/08-decision-log.md's
2026-08-03 motion-text-scrape entry: this is a SEPARATE run, not a
replacement. specification.py and its published outputs are untouched.

Population, donor-affiliation logic, and ward-intensity control are
unchanged from the original -- the only thing that differs is which vote
rows are available to include, since the enriched motion-direction pass
resolves 4 additional Amend-type motions (was 0) that the original pass
excluded wholesale.

Outputs:
  data/processed/candidate_donor_mix_enriched.csv (donor-side numbers are
    identical to the original candidate_donor_mix.csv -- votes don't
    affect this computation at all -- written separately only for a
    self-contained enriched-run record)
  phase3-specification-result-enriched.md
"""
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from scipy import stats

ROOT = Path(__file__).resolve().parents[2]
MEMBER_TERMS_CSV = ROOT / "data" / "interim" / "member_terms.csv"
DONORS_CSV = ROOT / "data" / "interim" / "donors.csv"
VOTES_CODED_CSV = ROOT / "data" / "interim" / "votes_coded_enriched.csv"
DEV_APPS_CSV = ROOT / "data" / "interim" / "development_applications.csv"
OUT_DIR = ROOT / "data" / "processed"
CANDIDATE_MIX_OUT = OUT_DIR / "candidate_donor_mix_enriched.csv"
RESULT_OUT = ROOT / "phase3-specification-result-enriched.md"

BASE_THRESHOLD = 0.5


def load_current_members():
    mt = pd.read_csv(MEMBER_TERMS_CSV)
    current = mt[mt["end_date"].isna()].copy()
    return current


def compute_dev_affiliation_share(current_members, donors, threshold):
    donors = donors.copy()
    rows = []
    for _, m in current_members.iterrows():
        sub = donors[
            (donors["candidate"] == m["efd_candidate_name"])
            & (donors["election"] == m["source_election"])
        ]
        total_net = sub["amount_net"].sum()
        dev_net = sub.loc[sub["development_affiliation_score"] >= threshold, "amount_net"].sum()
        share = (dev_net / total_net) if total_net > 0 else np.nan
        rows.append({
            "member_id": m["member_name"],
            "ward_number": m["ward_number"],
            "office": m["office"],
            "total_raised_net": round(total_net, 2),
            "dev_linked_net": round(dev_net, 2),
            "dev_affiliation_share": share,
            "n_donors": sub["donor_id"].nunique(),
            "threshold_setting": threshold,
        })
    return pd.DataFrame(rows)


def compute_ward_intensity(dev_apps):
    apps = dev_apps.copy()
    apps = apps[apps["date_submitted"] >= "2022-01-01"]
    counts = apps.groupby("ward_number").size().rename("ward_development_intensity")
    return counts


def main():
    warnings.filterwarnings("ignore")

    current_members = load_current_members()
    donors = pd.read_csv(DONORS_CSV)

    mix_base = compute_dev_affiliation_share(current_members, donors, BASE_THRESHOLD)

    dev_apps = pd.read_csv(DEV_APPS_CSV)
    ward_intensity = compute_ward_intensity(dev_apps)
    mix_base = mix_base.merge(ward_intensity, left_on="ward_number", right_index=True, how="left")
    mix_base["ward_development_intensity"] = mix_base["ward_development_intensity"].fillna(0)

    votes = pd.read_csv(VOTES_CODED_CSV)
    votes_included = votes[votes["included"] == True].copy()  # noqa: E712
    current_ids = set(current_members["member_name"])
    votes_primary = votes_included[votes_included["member_id"].isin(current_ids)].copy()

    vote_level = votes_primary.merge(
        mix_base[["member_id", "dev_affiliation_share", "ward_development_intensity", "total_raised_net", "n_donors"]],
        on="member_id", how="left",
    )
    vote_level["pro_dev_vote"] = vote_level["pro_dev_vote"].astype(bool).astype(int)

    n_members_with_votes = vote_level["member_id"].nunique()
    n_members_with_share = mix_base["dev_affiliation_share"].notna().sum()

    model_df = vote_level.dropna(subset=["dev_affiliation_share", "ward_development_intensity"])

    logit_summary_text = "MODEL DID NOT RUN"
    logit_coef = logit_pvalue = logit_ci_low = logit_ci_high = None
    try:
        model = smf.logit(
            "pro_dev_vote ~ dev_affiliation_share + ward_development_intensity",
            data=model_df,
        ).fit(disp=0, cov_type="cluster", cov_kwds={"groups": model_df["member_id"]})
        logit_summary_text = model.summary().as_text()
        logit_coef = model.params["dev_affiliation_share"]
        logit_pvalue = model.pvalues["dev_affiliation_share"]
        ci = model.conf_int().loc["dev_affiliation_share"]
        logit_ci_low, logit_ci_high = ci[0], ci[1]
    except Exception as e:  # noqa: BLE001
        logit_summary_text = f"MODEL FAILED: {e}"

    member_level = mix_base.dropna(subset=["dev_affiliation_share"]).copy()
    member_vote_rate = votes_primary.groupby("member_id")["pro_dev_vote"].apply(
        lambda s: s.astype(bool).mean()
    ).rename("pro_dev_vote_rate")
    member_level = member_level.merge(member_vote_rate, on="member_id", how="left")
    member_level_complete = member_level.dropna(subset=["pro_dev_vote_rate"])

    spearman_rho = spearman_p = None
    if len(member_level_complete) >= 3:
        spearman_rho, spearman_p = stats.spearmanr(
            member_level_complete["dev_affiliation_share"],
            member_level_complete["pro_dev_vote_rate"],
        )

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    mix_base.to_csv(CANDIDATE_MIX_OUT, index=False)

    with RESULT_OUT.open("w", encoding="utf-8") as f:
        f.write("# Phase 3 — Primary Specification Result (ENRICHED)\n\n")
        f.write("Generated by pipeline/analyze/specification_enriched.py against votes_coded_enriched.csv "
                "(motion-text scrape, docs/08-decision-log.md 2026-08-03). Reported alongside, not instead "
                "of, phase3-specification-result.md per docs/04's pre-registration note.\n\n")
        f.write(f"Base threshold: {BASE_THRESHOLD}\n\n")
        f.write("## Population\n\n")
        f.write(f"- Currently sitting members: {len(current_members)}\n")
        f.write(f"- Members with a defined dev_affiliation_share (total_raised_net > 0): {n_members_with_share}\n")
        f.write(f"- Members with at least one included vote: {n_members_with_votes}\n")
        f.write(f"- Members in the final logistic model (share + votes + ward intensity all present): "
                f"{model_df['member_id'].nunique() if len(model_df) else 0}\n")
        f.write(f"- Included vote rows in the primary model: {len(model_df)}\n\n")

        f.write("## Vote-level logistic regression (primary test)\n\n")
        f.write("`pro_dev_vote ~ dev_affiliation_share + ward_development_intensity`, "
                "clustered SE by member.\n\n")
        f.write("```\n" + logit_summary_text + "\n```\n\n")
        if logit_coef is not None:
            f.write(f"**dev_affiliation_share coefficient: {logit_coef:.4f} "
                    f"(p={logit_pvalue:.4f}, 95% CI [{logit_ci_low:.4f}, {logit_ci_high:.4f}])**\n\n")

        f.write("## Member-level Spearman correlation (illustrative/secondary)\n\n")
        f.write(f"n = {len(member_level_complete)}\n\n")
        if spearman_rho is not None:
            f.write(f"rho = {spearman_rho:.4f}, p = {spearman_p:.4f}\n\n")
        else:
            f.write("Not computed (fewer than 3 members with both a defined share and a vote rate).\n\n")

        f.write("## Member-level table\n\n")
        f.write(member_level.to_string(index=False))
        f.write("\n")

    print(f"Currently sitting members: {len(current_members)}")
    print(f"Members with defined dev_affiliation_share: {n_members_with_share}")
    print(f"Members with >=1 included vote: {n_members_with_votes}")
    print(f"Model rows: {len(model_df)}, members in model: {model_df['member_id'].nunique() if len(model_df) else 0}")
    if logit_coef is not None:
        print(f"Logistic: coef={logit_coef:.4f} p={logit_pvalue:.4f} CI=[{logit_ci_low:.4f},{logit_ci_high:.4f}]")
    else:
        print("Logistic model did not produce a result -- see", RESULT_OUT)
    if spearman_rho is not None:
        print(f"Spearman: rho={spearman_rho:.4f} p={spearman_p:.4f} (n={len(member_level_complete)})")
    print(f"-> {CANDIDATE_MIX_OUT}")
    print(f"-> {RESULT_OUT}")


if __name__ == "__main__":
    main()
