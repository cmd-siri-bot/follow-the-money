# Handoff: Follow the Ask (Toronto development-donor/vote analysis)
Generated 2026-08-03 · Session 2

## Objective
Data journalism piece + interactive site answering: do Toronto councillors who receive money from people in the development industry vote differently on development matters? Methodology has to survive hostile scrutiny. Target publication: mid-to-late September 2026 (Toronto municipal election Oct 26, 2026). Owner: Siri. Repo: `https://github.com/cmd-siri-bot/follow-the-money`, working directory `C:\Users\iamsi\toronto-2026-election`.

**Constraints (unchanged from Session 1):** every external data claim verified live, not assumed. Never put a number on the site that isn't computed from data in the repo. Every classification carries a confidence score, not a binary label. A null/inconclusive result published honestly is a stronger outcome than a strained correlation. Only commit to git when explicitly asked (in this session the user gave that ask repeatedly at each checkpoint — pattern held throughout).

**End of Session 2, the objective forked into two candidate next directions the user wants to pursue, likely in separate new chats:**
1. Scrape motion text to grow the vote-level sample beyond its current 2.6% inclusion rate.
2. A new deep-dive into lobbyists, the companies/firms lobbying, and top donors' connections to power in Toronto — **not yet scoped**, see Open questions.

## Status

**Done — all of Phase 2 and the Phase 3 primary run:**
- Resolved Session 1's open question: `docs/01`–`docs/07` are authored documents (were on disk, untracked; confirmed byte-identical to what the user pasted, committed).
- Donor classification pipeline built end-to-end: `member_terms.csv` (live-verified roster), name/address normalization, a development-sector reference list from the lobbyist registry, `classify_donors.py` (Signals 1–3; Signal 4 dropped, no occupation field in the data), `donors.csv` + `donor_clusters.csv`.
- Vote coding pipeline built end-to-end: `code_votes.py` (Variable 1, is_development), `code_motion_direction.py` (Variable 2, motion direction / `pro_dev_vote`), `agenda_items.csv` + `motions.csv` + `votes_coded.csv`.
- Manual adjudication per docs/02: all 87 (later 83) low-confidence vote-item flags read individually; the full donor audit worksheet (top 300 by dollar, signals-disagree sets, random 100 zero-score) built and reviewed.
- Michael Thompson's (Ward 21) missing EFD data resolved via a user-supplied Form 4 PDF, checksummed against the form's own declared total (exact match), merged in.
- Phase 3 pre-registration filled in and committed (the commit *is* the pre-registration, per docs/04's own rule) — locked before any analysis code ran.
- Phase 3 primary specification, sensitivity analysis (strict/base/permissive), and leave-one-out diagnostics all run. **Result: the data cannot distinguish H1 from its alternatives** (see Verbatim for the numbers). Published to `data/processed/`.

**In progress:** nothing — this is a clean stopping point.

**Not started:**
- The motion-text scrape (see Objective, direction 1).
- The lobbyist/donor "connections to power" deep-dive (direction 2) — completely unscoped.
- Phase 4 (site build) — explicitly blocked per `docs/06` until Phase 3 has a settled number, and right now Phase 3's number is "inconclusive," which itself might be the number to build around, or might change if the scrape narrows the confidence interval. That's a real open call, not decided.
- `docs/07`'s pre-publication checklist (right of reply to councillors, third-party advertiser registration check with the City Clerk's office, etc.) — not started, doesn't block further analysis work.

## Decisions

