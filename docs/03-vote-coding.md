# 03 — Vote Coding

Turning ~tens of thousands of vote rows into two variables: **is this a development matter?** and **which direction is pro-development?**

Both definitions must be written down and published *before* results are computed. See `docs/04`.

---

## Variable 1 — Is the item a development matter?

Three tiers of evidence, in descending order of preference.

**Tier 1 — Direct join.** If the development applications dataset carries an agenda item reference, use it. This is unambiguous and requires no judgment. Confirm during Phase 0 whether this link exists; it's the highest-value thing to look for.

**Tier 2 — Committee provenance.** Items routed through Planning and Housing Committee, Committee of Adjustment appeals, or Community Council planning items are development matters by construction. Committee origin is usually recoverable from the vote record's meeting metadata.

**Tier 3 — Text classification.** For remaining items, classify from motion and agenda item text. Includes: zoning by-law amendments, Official Plan amendments, site plan approvals, subdivision approvals, demolition permits, heritage designations *where they gate development*, Section 37/Community Benefits Charge agreements, LPAT/OLT appeal instructions, inclusionary zoning, and rental replacement.

Text classification produces a confidence score. Anything below threshold goes to manual review, and the reviewed set gets published.

**Explicitly excluded:** capital budget line items for infrastructure, transit planning, parkland acquisition unrelated to a development application. These are adjacent to development but aren't decisions on private applications, and including them would blur the variable.

---

## Variable 2 — Which direction is "pro-development"?

Harder, and the place where a critic will push. A `Yes` vote is not reliably pro-development — councillors routinely vote yes on motions that *restrict* an application.

**Code the motion, not the vote.** For each development item, first determine what the motion does:

- Approve application / adopt supportive planning report → yes = pro-development
- Refuse application / direct the City Solicitor to oppose at the OLT → yes = anti-development
- Amend to reduce height/density/units → yes = anti-development
- Defer → **ambiguous; exclude from the main specification**
- Procedural (receive for information, refer to staff) → exclude

Then `pro_dev_vote = (vote == "Yes") XOR (motion_direction == "restrictive")`.

Deferrals are genuinely ambiguous — deferral is used both as a delay tactic against applications and as a routine process step. Excluding them is cleaner than guessing. Report how many were excluded.

---

## Handling `Absent`

Per `docs/01`, `Absent` conflates genuine absence with declared conflicts of interest under the Municipal Conflict of Interest Act. The data cannot distinguish them.

- **Main specification:** treat `Absent` as missing. Denominator is votes actually cast.
- **Separate descriptive section:** absence rate on development items vs. all items, per member. If a member is systematically absent on development matters specifically, that's worth surfacing as a *question*, framed carefully — a declared conflict is the system working correctly, not evidence of anything untoward.

---

## The recorded-vote sampling problem

Only recorded votes are published. Items passing on consent or unanimous voice vote produce no rows at all. The dataset over-represents contested items.

This has a real analytical consequence: **uncontroversial approvals are invisible.** If development-linked money correlates with getting applications onto the consent agenda rather than with how contested votes go, this method cannot detect it.

State this limitation plainly on the methodology page. It's the most sophisticated objection available and pre-empting it is worth more than any additional chart.

---

## Outputs

| File | Contents |
|---|---|
| `data/processed/agenda_items.csv` | Item ID, meeting, committee, `is_development`, classification tier, confidence |
| `data/processed/motions.csv` | Motion text, `direction` (supportive/restrictive/ambiguous), basis |
| `data/processed/votes_coded.csv` | Member, item, raw vote, `pro_dev_vote`, included/excluded flag + reason |

Every exclusion carries a machine-readable reason. Someone will want to recompute with different exclusions; make that possible.
