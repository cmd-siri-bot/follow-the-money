# 05 — Pipeline

Batch analysis, static output. There is no reason to run a server: the data changes at most weekly and the analysis is deterministic.

---

## Repo layout

```
follow-the-ask/
├── STRATEGY.md
├── Makefile
├── docs/                    # this package
├── pipeline/
│   ├── config.py            # resource IDs, thresholds, constants
│   ├── extract/
│   │   ├── ckan.py          # generic CKAN client
│   │   ├── votes.py
│   │   ├── lobbying.py
│   │   ├── development.py
│   │   └── efd_scraper.py   # the hard one
│   ├── transform/
│   │   ├── normalize_names.py
│   │   ├── normalize_addresses.py
│   │   ├── classify_donors.py
│   │   └── code_votes.py
│   ├── analyze/
│   │   ├── specification.py
│   │   ├── sensitivity.py
│   │   └── diagnostics.py
│   └── publish/
│       └── build_artifacts.py   # → site/public/data/*.json
├── notebooks/               # exploration only; nothing published depends on these
├── data/
│   ├── raw/                 # gitignored, immutable, never edited
│   ├── interim/             # gitignored
│   └── processed/           # COMMITTED — these are the published artifacts
├── audit/
│   ├── donor_review.csv     # manual adjudication worksheet
│   └── error_rates.md
└── site/
```

**The one rule:** `data/raw/` is written once and never touched again. Every correction happens in `transform/` where it's version-controlled and visible. If you find yourself hand-editing a raw CSV, stop — that's how a project becomes unreproducible.

---

## Stages

```
extract → normalize → classify → code → analyze → publish
```

Each stage reads from the previous stage's output directory and writes to its own. No stage reaches backwards. This means any stage can be rerun in isolation, which matters a lot when the classifier changes for the fifth time.

### Stage contracts

**extract** → `data/raw/`
Raw responses, unparsed where possible. For EFD, archive the raw HTML alongside parsed output.

**normalize** → `data/interim/`
Canonical names and addresses. Names: strip titles, normalize case, handle "Last, First" vs "First Last", preserve the original in `name_raw`. Addresses: normalize street types, unit notation, postal code format; preserve `address_raw`. **Never discard the raw value** — you'll need it for manual review.

**classify** → `data/interim/`
Per `docs/02`. Emits scores with a `basis` string on every row.

**code** → `data/interim/`
Per `docs/03`. Emits `is_development`, `motion_direction`, `pro_dev_vote`, and exclusion reasons.

**analyze** → `data/processed/`
The pre-registered specification plus sensitivity and diagnostics. Writes result tables, not charts.

**publish** → `site/public/data/`
Small JSON for the frontend. Everything the site displays must exist here as a file — the frontend does no computation.

---

## Schemas

`donors.csv`
```
donor_id, name_raw, name_norm, address_raw, address_norm, postal_code,
amount, date, contribution_type, candidate_id, office_sought,
development_affiliation_score, signals_fired, basis,
manually_reviewed, reviewer_note
```

`votes_coded.csv`
```
vote_id, member_id, member_name, ward, agenda_item_id, meeting_date,
committee, motion_text, motion_direction, raw_vote, pro_dev_vote,
is_development, classification_tier, confidence, included, exclusion_reason
```

`candidate_donor_mix.csv`
```
candidate_id, name, ward, office_sought, total_raised, n_donors,
dev_linked_amount, dev_linked_share, dev_linked_share_ci_low,
dev_linked_share_ci_high, threshold_setting
```

One row per candidate **per threshold setting** — the sensitivity analysis needs all three side by side.

---

## Membership over time

Councillor↔ward is not static across 2022–2026. The term includes by-elections, at least one resignation (Ward 25), and a mayoral by-election in 2023 after John Tory's resignation.

Model this as `member_terms(member_id, ward, office, start_date, end_date)` and join votes to it by date. A flat lookup dict will silently misattribute votes and you may not notice.

---

## Refresh

GitHub Action, weekly:

1. Re-pull votes (contributions don't change — 2022 is closed)
2. Re-run coding and analysis
3. **Fail the build on schema drift.** Assert expected columns exist and value domains hold. A silent schema change that quietly corrupts the numbers is the worst realistic failure mode.
4. Open a PR rather than pushing to main, so numbers never change on the live site without a human seeing the diff

---

## Testing

Light but non-zero:

- Golden-file tests on normalization (a fixture of tricky names and addresses with expected outputs)
- Schema assertions on every extract
- One end-to-end run on a 100-row fixture in CI
- A regression test pinning the headline number, so you find out immediately if a refactor moves it

---

## Cost and runtime

Everything except the LLM classification pass is free and runs in minutes. The classification pass over a few tens of thousands of donor records is the only meaningful cost — batch it, cache by `donor_id`, and never re-classify an unchanged record.
