# 04 — Methodology and Pre-Registration

**Complete and commit this file before running the analysis.** The commit timestamp is the pre-registration. That's what lets you say the specification wasn't chosen to fit the answer, and it's the difference between analysis and advocacy.

---

## Pre-registered specification

Fill in and commit *before* Phase 3.

**Primary hypothesis (H1):** Councillors with a higher share of contributions from development-affiliated donors have a higher pro-development vote rate on development-related agenda items.

**Unit of analysis:** councillor (n ≈ 26, plus mid-term membership changes).

**Primary independent variable:** `dev_affiliation_share` — for each sitting member, the share (by dollar value, `amount_net`) of their in-scope campaign contributions (Councillor/Mayor office, `contributor_type` = Individual only — self/spouse funding excluded per docs/08-decision-log.md 2026-08-03) with `development_affiliation_score` ≥ threshold. **Base threshold: 0.5** — set 2026-08-03, before running. 0.5 requires at least one fully corroborated signal (the address+temporal "coordinated-firm pattern" alone scores 0.75; a corroborated name match alone scores 0.35 combined with either structural signal; an uncorroborated name match alone, 0.15, does not clear 0.5). Per docs/02's sensitivity-analysis requirement, this also gets run at a stricter and a more permissive threshold and all three are reported (see Sensitivity analysis, below) — 0.5 is the base setting only, not the sole result.

**Contributions are attributed per-member using `member_terms.csv`'s `source_election`** (docs/08-decision-log.md 2026-08-02, "By-elections require separate contribution exports"): the 2022 general campaign for members elected then, the relevant by-election campaign for the four members who weren't (Kandavel, Chernos Lin, Shan, Chow) — never a blend of both. Kandavel's losing 2022 Ward 20 run is excluded from his figure per the same log entry ("donor base = the campaign that won the seat they currently hold").

**Primary dependent variable:** `pro_dev_vote` (binary) at the individual vote level, from `votes_coded.csv` where `included = True` — i.e., Adopt-type motions on development items whose title gave an unambiguous approve/refuse signal, with the member not absent. **Set 2026-08-03: given this is only 2.6% of all recorded votes (1,176 of 45,665 — see docs/08-decision-log.md 2026-08-02, "Variable 2... a real, large coverage gap"), this specification will be rerun if the motion-text scrape (still open) meaningfully grows the included set, and both versions will be reported side by side, not just the later one.**

**Primary test: logistic regression at the vote level** — `pro_dev_vote ~ dev_affiliation_share + ward_development_intensity`, standard errors clustered by member (`member_id`), per docs/04's own reasoning: more power than the member-level correlation and it handles the unbalanced number of included votes per member (some members have only 1-2 included votes given the 2.6% rate; a member-level correlation alone would treat that member's single vote as equally informative as another member's twelve, which clustering handles more honestly). **Set 2026-08-03.** The member-level Spearman correlation (`dev_affiliation_share` vs. each member's own pro-development vote rate, n≈26) is reported alongside as the illustrative/secondary view, exactly as docs/04 originally suggested — not as the headline.

