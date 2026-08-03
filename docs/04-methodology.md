# 04 — Methodology and Pre-Registration

**Complete and commit this file before running the analysis.** The commit timestamp is the pre-registration. That's what lets you say the specification wasn't chosen to fit the answer, and it's the difference between analysis and advocacy.

---

## Pre-registered specification

Fill in and commit *before* Phase 3.

**Primary hypothesis (H1):** Councillors with a higher share of contributions from development-affiliated donors have a higher pro-development vote rate on development-related agenda items.

**Unit of analysis:** councillor (n ≈ 26, plus mid-term membership changes).

**Primary independent variable:** share of total 2022 campaign contributions with `development_affiliation_score` ≥ threshold. Base threshold: _____ (set before running).

**Primary dependent variable:** proportion of pro-development votes on included development items.

**Primary test:** _____ (specify: Spearman correlation / OLS with controls / logistic at vote level with member random effects).

**Controls:** at minimum, ward development intensity (applications per ward, 2022–2026). Optionally: total funds raised, incumbency, ward density.

**Decision rule:** _____ (state what result would count as supporting, refuting, or failing to distinguish).

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
