# 07 — Editorial and Legal

This project names real people — sitting councillors and private individual donors — in connection with a politically charged question, during an election campaign. That combination carries real obligations. Read this before publishing anything.

**Not legal advice.** If the analysis produces something pointed about a named individual, talk to a lawyer with Ontario defamation experience before it goes live. That's a few hundred dollars against a real downside.

---

## The core editorial principle

**Everything in this dataset is legal.** Individual contributions within the statutory limits, publicly disclosed as the law requires. Lobbying is registered and lawful. Councillors voting on development matters in their wards is their job.

The project describes a **statistical pattern**. It does not allege wrongdoing, and no piece of copy anywhere on the site should imply that it does. This isn't defensive hedging — it's the accurate description of what the analysis can support, and holding it consistently is what makes the piece credible rather than partisan.

If the framing starts to feel like an exposé, the framing has drifted. Pull it back.

---

## Named private individuals

Councillors are public figures and fair subjects of scrutiny about their public roles. **Donors are private citizens.** The bar for naming them is much higher.

Rules:

1. **Never assert employment or affiliation as fact** unless it's from a public record you can cite — a lobbyist registry filing, a corporate registry directorship, a development application. Inference from a shared address is a *pattern*, not a fact about a person.
2. **Prefer cluster-level to individual-level presentation.** "Four donors at 123 Example St, all at the limit, within six days" carries the analytical content without foregrounding names. The names are in the downloadable data — which is already public record — but the site's narrative shouldn't lead with them.
3. **Never impute motive.** You can say money arrived in a pattern. You cannot say why, and you don't know why.
4. **Precision over recall in classification** (per `docs/02`). A false positive here is a harm to a real person. Accept a weaker finding over a wrong label.
5. **Correction policy on the site**, with a working contact address, and act on corrections within 48 hours.

---

## Election timing

The election is October 26, 2026. Publishing analysis about sitting councillors, some of whom are candidates, during a campaign raises the stakes.

- **Publish by mid-to-late September** or wait until after the election. Dropping this in the final two weeks looks like an intervention rather than an analysis, regardless of intent.
- **Cover every councillor**, not a subset. If scope reduces per `docs/00`, the selection rule must be mechanical (e.g. development application volume) and stated publicly. Any selection that could be read as targeting is fatal to the piece.
- **Give right of reply.** Email every named councillor before publication with their figures and a reasonable window. Publish responses verbatim alongside their card. This is standard practice, it's cheap, and it converts the piece from something done *to* them into something done properly.
- **Check third-party advertiser registration rules.** Ontario municipal election law regulates third-party advertising — content that promotes or opposes a candidate may trigger registration requirements. A neutral analytical piece shouldn't qualify, but the line is worth confirming with the City Clerk's office rather than assuming. You've looked at Toronto's third-party advertising by-laws before; this is the same regime.

---

## Licensing and attribution

- City of Toronto data: **Open Government Licence – Toronto**. Commercial use and derivative products permitted; **attribution required**. Include the exact required attribution string in the footer and in every downloadable file's header.
- EFD contribution data is public record but confirm any terms of use on the EFD system itself before republishing in bulk.
- Your derived datasets: license them openly (CC BY 4.0 or ODbL). Publishing under an open licence is consistent with the project's premise and makes it more useful to others.
- Represent API data, if used: check Open North's terms.

---

## Privacy

Contribution records are public by law — the disclosure regime exists precisely so this information is available. But *republishing at scale* is different from a per-candidate lookup, and it deserves thought.

- Publish addresses at the **postal code or normalized-cluster level**, not full street addresses, in anything the site displays. Full addresses stay in the pipeline for clustering; they don't need to be on a public page.
- Don't build a reverse lookup by donor name. That's a surveillance tool, not an analysis.
- Consider omitting donors below a materiality threshold from displayed detail entirely. A $50 donor doesn't affect the finding and doesn't need to be surfaced.

---

## Pre-publication checklist

- [ ] Every number on the site traces to a committed script
- [ ] Methodology page complete, including all limitations from `docs/04` §7
- [ ] Measured error rate from the audit sample published
- [ ] Sensitivity analysis (all three thresholds) published
- [ ] Leave-one-out diagnostics published
- [ ] No causal verbs anywhere — search the copy for "buys", "influences", "leads to", "results in"
- [ ] Statement that contributions are legal, disclosed, and capped, above the fold
- [ ] Right of reply offered to every named councillor; responses included
- [ ] Correction policy and working contact address live
- [ ] OGL-Toronto attribution in footer and in file headers
- [ ] Addresses reduced to postal code / cluster level in displayed data
- [ ] Repo public, `make all` reproduces every artifact
- [ ] Third-party advertiser registration question resolved with the Clerk's office
- [ ] Read the whole site once imagining you're a councillor's chief of staff looking for a reason to discredit it

---

## If you get it wrong

Correct visibly and fast. A dated correction note at the top of the affected page, the change logged in the decision log, and the artifact regenerated. Quietly editing a number is the one unrecoverable mistake — it destroys the reproducibility claim that the entire project rests on.