| Decision | Why | Reopen if |
|---|---|---|
| `docs/01`–`08` confirmed authored/authoritative; the pasted `08-decision-log.md` was a stale template, kept the on-disk (actively-maintained) version | On-disk version was ahead, pasted version had a now-resolved "Open questions" section | Never |
| Signal 4 (occupation) dropped entirely | `contributions.csv` has no occupation field — confirmed, not assumed | If EFD ever adds the field |
| Signal 3 reference list built from lobbyist registry only, not dev applications | `development_applications.csv` has no applicant/developer name field, only a City staff contact — confirmed by inspecting all 23 columns | If the AIC per-application pages (`app.toronto.ca/AIC`) are ever scraped for applicant names |
| Signal 3 restricted to `registrant_Type == "In-house"` lobbyists on dev-related subject matters (1,364 people) | Precision over recall per docs/02 — a Consultant-type lobbyist isn't an officer of their client | — |
| Signal 1 (postal-code clustering) gated on `near_limit_share ≥ 0.3` and scaled continuously by it, not just donor-count/aggregate-amount | Un-gated version flagged a 10-donor, $192-avg cluster identically to an 8-donor, $1,200-avg (maxed) cluster — near-limit-share distribution was strongly bimodal, confirming two different populations were being conflated | — |
| Signal 2 (temporal clustering) alone scores ~0; only fires meaningfully combined with Signal 1 (`coordinated_firm_bonus`) | Un-gated version fired on 78% of all contributions — any healthy campaign has 3+ donors in *some* 7-day window from ordinary fundraiser timing; docs/02 itself calls this the benign "fundraiser-event pattern," distinct from the "coordinated-firm pattern" (shared address + shared window) | — |
| `contributor_type` in `{"Candidate", "Candidate Spouse"}` excluded from the donor population | Self/spousal funding runs under a separate, much higher limit than third-party giving and isn't "development industry money" by definition; was dominating the top of the dollar-value rankings (5.2% of total dollars) | — |
| `amount_net = amount − amount_returned` used for all scoring/clustering, not gross `amount` | Found a $10,000 contribution to a mayoral candidate that was returned in full (over the legal limit) — 64 rows, $80,936 total returned, were being credited at face value | — |
| Vote coding Tier 1 (direct join votes↔dev-applications) confirmed **not available** | No shared ID format between `agenda_item_number` (`2023.FM1.8`) and dev-applications' `application_number`/`reference_file_number` | — |
| Tier 2 uses the body-abbreviation code embedded in `agenda_item_number`, not votes.csv's `committee` column | `committee` shows where a vote was *cast* — 93.8% show `"City Council"` regardless of true origin, since most items get their final vote at Council | — |
| Only `PH` and `PB` codes get a blanket Tier 2 development flag; `NY/TE/SC/EY` (community councils) still go through Tier 3 text filtering | docs/03's own phrasing is "Community Council *planning* items," not all community council business | — |
| "Release Section 37/42 Funds" items excluded even when the section_37_cbc keyword matches | These are spending decisions on money already collected from a past approval, not a decision on a development application — 5 items miscaught before this fix | — |
| Variable 2 direction classified from `agenda_item_title` only; `vote_description` isn't useful (too terse) | Confirmed by sampling — `vote_description` is almost always just a procedural label like "Majority required - EX27.2 - Saxe - motion 2" | If full motion text is scraped (direction 1 above) |
| "Amend Item" motions always excluded (direction unknowable from title alone) | docs/03's own worked example ("reduce height/density → restrictive") assumes access to amendment text this pipeline doesn't have | Same as above |
| Only title-explicit approve/refuse/oppose language counted for direction — 36.2% of Adopt-type motions, the rest excluded rather than guessed | Guessing on the single most scrutinized variable is worse than an honestly small sample | Same as above |
| Kandavel's losing 2022 Ward 20 campaign excluded from his `dev_affiliation_share`; only his winning 2023 by-election donors count | "Donor base = the campaign that won the seat they currently hold" | If reanalyzing "does losing-campaign money predict anything" as a side question |
| Phase 3 population = 26 currently-sitting members only, NOT merged with the 4 departed predecessors | Faithful reading of the *already-locked* pre-registration text ("n ≈ 26, plus mid-term membership changes") — reinterpreting this after seeing results would defeat the point of pre-registering | If a supplementary within-ward before/after analysis is added later (predecessors' data already exists in `member_terms.csv` for this) |
| Phase 3 locked choices (user-approved 2026-08-03): base threshold 0.5, primary test = vote-level logistic regression with member-clustered SEs, member-level Spearman as secondary, ward development intensity as the required control | User's explicit decision at the pre-registration checkpoint | — |
| Phase 3 verdict is **"cannot distinguish,"** not "refuted," despite a consistently negative point estimate | The locked decision rule's own override: base-threshold 95% CI spans both an economically meaningful negative *and* positive effect | If the scrape narrows the CI enough to resolve this |

## Dead ends — don't retry

| Tried | What happened | Why it failed |
|---|---|---|
| `WebFetch` against `secure.toronto.ca/council/agenda-item.do?...` | HTTP 403 | Same Akamai WAF as the EFD site (Session 1 finding) — this host blocks non-browser traffic generally, not just EFD. **The `mcp__Claude_Browser__*` tools work fine against it** — used successfully ~10 times this session for committee-code verification. |
| Early `classify_donors.py`: Signal 2 (temporal) weighted equally to Signal 1 | 96.4% of all contributions scored above zero | Any campaign with a healthy donor base has 3+ people giving within *some* 7-day window from ordinary fundraiser timing — not a signal on its own per docs/02's own framing. |
| Early `classify_donors.py`: Signal 1 gated only on donor-count/aggregate-amount, no near-limit check | Flagged a 10-donor cluster averaging $192 (16% of the limit) identically to an 8-donor cluster averaging $1,200 (the limit) | docs/02's actual signature requires donations *at or near the limit* — donor count/amount alone doesn't capture that. |
| Using `development_applications.csv`'s `contact_name` as an applicant/developer field | It's a City of Toronto planner's name (`@toronto.ca` email), not the developer | Field doesn't exist in the bulk CSV export; would need to scrape each application's detail page at `app.toronto.ca/AIC/...` (not attempted). |
| Using votes.csv's `committee` field for Tier 2 classification | 93.8% of all votes show `committee="City Council"` | Shows where the vote was *cast*, not where the item originated — the agenda-item-number's embedded code is the right field. |

## Corrections & preferences
Carried forward from Session 1 (still applicable, no contradicting signal this session):
- User is not deeply technical with devtools — give explicit step-by-step walkthroughs, not just "check devtools."
- Always sanity-check file content against filename claims.
- Only commit when explicitly asked.

New this session:
- User answers "Recommended" options quickly in `AskUserQuestion` prompts — seems to trust default judgment calls once the tradeoff is stated clearly; doesn't need extensive hand-holding on methodology choices once framed.
- User will proactively supply primary-source documents (mid-message, without being asked) when told about a data gap — happened with the Thompson Form 4 PDF. Worth taking at face value and integrating carefully (with a checksum/validation step) rather than treating as a distraction from the current task.
- User is comfortable with long, thorough sessions covering multiple phases in one sitting — this session ran Phase 2 (both halves) through Phase 3 primary analysis without a natural break point being requested until context-budget became the concern.

## Work products

| Item | What it is | Where it is | State |
|---|---|---|---|
| `docs/08-decision-log.md` | Full narrative log — **read this first**, it has complete reasoning for every decision above | committed | Extensively updated this session, current through the Phase 3 result |
| `docs/04-methodology.md` | Locked pre-registration | committed at `febdaba` | Complete, do not edit without treating it as reopening the pre-registration |
| `pipeline/transform/*.py` | `normalize_names.py`, `normalize_addresses.py`, `build_member_terms.py`, `build_dev_reference.py`, `classify_donors.py`, `thompson_form4_transcription.py`, `merge_thompson_form4.py`, `code_votes.py`, `code_motion_direction.py`, `build_donor_audit.py` | committed | All working, re-runnable in this order |
| `pipeline/analyze/*.py` | `specification.py`, `sensitivity.py`, `diagnostics.py` | committed | Working; rerun as-is if `votes_coded.csv` changes (e.g. after the scrape) |
| `data/interim/*` | `contributions.csv` (24,125 rows, incl. Thompson's), `votes.csv`, `member_terms.csv`, `dev_sector_reference.csv`, `donors.csv`, `donor_clusters.csv`, `agenda_items.csv`, `motions.csv`, `votes_coded.csv`, `thompson_form4_contributions.csv` | **local only, gitignored** at `C:\Users\iamsi\toronto-2026-election\data\interim\` | Present locally, fully regenerable by rerunning the pipeline scripts in order, *except* the 5 EFD `.xls` files (manual export, per Session 1) |
| `data/raw/efd_contributions/2022_thompson_ward21_form4.pdf` | Archived source PDF | **local only, gitignored** | Present locally |
| `data/processed/candidate_donor_mix.csv`, `candidate_donor_mix_all_thresholds.csv`, `leave_one_out.csv` | Published Phase 3 outputs | committed | Complete |
| `audit/donor_review.csv` | Manual adjudication worksheet, `reviewer_verdict`/`reviewer_note` columns still blank | committed | Ready for the user's own read before any donor name goes public — this session's review was a first pass, not the required human sign-off |
| `phase3-specification-result.md`, `phase3-sensitivity-result.md`, `phase3-leave-one-out-result.md` | Full Phase 3 result writeups | repo root, committed | Complete |
| `handoff-follow-the-ask-2026-08-02.md` | Session 1 handoff | repo root, committed | Superseded by this document — this one absorbs everything still-live from it |

**Important:** if a new chat runs against the same working directory (`C:\Users\iamsi\toronto-2026-election`), everything above — including the gitignored `data/interim/` and `data/raw/` files — will still be there. Nothing needs to be re-attached. If a new chat runs somewhere else, only the committed files travel (via git); `data/interim/` and `data/raw/` would need the pipeline scripts rerun (all reproducible except the manual EFD exports and the Thompson PDF).

## Verbatim
- Repo: `https://github.com/cmd-siri-bot/follow-the-money`, working dir `C:\Users\iamsi\toronto-2026-election`
- Pre-registration commit: `febdaba`
- **Phase 3 primary result** (base threshold 0.5): `dev_affiliation_share` coefficient = **−2.3310** (p=0.2832), 95% CI **[−6.5881, 1.9262]**, n=1,154 included votes, 26 members, clustered SE by member
- **Sensitivity** (strict 0.75 / base 0.5 / permissive 0.35): coef −2.1582 (p=0.317) / −2.3310 (p=0.283) / −1.4788 (p=0.518) — negative at all three, no direction flip
- **Leave-one-out** (26 reruns, base threshold): logistic coef range [−4.6969, −1.6848], 0/26 flip positive; Spearman rho range [−0.3776, −0.2055], 0/26 flip positive
- **Vote-level inclusion rate: 2.6%** (1,176 of 45,665 total recorded votes) — the number to try to grow via the scrape
- Development items: 246 → **241** after the Section 37 fund-release fix; manual-review flags 87 → **83**
- Development-item Adopt-type motions with resolvable title direction: **85 of 235 (36.2%)**
- `classify_donors.py` key constants: `WEIGHTS = {"address_cluster": 0.35, "coordinated_firm_bonus": 0.40, "name_match_corroborated": 0.35, "name_match_uncorroborated": 0.15}`; `ADDRESS_NEAR_LIMIT_MIN_SHARE = 0.3`; `NEAR_LIMIT_FRACTION = 0.9`; `TEMPORAL_WINDOW_DAYS = 3`; `EXCLUDED_CONTRIBUTOR_TYPES = {"Candidate", "Candidate Spouse"}`
- Dev-sector reference list: **1,364 distinct people** from the lobbyist registry (In-house registrants, dev-related subject matters only)
- `candidate_donor_mix.csv` range at base threshold: 15 of 26 members at exactly 0.00 `dev_affiliation_share`; highest is Anthony Perruzza at 0.324, lowest non-zero is Michael Thompson at 0.037
- Illustrative structural-cluster finding (no corroborating name match, correctly scored via clustering alone): six donors surnamed "Ajmera," each $7,500 total, each to the same three 2023 mayoral candidates (Bailão, Saunders, Tory) — a strong candidate for the site's hero sequence per `docs/06`
- Honest false-negative illustration (deliberately *not* acted on): a donor named "Losani, Fred" — a recognizable GTA homebuilder surname by reputation, but no corroborating record in the lobbyist-registry-only reference list, so left unscored rather than patched from general knowledge
- Committee-abbreviation-code table (full version, ~33 codes verified/inferred) lives in `docs/08-decision-log.md`'s 2026-08-02 entry "docs/03's Tier 1 vote↔development-application join does not exist"

## Open questions

**For the motion-text scrape (direction 1):**
- Scope: 404 distinct motions across 241 development items, pages at `secure.toronto.ca/council/agenda-item.do?item=<agenda_item_id>` (same pattern already used successfully via the browser tool this session — see the FM1.8/DM5.2/MPB4.1/PB1.4/CA2.2/RM5.7/IA3.1/BL3.1 fetches).
- Not yet designed: how to parse per-motion text out of a page that can show multiple motions (each item page lists all its motions in order, with mover name and "motion N" labels matching `vote_description`'s existing mover/number data — should be joinable). Needs a new script, tentatively `pipeline/transform/scrape_motion_text.py`, feeding an updated `code_motion_direction.py` that uses real motion text instead of title-only keyword heuristics.
- Whether to re-run Phase 3 automatically after, or treat it as a distinct "enriched" rerun reported alongside the original (docs/04's pre-registration note already anticipates this: "both versions will be reported side by side, not just the later one").

**For the lobbyist/donor deep-dive (direction 2) — entirely unscoped, start here:**
- What's the actual deliverable? A site section, a standalone side investigation, or an enrichment to Signal 3's reference list (currently limited to Toronto's own lobbyist registry — Ontario Business Registry directorships were never pulled, flagged as a gap multiple times this session)?
- What does "connections to power" mean concretely — donor-to-donor networks (shared surnames/addresses, like the Ajmera cluster found by accident this session), lobbyist-to-donor overlap (does anyone in `dev_sector_reference.csv` also appear as a donor?), or firm-to-firm relationships via `lobbyist_beneficiaries.csv`'s parent-company/subsidiary/controlling-interest fields (barely touched this session)?
- Privacy/harm framing needs revisiting before building anything here — `docs/07`'s explicit caution ("Don't build a reverse lookup by donor name. That's a surveillance tool, not an analysis") is directly relevant to a "map the network" style deep-dive and should shape scope from the start, not be retrofitted after.

## Next action
Two independent threads, likely two separate new chats. For the **scrape**: attach this handoff, say "continuing the motion-text scrape," and start by reading `docs/08-decision-log.md`'s Variable 2 entries plus `data/interim/motions.csv` to confirm the exact 404-motion population before writing the scraper. For the **deep-dive**: attach this handoff and have a scoping conversation first — deliverable, definition of "connections to power," and privacy framing — before touching any data.
