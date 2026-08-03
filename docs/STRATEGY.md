# Follow the Ask — Strategy

**Status:** Pre-build. Data dependencies verified 2026-08-02.
**Target publication:** Mid-to-late September 2026 (Toronto municipal election is October 26, 2026).
**Owner:** Siri
**Repo:** `follow-the-ask` (not yet created)

---

## 1. What this is, in one paragraph

A single-question data journalism piece with an interactive explorer attached. The question: **do Toronto councillors who receive money from people in the development industry vote differently on development matters?** The output is a static site that leads with a quantified answer, backs it with a reproducible pipeline, and publishes every derived dataset for download. It is not a civic data browser — three of those already exist for Toronto. It is an analysis with a finding.

## 2. Why this and not something else

Three sites already browse Toronto council votes: VoteToronto, councillors.torontoinsights.com, and SolveTO. They are all competent data browsers built by civic technologists. None of them runs an analysis.

The differentiator is not engineering. It's method: defining a question, building a classification layer under uncertainty, controlling for a confounder, and shipping a number you can defend under hostile questioning. That is the same skill as the PQL scoring work, and it reads to a hiring manager as analyst judgment rather than API plumbing.

**The portfolio framing:** this piece should demonstrate that you can be trusted with an ambiguous question and messy inputs. The methodology page matters more than the map.

## 3. Two findings from verification that reshape the build

These were discovered before writing a line of code and they change the design substantially. Read them before anything else.

### 3.1 Corporate donations are illegal. Every donor is a person.

Toronto banned corporate and union donations in 2009; Ontario followed province-wide in 2017 via the Modernizing Ontario's Municipal Legislation Act, explicitly to reduce development industry influence. Only individuals normally resident in Ontario, plus the candidate and spouse, may contribute.

This means there is no `donor_type = corporation` column to filter on. Every single contribution in the 2022 file is from a named human being. **Industry attribution is therefore the entire analytical problem, not a preprocessing step.** The method has to infer industry affiliation from clustering — shared addresses, shared surnames, donation bursts within days of each other, all at or near the contribution limit.

There is precedent that this pattern is real and detectable: reporting on the Ontario Liberal leadership race identified $33,500 arriving from ten individuals whose names matched executives at a single Vaughan-based developer, nine of them within a three-day window, each at the maximum. That is the signature to look for.

**Consequence for scope:** the classification module (`docs/02`) is now the critical path, not the frontend. Budget accordingly.

### 3.2 Contribution data is not on the open data portal.

It lives in the Elections Financial Disclosure system at `app.toronto.ca/EFD`, a JSF web application with per-candidate search. There is no bulk CSV and no API. This is a scraping job with session handling, and it is the single largest unknown in the estimate.

**Consequence for scope:** Phase 0 is a scraping spike. If the EFD scrape proves harder than two days of work, the fallback is a reduced scope covering mayor plus ten downtown/high-growth wards rather than all 26 seats.

## 4. What is verified vs. assumed

| Dependency | Status | Note |
|---|---|---|
| Council voting record, 2022–2026 | **Verified live** | `Is Retired?: False`, last refreshed 2026-06-18. The "Retired" badge on open.toronto.ca is a stale page render — the underlying CKAN package is active. |
| Lobbyist Registry | Assumed available | On open data portal; confirm resource IDs in Phase 0 |
| Development Applications | Assumed available | Confirm coverage window matches 2022–2026 term |
| Ward boundaries GeoJSON | Assumed available | Low risk |
| Campaign contributions | **Verified as scrape-only** | No API. See 3.2. |

## 5. Phases

**Phase 0 — Feasibility (target: one sitting, ~3 hours).**
Confirm every resource ID resolves, pull 100 rows from each, and spike the EFD scraper against a single candidate. Ends with a go/no-go and a scope decision (full council vs. reduced).

**Phase 1 — Extraction.**
Scrape all 2022 contributions. Pull the full 2022–2026 vote record. Pull lobbying and development applications. Everything lands as raw, untouched files under `data/raw/` and is never edited in place.

**Phase 2 — Classification.** *(critical path)*
Build the donor industry classifier. Build the development-item vote coder. Both produce a labelled table with a confidence score per row and both get manually audited on a sample.

**Phase 3 — Analysis.**
Pre-register the specification in writing before running it. Then run it. Report the result including the null case.

**Phase 4 — Build and publish.**
Static site, methodology page, downloads, repo link.

**Do not start Phase 4 before Phase 3 produces a number.** The design should be built around the actual finding, not a placeholder. If the correlation turns out to be near zero, the hero copy and probably the whole visual direction change.

## 6. Working agreement with Claude

When picking this up in a new session, read `STRATEGY.md` first, then the doc for the current phase. Rules for the collaboration:

- **Verify before building.** Every external data assumption gets a live check, not a plausible-looking guess. The two findings in section 3 were both surprises; assume there are more.
- **Never invent a number.** If a figure isn't computed from data in the repo, it doesn't go on the site.
- **Log decisions.** Anything that changes scope, method, or a definition goes in `docs/08-decision-log.md` with a date and a reason. This doc is what makes the methodology page writable later.
- **Confidence scores, not binary labels.** Every classification carries a score. The site exposes them.
- **Push back on the thesis.** If the data doesn't support the framing, say so early. A null result published honestly is a stronger portfolio piece than a strained correlation.

## 7. Document index

| File | Purpose | Read when |
|---|---|---|
| `docs/00-getting-started.md` | The Phase 0 checklist, step by step | Now |
| `docs/01-data-sources.md` | Every source, verified IDs, endpoints, known quirks | Phase 0–1 |
| `docs/02-donor-classification.md` | The clustering method for inferring industry | Phase 2 |
| `docs/03-vote-coding.md` | Defining "development-related agenda item" | Phase 2 |
| `docs/04-methodology.md` | Pre-registration, confounders, what we will and won't claim | Before Phase 3 |
| `docs/05-pipeline.md` | Repo layout, stage contracts, data schemas | Phase 1 |
| `docs/06-frontend.md` | Design direction, IA, component spec | Phase 4 |
| `docs/07-editorial-legal.md` | Defamation care, licensing, publication checklist | Before publishing |
| `docs/08-decision-log.md` | Running record of every decision and why | Continuously |

## 8. The one-line success test

If a Toronto Star reporter or a councillor's staffer reads the methodology page and cannot find a hole in it, the project succeeded — regardless of what the number turned out to be.
