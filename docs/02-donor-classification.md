# 02 — Donor Classification

**This is the critical path.** Everything else in the project is standard data engineering; this is the part that requires judgment and the part that will be attacked.

---

## The problem

Corporate donations are illegal in Ontario municipal elections. Every contribution in the file comes from a named individual. There is no industry field, no employer field, and no corporate flag.

So the question "how much development-industry money did this councillor receive?" has no direct answer in the data. It has to be **inferred**, and inference under uncertainty is exactly where this kind of analysis usually goes wrong — either by being too credulous (calling every donor named in a news article a developer) or too timid (refusing to classify and producing nothing).

The way through is to treat industry affiliation as a **probabilistic label with an auditable basis**, never a binary assertion, and to publish the whole classification table so anyone can check your work.

---

## The signature you're looking for

The pattern that documents coordinated industry giving is well-established in Ontario reporting. Its components:

- Multiple individuals donating **at or very near the contribution limit** ($1,200 council / $2,500 mayoral)
- Donations **clustered within a short window** — often days
- Donors sharing a **common address**, or addresses resolving to one corporate location
- Donors sharing **surnames** (family-held firms are common in the GTA development sector)
- The associated firm having **active business before council** in the same period

A documented example from the Ontario Liberal leadership race: $33,500 arriving from ten individuals whose names matched executives of a single Vaughan-based developer, each at the maximum, nine of the ten within three days. No single element of that is remarkable. The combination is the signal.

**None of this is illegal.** Individuals in any industry may donate to whomever they like. The analysis describes a pattern; it does not allege wrongdoing. Hold that line in every piece of copy — see `docs/07`.

---

## Method: four signals, scored

Build each signal independently, then combine. Never collapse to a binary.

### Signal 1 — Address clustering (strongest)

Normalize addresses aggressively (case, suite/unit notation, street type abbreviations, postal code formatting), then group.

- Flag any address contributing to a given candidate above a threshold (start at 3+ donors or $3,000+ aggregate)
- Geocode flagged addresses and check whether they resolve to commercial rather than residential property — a cluster at an office tower is a very different object from a cluster at a triplex
- **Watch for the false positive:** family homes legitimately produce 2–3 donors at one address. Set the threshold high enough that ordinary households don't trip it, and eyeball everything near the boundary.

### Signal 2 — Temporal clustering

Group each candidate's contributions into windows (start with 7 days). Within a window, compute donor count, share at/near the limit, and address diversity.

A tight window of maxed donations from distinct addresses is the fundraiser-event pattern; a tight window from *shared* addresses is the coordinated-firm pattern. The combination of Signals 1 and 2 is much more informative than either alone.

### Signal 3 — Name matching against firm leadership

Assemble a reference list of development-sector firms active in Toronto 2022–2026 — buildable from the development applications dataset (applicant names) and the lobbyist registry (client names). Then match donor names against publicly listed directors and officers.

- Ontario Business Registry gives directors for some entities
- Lobbyist registry filings name individuals
- Development application applicant fields name firms directly

**Precision over recall here.** A false positive on a named individual is a reputational harm to a real person; a false negative is a slightly weaker finding. Require exact or near-exact name match plus at least one corroborating signal. Never classify on name alone.

### Signal 4 — Sectoral occupation inference

Some filings capture occupation. Where present, use it. Where absent, do not guess from name or address alone.

---

## Combining into a score

```
development_affiliation_score ∈ [0, 1]
```

Weight address and temporal clustering highest (they're structural and don't depend on identifying anyone), name matching lower (higher harm if wrong), occupation as a confirmatory bump.

Emit for **every donor record**:

| Field | Meaning |
|---|---|
| `donor_id` | Stable hash of normalized name + address |
| `score` | 0–1 affiliation score |
| `signals_fired` | Which of the four, explicitly |
| `basis` | Human-readable one-line justification |
| `manually_reviewed` | Boolean |
| `reviewer_note` | Free text where reviewed |

The `basis` field is what makes the project defensible. Anyone should be able to read one row and understand exactly why it was labelled.

---

## Manual adjudication

Automated classification is a first pass, not an answer.

- **Review the top 300 donors by dollar value.** This will cover most of the contributed mass with a bounded amount of work.
- **Review every record where signals disagree** — high address score but no name match, or vice versa.
- **Review a random sample of 100 low-score records** to estimate the false negative rate. Report that rate on the methodology page. Reporting your own error rate is the single most credibility-building thing in the project.

An LLM pass can do first-cut classification cheaply. It must produce the `basis` string for every call, and the basis must cite a specific signal — not a vibe. Any LLM-assigned label above a materiality threshold gets human review before publication. Log the model and prompt version in the decision log so the run is reproducible.

---

## Sensitivity analysis (do not skip)

The headline number will depend on where you set the thresholds. Show that dependence rather than hiding it.

Run the main specification at three settings — strict, base, permissive — and publish all three. If the direction of the finding flips between them, that *is* the finding, and it should be reported as "the data cannot distinguish these hypotheses" rather than picking the flattering one.

---

## Outputs

| File | Contents |
|---|---|
| `data/processed/donors.csv` | One row per donor with score, signals, basis |
| `data/processed/donor_clusters.csv` | Identified clusters with member donors and rationale |
| `data/processed/candidate_donor_mix.csv` | Per-candidate aggregate: total raised, development-linked $, share, CI |

All three are published as downloads on the site. Non-negotiable.

---

## What would make you abandon this module

If contribution records turn out to lack **addresses** or **dates**, Signals 1 and 2 both collapse and you're left with name matching alone — which is the highest-harm, lowest-confidence signal. Do not proceed on name matching alone. Pivot to one of the alternates in the strategy doc instead.