**Controls:** ward development intensity (applications per ward, 2022–2026, from `development_applications.csv`'s `ward_number`/`date_submitted`) — required minimum, included in the base specification. Total funds raised — included as a secondary control if it does not produce unstable collinearity with `dev_affiliation_share` (checked, not assumed). Incumbency and ward density — **not included in v1**: incumbency would require pulling the 2018–2022 vote record (resource ID logged in docs/01 but never fetched) to determine which members served the prior term, out of scope for this pass; ward density was never sourced. Both logged here as named, deliberate omissions rather than silent gaps.

**Decision rule, set 2026-08-03:**
- **H1 supported** if the `dev_affiliation_share` coefficient is positive with a 95% CI excluding zero, after controlling for ward development intensity, **and** this holds at 2 of the 3 sensitivity thresholds (strict/base/permissive).
- **H1 refuted** if the coefficient is statistically indistinguishable from zero, or negative, across all three thresholds.
- **Result reported as "the data cannot distinguish these hypotheses"** if the direction of the effect flips across the three thresholds, or if the 95% CI at the base threshold is wide enough to span both an economically meaningful positive effect and an economically meaningful negative effect (i.e., the interval doesn't rule out either "money predicts votes" or "money predicts nothing" as the true state).
- In every case: leave-one-out diagnostics (member-level) are run and published alongside the headline result per docs/04's own n≈26 warning, regardless of which of the three outcomes above obtains.

---

## n = 26. Take this seriously.

Twenty-six councillors is a very small sample. This is the honest constraint on the whole project and it should shape the claims, not be buried in a footnote.

Implications:
- One or two influential observations can drive any correlation. **Run leave-one-out diagnostics and publish them.**
- Confidence intervals will be wide. Show them. A point estimate without an interval on n=26 is misleading.
- Consider the vote-level specification (thousands of votes, member-clustered errors) as the primary and the member-level correlation as illustrative. More power, and it handles the unbalanced number of votes per member.
- **Do not report a p-value as though it settles anything.** Report effect size and interval, and describe the uncertainty in words.

Pooling the 2018–2022 term roughly doubles the sample and is worth considering — but the councillors overlap heavily, so observations aren't independent. If you pool, model it properly or don't pool.

---

## The confounder that will be raised first

**Ward composition.** Councillors representing downtown and high-growth wards face more development votes *and* attract more development-sector attention and money. That alone could produce the entire correlation with no influence mechanism whatsoever.

This is the obvious objection and the analysis is worthless if it isn't addressed head-on:

1. Control for ward development intensity in the main specification
2. Publish the ward-stratified version alongside the pooled one
3. Look at within-ward variation across terms where members changed

If the correlation vanishes once you control for ward, **that is the finding** and it's a genuinely interesting one: money follows development activity rather than buying votes. Publish it with the same prominence you'd have given the opposite result.

Other confounders to name: ideological priors (a councillor's general growth orientation attracts aligned donors), incumbency and fundraising capacity, and reverse causality — donors giving to councillors who were *already* going to vote their way. Nothing in this design can rule out reverse causality. Say so.

---

## What we will and will not claim

**Will claim:**
- Descriptive statistics on the composition of campaign funding
- Correlations, with intervals and sensitivity ranges
- Identification of specific donation clusters, with the evidence shown
- That the data does or does not support H1

**Will not claim:**
- Causation. Not in the headline, not in a chart title, not implicitly through verb choice.
- That any individual acted improperly
- That any donation was coordinated in a legal sense
- That contributions are illegitimate. **They are lawful, disclosed, and capped.** The question is whether they correlate with anything, not whether they should exist.

Every donation in this dataset was made legally by a private individual exercising a political right. The framing is *pattern description*, and the language on the site must reflect that at every point.

---

## Publish the null

Write the null-result version of the hero copy **before running the analysis**. If you only draft the "money predicts votes" headline, you have created an incentive to find it.

The null is a good story: "Toronto banned corporate donations in 2009 to reduce development influence. Here's what the data shows about whether the individual-donation channel replaced it — and the answer is less than you'd expect." That's publishable and, for a portfolio, arguably more impressive than a splashy correlation.

---

## Reproducibility

- Every figure on the site traces to a script in `pipeline/`
- Random seeds fixed and logged
- LLM-assisted classification: model version, prompt, and date recorded in the decision log; outputs committed so a rerun is comparable
- `make all` reproduces every published artifact from raw data
- Raw scrapes archived so the extract is reproducible even if EFD changes

---

## Methodology page: required sections

The public page must contain, in this order:

1. The question, in one sentence
2. Data sources with links and access dates
3. How development affiliation was inferred, including the **measured error rate** from the audit sample
4. How development items and vote direction were coded, with the full definition
5. The specification, with a link to the pre-registration commit
6. Sensitivity analysis across all three thresholds
7. **Limitations** — recorded-vote sampling bias, n=26, the `Absent` ambiguity, third-party advertiser leakage, reverse causality
8. What the analysis does not claim
9. Every dataset as a download, plus the repo link
10. A correction policy and a contact address

Section 7 should be long, specific, and unhedged. Volunteering your own weaknesses is what separates this from advocacy, and it's the section a hiring manager will actually read closely.
