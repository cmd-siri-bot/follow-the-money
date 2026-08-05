from collections import defaultdict

from django.db.models import Count
from django.shortcuts import render

from apps.budget.views import EARLIEST_YEAR, LATEST_YEAR, policy_area_changes

from .models import FactLobbyingRegistration
from .taxonomy import LOBBYING_ISSUE_TO_POLICY_AREA, explode_subject_matter

TOP_N = 15


def _issue_stats():
    """Explode subject_matter into individual tags and count, per tag: how
    many registrations mention it, and how many distinct organizations
    are involved (beneficiary if set, otherwise the in-house registrant's
    own employer -- stored in the firm field for In-house rows, see
    apps/lobbying/taxonomy.py)."""
    reg_ids_by_tag = defaultdict(set)
    orgs_by_tag = defaultdict(set)
    rows = FactLobbyingRegistration.objects.exclude(subject_matter="").values_list(
        "id", "subject_matter", "beneficiary_id", "firm_id"
    )
    for reg_id, subject_matter, beneficiary_id, firm_id in rows:
        org_id = beneficiary_id or firm_id
        for tag in explode_subject_matter(subject_matter):
            reg_ids_by_tag[tag].add(reg_id)
            if org_id:
                orgs_by_tag[tag].add(org_id)

    rows_out = [
        {"tag": tag, "registration_count": len(ids), "org_count": len(orgs_by_tag[tag])}
        for tag, ids in reg_ids_by_tag.items()
    ]
    rows_out.sort(key=lambda r: r["registration_count"], reverse=True)
    return rows_out[:TOP_N]


def _top_firms(limit=TOP_N):
    """Professional lobbying firms only -- Consultant-type registrations,
    where `firm` holds the firm the registrant works for. In-house
    registrations also populate `firm` (with the registrant's own
    employer), which would misleadingly inflate this list if included."""
    return list(
        FactLobbyingRegistration.objects.filter(registrant_type="Consultant")
        .exclude(firm__isnull=True)
        .values("firm__id", "firm__display_name")
        .annotate(n=Count("id"))
        .order_by("-n")[:limit]
    )


def _top_consultants(limit=TOP_N):
    return list(
        FactLobbyingRegistration.objects.filter(registrant_type="Consultant")
        .values("registrant__id", "registrant__display_name")
        .annotate(n=Count("id"))
        .order_by("-n")[:limit]
    )


def _top_represented_orgs(limit=TOP_N):
    """Organizations lobbying happened on behalf of -- beneficiary for
    Consultant-type registrations (the client), or the registrant's own
    employer for In-house (stored in `firm`, since beneficiary is null
    for those). This is the fuller version of the homepage's "most
    lobbied-for organizations" teaser."""
    beneficiary_counts = (
        FactLobbyingRegistration.objects.exclude(beneficiary__isnull=True)
        .values("beneficiary__id", "beneficiary__display_name")
        .annotate(n=Count("id"))
    )
    inhouse_counts = (
        FactLobbyingRegistration.objects.filter(registrant_type="In-house")
        .exclude(firm__isnull=True)
        .values("firm__id", "firm__display_name")
        .annotate(n=Count("id"))
    )
    combined = defaultdict(int)
    names = {}
    for row in beneficiary_counts:
        combined[row["beneficiary__id"]] += row["n"]
        names[row["beneficiary__id"]] = row["beneficiary__display_name"]
    for row in inhouse_counts:
        combined[row["firm__id"]] += row["n"]
        names[row["firm__id"]] = row["firm__display_name"]
    ranked = sorted(combined.items(), key=lambda kv: -kv[1])[:limit]
    return [{"entity_id": eid, "display_name": names[eid], "n": n} for eid, n in ranked]


def _funding_cross_reference():
    """Lobbying volume per policy area (only the tags with a clean mapping,
    see taxonomy.py) next to that area's real spending change over the
    full term. Two parallel facts, not a claim that one caused the other
    -- lobbying volume reflects what's filed as legally required
    disclosure, not lobbying effectiveness or influence."""
    reg_ids_by_area = defaultdict(set)
    rows = FactLobbyingRegistration.objects.exclude(subject_matter="").values_list("id", "subject_matter")
    for reg_id, subject_matter in rows:
        tags = set(explode_subject_matter(subject_matter))
        areas = {LOBBYING_ISSUE_TO_POLICY_AREA[t] for t in tags if t in LOBBYING_ISSUE_TO_POLICY_AREA}
        for area in areas:
            reg_ids_by_area[area].add(reg_id)

    spending_by_area = {c["name"]: c for c in policy_area_changes(EARLIEST_YEAR, LATEST_YEAR)}

    out = []
    for area, ids in reg_ids_by_area.items():
        spend = spending_by_area.get(area)
        if not spend:
            continue
        out.append({
            "policy_area": area,
            "lobbying_registration_count": len(ids),
            "spending_before": spend["before_dollars"],
            "spending_after": spend["after_dollars"],
            "spending_pct_change": spend["pct_change"],
        })
    out.sort(key=lambda r: r["lobbying_registration_count"], reverse=True)
    return out


def overview(request):
    context = {
        "issues": _issue_stats(),
        "firms": _top_firms(),
        "consultants": _top_consultants(),
        "represented_orgs": _top_represented_orgs(),
        "cross_reference": _funding_cross_reference(),
        "earliest_year": EARLIEST_YEAR,
        "latest_year": LATEST_YEAR,
        "total_registrations": FactLobbyingRegistration.objects.count(),
    }
    return render(request, "lobbying/overview.html", context)
