# 01 — Data Sources

Every external dependency, its access method, verification status, and known quirks.
**Verification date: 2026-08-02.** Re-verify anything marked *assumed* during Phase 0.

---

## Source A — Council Voting Record ✅ VERIFIED LIVE

**Portal:** City of Toronto Open Data (CKAN)
**Package slug:** `members-of-toronto-city-council-voting-record`
**Package ID:** `7f5232d6-0d2a-4f95-864a-417cbf341cc4`
**Owner:** City Clerk's Office (`clerk@toronto.ca`)
**Refresh:** "As available" — tied to publication of meeting minutes
**Last refreshed at verification:** 2026-06-18
**Retirement flag:** `Is Retired?: False`

> **Note on the "Retired" badge.** The public page at `open.toronto.ca/dataset/members-of-toronto-city-council-voting-record/` renders a Retired label. The underlying CKAN record says otherwise and is actively refreshing. Trust the API, not the portal chrome. If someone challenges the data's currency, this distinction is worth being able to explain.

### Resource IDs

| Term | Resource ID | Format | Datastore |
|---|---|---|---|
| **2022–2026** *(primary)* | `55ead013-2331-4686-9895-9e8145b94189` | CSV | Yes — queryable |
| 2018–2022 | `84ce76c3-94ed-486c-818b-596fd78d1fea` | CSV | Yes — queryable |
| 2014–2018 | `4e7ac62c-c607-4184-9531-315d9d389798` | CSV | Yes |
| 2010–2014 | `59f37a01-77fd-48db-a997-3cb94802642c` | CSV | Yes |
| Field readme | `6f7d8bb7-6ae4-4a15-8b01-b95a81c35dfe` | TXT | — |

There are also non-datastore CSV/JSON/XML mirrors per term (e.g. `c4feb78c-c867-42a9-b803-7c6d859df969` for 2022–2026 CSV). Prefer the datastore-active resources — they support pagination and filtering.

**Bulk dump:** `https://ckan0.cf.opendata.inter.prod-toronto.ca/datastore/dump/{resource_id}`

### Semantics that affect the analysis

Three things from the City Clerk's documentation that you must encode correctly:

1. **Only recorded votes appear.** Under Article 12 of the Council Procedures by-law, votes are recorded on request. Items passing on consent or by unanimous voice vote generate no rows. **The dataset is therefore a non-random sample of council decisions — it over-represents contested items.** Say this on the methodology page; someone will raise it.
2. **"Absent" is overloaded.** It covers genuine absence *and* a member declining to participate because they declared a conflict of interest under the Municipal Conflict of Interest Act. These are analytically opposite — a declared conflict on a development item is arguably the most interesting signal in the dataset, and it's indistinguishable from a dentist appointment. Treat `Absent` as missing data in the main specification, and consider a separate descriptive section on absence rates.
3. Vote values are `Yes` / `No` / `Absent`. Validate this on load rather than assuming.

**Licence:** the raw CKAN record shows "License not specified"; the public portal applies Open Government Licence – Toronto. Attribute under OGL-Toronto and confirm the exact string during Phase 0.

---

## Source B — Campaign Contributions ⚠️ SCRAPE ONLY

**System:** Elections Financial Disclosure (EFD), `app.toronto.ca/EFD`
**Access:** JSF web application, per-candidate search. No API. No bulk export. Not on the open data portal.
**Cycle needed:** 2022 (filed early 2023)

### The regulatory context that defines the data

- **Corporate and union contributions are prohibited.** Toronto banned them in 2009; Ontario followed province-wide in 2017 under the Modernizing Ontario's Municipal Legislation Act, with the stated aim of reducing development industry influence in municipal politics. Only individuals normally resident in Ontario, plus the candidate and their spouse, may contribute.
- **Limits (2022 cycle):** $1,200 per individual to a council candidate; $2,500 to a Toronto mayoral candidate; $5,000 aggregate from one contributor across candidates in the same jurisdiction.
- **In-kind counts** — donated goods and services and fundraiser ticket purchases are contributions and are valued at market rate.

**Every donor is a natural person.** There is no corporate flag to filter on. This is the finding that makes `docs/02` the centre of the project rather than a preprocessing step.

### The known leakage channel

Corporations and unions can't donate to candidates, but they *can* register as third-party advertisers and contribute to registered third-party advertisers. Toronto maintains a third-party advertiser registry. This is out of scope for v1 but is the obvious v2 module — and it's the first thing a knowledgeable critic will ask about, so acknowledge it on the methodology page.

### Fields to confirm in the Phase 0 spike

Contributor name, contributor address, amount, **date**, contribution type (monetary/in-kind), recipient candidate, office sought. Date and address are load-bearing — see `docs/02`.

---

## Source C — Lobbyist Registry *(assumed)*

On the open data portal. Provides registered lobbyists, their clients, subject matter, and communications with public office holders.

**Role in v1:** secondary corroboration only. If a donor cluster maps to a firm that also lobbied on the same agenda items, that's a much stronger story than either signal alone. Do not make it a primary variable — lobbying is legal, disclosed, and routine, and treating it as inherently suspect is exactly the analytical sloppiness this project is meant to avoid.

Confirm during Phase 0: resource IDs, coverage window, whether subject matter is coded or free text.

---

## Source D — Development Applications *(assumed)*

On the open data portal. Application-level records with location, type, and status. Committee of Adjustment records may be a separate dataset.

**Role:** identifies which agenda items are development matters, and provides ward-level development intensity for the confounder control in `docs/04`.

Confirm during Phase 0: coverage includes 2022–2026, ward field present, and whether there's any identifier that links an application to the council agenda item that decided it. That link, if it exists, is the highest-value join in the project.

---

## Source E — Ward Boundaries *(assumed, low risk)*

GeoJSON on the open data portal, 25-ward model in effect since 2018. Used for the map layer only.

Cross-check councillor↔ward assignment against the Represent API (`https://represent.opennorth.ca/boundaries/toronto-wards/`) — useful for catching mid-term changes.

**Mid-term membership changes to handle:** the 2022–2026 term includes by-elections and at least one resignation (Ward 25 Scarborough—Rouge Park), plus the 2023 mayoral by-election following John Tory's resignation, which brought Olivia Chow in mid-term. Councillor↔ward is not a static mapping over the term. Model it with effective date ranges, not a lookup dict.

---

## Access pattern (all CKAN sources)

```python
BASE = "https://ckan0.cf.opendata.inter.prod-toronto.ca/api/3/action"

# find it
requests.get(f"{BASE}/package_search", params={"q": "development applications"})

# inspect it
requests.get(f"{BASE}/package_show", params={"id": "<slug>"})

# read it — paginate with offset, datastore_search caps per request
requests.get(f"{BASE}/datastore_search",
             params={"resource_id": "<rid>", "limit": 1000, "offset": 0})
```

Always check `datastore_active` on a resource before assuming you can query it. Plenty of Toronto resources are parked files with no datastore behind them.

## Standing risks

- **Schema drift.** Column names change between refreshes without versioning. Validate on ingest and fail loudly.
- **EFD availability.** A city IT change could break the scraper at any point. Once scraped, archive the raw HTML alongside the parsed data so the extract is reproducible even if the source moves.
- **Rate limits are unpublished.** Cache everything; back off on 503.
