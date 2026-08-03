"""
Knowledge graph of money/power/influence connections around Toronto city
government: lobbyist registrants, the firms/clients they represent, the
specific public-office-holder contacts they lobbied, campaign donors, and
sitting members of Council.

Standalone side investigation ("lobbyist/donor deep-dive", scoped 2026-08-03)
-- distinct from and not feeding back into donors.csv or the Phase 3
donor-classification/vote pipeline. Two files that pipeline never used are
the core new material here: lobbyist_beneficiaries.csv (corporate structure
-- client/parent/subsidiary/controlling-interest) and
lobbyist_communications.csv (140,921 individual lobbying-contact records,
89,443 with a named public-office-holder contact).

Scope deliberately widened vs. Signal 3 (classify_donors.py): this graph
includes Consultant-type registrants, not just In-house, and applies no
development-sector subject-matter filter. Signal 3's restriction was about
precision for a public per-donor classification ("a false positive here is
a harm to a real person," docs/02); this graph is backend analytical
infrastructure, not a publication -- see docs/08-decision-log.md,
2026-08-03 "Lobbyist/donor deep-dive scoping" for the publication-layer
question this deliberately defers.

Cross-role identity links (does this lobbyist also appear as a donor?) are
still confidence-scored, never asserted as fact from a name match alone --
same reasoning as Signal 3: a shared name is not proof of a shared person.

**Ward-numbering trap, verified live before writing this join (not
assumed):** POH_Office in lobbyist_communications.csv spans dates from
2000-2026 and pre-2018-reform rows use Toronto's old 44/47-ward numbering
(e.g. "Ward 34 Don Valley East" for what is Ward 16 today; "Ward 37
Scarborough Centre" for today's Ward 21). Checked post-2022-11-15 rows
specifically: their embedded ward numbers DO match member_terms.csv's
current numbering (e.g. "Ward 11 University-Rosedale", "Ward 16 Don Valley
East" both correct). Resolution requires BOTH the ward number AND the ward
name text to match a member whose term covers the communication's date --
number-only matching would have silently mis-attributed pre-reform-era
contacts to whichever current councillor happens to hold that number today.

2026-08-03 addition: the 81 development-application items with an
extracted Applicant/Agent/Architect/Owner (data/processed/
development_applicants.csv, see docs/08's "Staff-report PDF route"
entry) are fed in as a `devapp:` project entity per item plus a role
entity per name. Organization-shaped names (architecture/planning firms,
numbered companies) reuse the same org_key() merge every other org
entity uses -- if a name here is already an org: entity from the
lobbyist firm/beneficiary tables, it's automatically the same node, no
extra linking code needed (this is how the Samuel Sarick Limited /
Graduate Holdings Limited cross-validation surfaced in the prior
session's manual read). Person-shaped names (mostly individual Owners)
get the same confidence-scored possible_same_person treatment as
registrant<->donor linking below -- matched against the graph's full
donor and lobbyist_registrant populations (a superset of donors.csv and
dev_sector_reference.csv), never asserted as identity from name alone.

Outputs:
  data/interim/kg_entities.csv -- entity_id, entity_type (person/org),
    subtype, display_name, match_key, postal_code, notes
  data/interim/kg_edges.csv -- edge_id, source_id, target_id, edge_type,
    date, amount, confidence, basis, source_table
"""
import csv
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from normalize_names import normalize_name, normalize_whitespace, normalize_postal, strip_accents_for_matching  # noqa: E402
from extract_role_name import extract_name_and_postal, classify_role_name, person_match_key  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
INTERIM = ROOT / "data" / "interim"
PROCESSED = ROOT / "data" / "processed"

SUBJ_PATH = INTERIM / "lobbyist_subject_matters.csv"
FIRMS_PATH = INTERIM / "lobbyist_firms.csv"
BENE_PATH = INTERIM / "lobbyist_beneficiaries.csv"
COMMS_PATH = INTERIM / "lobbyist_communications.csv"
DONORS_PATH = INTERIM / "donors.csv"
MEMBERS_PATH = INTERIM / "member_terms.csv"
DEV_APPLICANTS_PATH = PROCESSED / "development_applicants.csv"

ROLE_COLUMNS = ["applicant", "agent", "architect", "owner"]

ENTITIES_OUT = INTERIM / "kg_entities.csv"
EDGES_OUT = INTERIM / "kg_edges.csv"

ENTITY_FIELDS = ["entity_id", "entity_type", "subtype", "display_name", "match_key", "postal_code", "notes"]
EDGE_FIELDS = ["edge_id", "source_id", "target_id", "edge_type", "date", "amount", "confidence", "basis", "source_table"]

MAYOR_OFFICE_ALIASES = {"mayor", "mayors office", "office of the mayor"}
NO_TERM_END = "9999-12-31"


def org_key(name: str) -> str:
    name = strip_accents_for_matching(normalize_whitespace(name or "")).lower()
    name = re.sub(r"[^a-z0-9 ]", " ", name)
    name = re.sub(r"\b(inc|incorporated|ltd|limited|corp|corporation|llp|lp|the|co)\b", " ", name)
    return normalize_whitespace(name)


def load_csv(path: Path):
    with path.open("r", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


class Registry:
    def __init__(self):
        self.entities = {}
        self.edges = []
        self._n = 0

    def add_entity(self, entity_id, entity_type, subtype, display_name, match_key="", postal_code="", notes=""):
        if entity_id not in self.entities:
            self.entities[entity_id] = {
                "entity_id": entity_id, "entity_type": entity_type, "subtype": subtype,
                "display_name": display_name, "match_key": match_key,
                "postal_code": postal_code, "notes": notes,
            }
        return entity_id

    def add_edge(self, source_id, target_id, edge_type, date="", amount="", confidence="", basis="", source_table=""):
        self._n += 1
        self.edges.append({
            "edge_id": f"e{self._n}", "source_id": source_id, "target_id": target_id,
            "edge_type": edge_type, "date": date, "amount": amount,
            "confidence": confidence, "basis": basis, "source_table": source_table,
        })

    def org(self, name: str, source_table: str):
        if not name or not name.strip():
            return None
        key = org_key(name)
        if not key:
            return None
        entity_id = f"org:{key}"
        self.add_entity(entity_id, "org", "organization", normalize_whitespace(name),
                         match_key=key, notes=f"first seen in {source_table}")
        return entity_id


def build_registrants(reg: Registry, subj_rows, firms_rows, bene_rows):
    """One subj_row == one (subject_matter, registrant) filing; verified
    1:1 SMNumber->registrant (0 of 14,504 subject matters have >1
    registrant), so no fan-out ambiguity here."""
    firm_by_sm, bene_by_sm = {}, {}
    for r in firms_rows:
        firm_by_sm.setdefault(r["subject_matter_number"], []).append(r)
    for r in bene_rows:
        bene_by_sm.setdefault(r["subject_matter_number"], []).append(r)

    sm_to_registrant = {}
    for r in subj_rows:
        sm = r["SMNumber"]
        last, first = (r.get("registrant_LastName") or "").strip(), (r.get("registrant_FirstName") or "").strip()
        regnum = (r.get("registrant_RegistrationNUmber") or "").strip()
        if not last or not first or not regnum:
            continue
        norm = normalize_name(f"{last}, {first}")
        registrant_id = f"reg:{regnum}"
        sm_to_registrant[sm] = registrant_id
        reg.add_entity(registrant_id, "person", "lobbyist_registrant",
                        f"{first} {last}", match_key=norm["match_key"],
                        postal_code=normalize_postal(r.get("registrant_PostalCode") or ""),
                        notes=f"{r.get('registrant_Type','')}; {r.get('registrant_PositionTitle','')}".strip("; "))

        subject_text = r.get("SubjectMatter", "")
        for fr in firm_by_sm.get(sm, []):
            firm_id = reg.org(fr.get("Name", ""), "lobbyist_firms.csv")
            if firm_id:
                reg.add_edge(registrant_id, firm_id, "represents",
                             date=fr.get("FiscalStart", ""),
                             basis=f"{sm}: {subject_text}", source_table="lobbyist_firms.csv")
        for br in bene_by_sm.get(sm, []):
            org_id = reg.org(br.get("Name", ""), "lobbyist_beneficiaries.csv")
            if org_id:
                btype = re.sub(r"\s+", "_", (br.get("Type") or "unspecified").strip().lower())
                reg.add_edge(registrant_id, org_id, f"lobbies_for__{btype}",
                             basis=f"{sm}: {subject_text}", source_table="lobbyist_beneficiaries.csv")
    return sm_to_registrant


def build_members(reg: Registry, member_rows):
    for m in member_rows:
        member_id = f"member:{m['member_id']}"
        subtype = "mayor" if m["office"] == "Mayor" else "councillor"
        reg.add_entity(member_id, "person", subtype, m["member_name"],
                        match_key=normalize_name(f"{m['member_name']}")["match_key"],
                        notes=f"Ward {m['ward_number']} {m['ward_name']}; {m['start_date']}-{m['end_date'] or 'present'}")


def _ward_num_match(text: str):
    m = re.match(r"^Ward\s+(\d+)\b", text)
    return m.group(1) if m else None


def _term_active(member_row: dict, date: str) -> bool:
    end = member_row["end_date"] or NO_TERM_END
    return member_row["start_date"] <= date <= end


def resolve_poh_office(poh_office_text: str, comm_date: str, member_rows):
    """Returns (member_row_or_None, match_basis_string)."""
    text = normalize_whitespace(poh_office_text)
    if not text or not comm_date:
        return None, "missing_office_or_date"

    active = [m for m in member_rows if _term_active(m, comm_date)]
    if not active:
        return None, "no_member_in_office_on_date"

    wardnum = _ward_num_match(text)
    if wardnum:
        norm_text = strip_accents_for_matching(text).lower()
        candidates = [
            m for m in active
            if m["ward_number"] == wardnum
            and strip_accents_for_matching(m["ward_name"]).lower() in norm_text
        ]
        if len(candidates) == 1:
            return candidates[0], "ward_number_and_name_match"
        if len(candidates) > 1:
            return None, "ambiguous_ward_match"

    norm_text = strip_accents_for_matching(text).lower()
    name_candidates = []
    for m in active:
        aliases = {strip_accents_for_matching(m["member_name"]).lower()}
        if m["office"] == "Mayor":
            aliases |= MAYOR_OFFICE_ALIASES
            aliases.add(f"mayor {strip_accents_for_matching(m['member_name']).lower()}")
        if norm_text in aliases:
            name_candidates.append(m)
    if len(name_candidates) == 1:
        return name_candidates[0], "member_name_match"
    if len(name_candidates) > 1:
        return None, "ambiguous_name_match"

    return None, "no_match"


def build_communications(reg: Registry, comms_rows, sm_to_registrant, member_rows):
    stats = {"total_with_poh_name": 0, "resolved_to_member": 0}
    for r in comms_rows:
        poh_name = (r.get("POH_Name") or "").strip()
        if not poh_name:
            continue
        stats["total_with_poh_name"] += 1
        sm = r["subject_matter_number"]
        registrant_id = sm_to_registrant.get(sm)
        if not registrant_id:
            continue

        date = (r.get("CommunicationDate") or "").strip()
        method = (r.get("CommunicationMethod") or "").strip()

        poh_norm = normalize_name(poh_name)
        poh_id = f"poh:{poh_norm['match_key']}"
        reg.add_entity(poh_id, "person", "poh_contact", poh_name, match_key=poh_norm["match_key"],
                        notes=(r.get("POH_Type") or ""))
        reg.add_edge(registrant_id, poh_id, "lobbied_contact", date=date,
                     basis=f"{sm}, method={method}, office={r.get('POH_Office','')}",
                     source_table="lobbyist_communications.csv")

        member_row, basis = resolve_poh_office(r.get("POH_Office", ""), date, member_rows)
        if member_row:
            stats["resolved_to_member"] += 1
            reg.add_edge(registrant_id, f"member:{member_row['member_id']}", "lobbied_office",
                         date=date, confidence=basis,
                         basis=f"{sm}, contact={poh_name} ({r.get('POH_Type','')}), method={method}",
                         source_table="lobbyist_communications.csv")
    return stats


def build_donors(reg: Registry, donor_rows, member_rows):
    efd_to_member = {m["efd_candidate_name"]: m for m in member_rows if m["efd_candidate_name"]}
    seen_donor_people = {}
    for r in donor_rows:
        name_norm = r["name_norm"]
        postal = r["postal_code"]
        person_key = (name_norm, postal)
        if person_key not in seen_donor_people:
            match_key = strip_accents_for_matching(name_norm)
            match_key = re.sub(r"[^a-z0-9, ]", "", match_key)
            donor_id = f"donor:{match_key}|{postal}"
            reg.add_entity(donor_id, "person", "donor", r["name_raw"], match_key=match_key, postal_code=postal)
            seen_donor_people[person_key] = donor_id
        donor_id = seen_donor_people[person_key]

        member_row = efd_to_member.get(r["candidate"])
        if member_row:
            amount_net = r.get("amount_net", "")
            reg.add_edge(donor_id, f"member:{member_row['member_id']}", "donated",
                         date=r.get("date_received", ""), amount=amount_net,
                         basis=f"{r.get('election','')}, {r.get('contribution_type','')}",
                         source_table="donors.csv")
    return seen_donor_people


def link_registrants_to_donors(reg: Registry):
    """Name-match only, confidence-scored -- never asserted as identity.
    Corroborated = shared postal code between the lobbyist registry's
    registrant_PostalCode and the donor's EFD postal_code; same
    corroboration logic Signal 1 uses for address clustering."""
    registrants = [e for e in reg.entities.values() if e["subtype"] == "lobbyist_registrant"]
    donors = [e for e in reg.entities.values() if e["subtype"] == "donor"]
    donors_by_key = {}
    for d in donors:
        donors_by_key.setdefault(d["match_key"], []).append(d)

    n_matched = 0
    for reg_person in registrants:
        for donor_person in donors_by_key.get(reg_person["match_key"], []):
            corroborated = bool(reg_person["postal_code"]) and reg_person["postal_code"] == donor_person["postal_code"]
            confidence = "name_and_postal_corroborated" if corroborated else "name_only_uncorroborated"
            reg.add_edge(reg_person["entity_id"], donor_person["entity_id"], "possible_same_person",
                         confidence=confidence,
                         basis=f"match_key='{reg_person['match_key']}'",
                         source_table="build_knowledge_graph.py")
            n_matched += 1
    return n_matched


def build_dev_applicants(reg: Registry, dev_app_rows):
    """One devapp: entity per item with a found Data Sheet, plus a
    role edge to the (org- or person-classified) name in each of the
    four role columns. Returns stats for reporting."""
    stats = {"items": 0, "role_values_seen": 0, "org_roles": 0, "person_roles": 0, "skipped": 0}
    person_role_entity_ids = []

    for r in dev_app_rows:
        if r.get("found_data_sheet") != "True":
            continue
        item_id = r["item_id"]
        devapp_id = f"devapp:{item_id}"
        reg.add_entity(
            devapp_id, "project", "development_application", r.get("agenda_item_title", item_id),
            notes=(f"application_number={r.get('application_number','')}; "
                    f"street={r.get('dev_app_street','')}").strip("; "),
        )
        stats["items"] += 1

        for role in ROLE_COLUMNS:
            raw = r.get(role, "")
            if not raw:
                continue
            stats["role_values_seen"] += 1
            name, postal = extract_name_and_postal(raw)
            kind = classify_role_name(name)
            if kind is None:
                stats["skipped"] += 1
                continue

            if kind == "org":
                org_id = reg.org(name, "development_applicants.csv")
                if org_id is None:
                    stats["skipped"] += 1
                    continue
                stats["org_roles"] += 1
                reg.add_edge(org_id, devapp_id, f"role__{role}",
                             basis=f"{item_id}: {r.get('agenda_item_title','')}",
                             source_table="development_applicants.csv")
            else:
                norm = person_match_key(name)
                match_key = norm["match_key"]
                if not match_key:
                    stats["skipped"] += 1
                    continue
                stats["person_roles"] += 1
                person_id = f"devrole:{match_key}|{postal}"
                reg.add_entity(person_id, "person", "dev_role_person", name,
                                match_key=match_key, postal_code=postal,
                                notes=f"role={role}; first seen on {item_id}")
                reg.add_edge(person_id, devapp_id, f"role__{role}",
                             basis=f"{item_id}: {r.get('agenda_item_title','')}",
                             source_table="development_applicants.csv")
                person_role_entity_ids.append(person_id)
    return stats, person_role_entity_ids


def link_dev_role_persons(reg: Registry, person_role_entity_ids):
    """Same confidence-scored, name-match-only approach as
    link_registrants_to_donors: person-shaped applicant/agent/architect/
    owner names checked against the graph's full donor and
    lobbyist_registrant populations (a superset of donors.csv and
    dev_sector_reference.csv). A shared name is never asserted as a
    shared identity -- only postal-corroborated matches should be
    treated as real leads, per docs/02's identity-match standard."""
    donors = [e for e in reg.entities.values() if e["subtype"] == "donor"]
    registrants = [e for e in reg.entities.values() if e["subtype"] == "lobbyist_registrant"]
    donors_by_key, registrants_by_key = {}, {}
    for d in donors:
        donors_by_key.setdefault(d["match_key"], []).append(d)
    for r in registrants:
        registrants_by_key.setdefault(r["match_key"], []).append(r)

    n_matched = 0
    for person_id in set(person_role_entity_ids):
        person = reg.entities[person_id]
        for target_list, target_label in ((donors_by_key, "donor"), (registrants_by_key, "lobbyist_registrant")):
            for target in target_list.get(person["match_key"], []):
                corroborated = bool(person["postal_code"]) and person["postal_code"] == target["postal_code"]
                confidence = "name_and_postal_corroborated" if corroborated else "name_only_uncorroborated"
                reg.add_edge(person_id, target["entity_id"], "possible_same_person",
                             confidence=confidence,
                             basis=f"match_key='{person['match_key']}', target_subtype={target_label}",
                             source_table="build_knowledge_graph.py")
                n_matched += 1
    return n_matched


def write_outputs(reg: Registry):
    ENTITIES_OUT.parent.mkdir(parents=True, exist_ok=True)
    with ENTITIES_OUT.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=ENTITY_FIELDS)
        w.writeheader()
        w.writerows(reg.entities.values())
    with EDGES_OUT.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=EDGE_FIELDS)
        w.writeheader()
        w.writerows(reg.edges)


def main():
    subj_rows = load_csv(SUBJ_PATH)
    firms_rows = load_csv(FIRMS_PATH)
    bene_rows = load_csv(BENE_PATH)
    comms_rows = load_csv(COMMS_PATH)
    donor_rows = load_csv(DONORS_PATH)
    member_rows = load_csv(MEMBERS_PATH)
    dev_app_rows = load_csv(DEV_APPLICANTS_PATH)

    reg = Registry()
    build_members(reg, member_rows)
    sm_to_registrant = build_registrants(reg, subj_rows, firms_rows, bene_rows)
    comm_stats = build_communications(reg, comms_rows, sm_to_registrant, member_rows)
    build_donors(reg, donor_rows, member_rows)
    n_identity_links = link_registrants_to_donors(reg)

    # Snapshot which org: entities already existed from the lobbyist
    # tables before dev-applicant orgs get merged in, so the cross-
    # validation count below reflects genuine independent overlap.
    org_keys_before = {e["match_key"] for e in reg.entities.values() if e["entity_type"] == "org"}
    dev_app_stats, person_role_entity_ids = build_dev_applicants(reg, dev_app_rows)
    n_applicant_identity_links = link_dev_role_persons(reg, person_role_entity_ids)
    devapp_org_ids = {e["source_id"] for e in reg.edges if e["source_table"] == "development_applicants.csv"}
    org_keys_from_devapps = {
        reg.entities[eid]["match_key"] for eid in devapp_org_ids
        if eid in reg.entities and reg.entities[eid]["entity_type"] == "org"
    }
    n_org_cross_validation = len(org_keys_from_devapps & org_keys_before)

    write_outputs(reg)

    by_subtype = {}
    for e in reg.entities.values():
        by_subtype[e["subtype"]] = by_subtype.get(e["subtype"], 0) + 1
    by_edge_type = {}
    for e in reg.edges:
        by_edge_type[e["edge_type"]] = by_edge_type.get(e["edge_type"], 0) + 1

    print(f"Entities: {len(reg.entities)}")
    for k, v in sorted(by_subtype.items(), key=lambda kv: -kv[1]):
        print(f"  {k}: {v}")
    print(f"Edges: {len(reg.edges)}")
    for k, v in sorted(by_edge_type.items(), key=lambda kv: -kv[1]):
        print(f"  {k}: {v}")
    print(f"Communications with a named POH contact: {comm_stats['total_with_poh_name']}")
    print(f"  resolved to a specific current member's office (date+ward matched): {comm_stats['resolved_to_member']}")
    print(f"Registrant<->donor possible-same-person links: {n_identity_links}")
    print()
    print(f"Development-application items with a found Data Sheet fed in: {dev_app_stats['items']}")
    print(f"  role values seen: {dev_app_stats['role_values_seen']} "
          f"(org-classified: {dev_app_stats['org_roles']}, person-classified: {dev_app_stats['person_roles']}, "
          f"skipped/placeholder: {dev_app_stats['skipped']})")
    print(f"  org-level cross-validation (same org already existed as a lobbyist firm/beneficiary): {n_org_cross_validation}")
    print(f"  dev-role-person<->donor/registrant possible-same-person links: {n_applicant_identity_links}")
    print(f"-> {ENTITIES_OUT}")
    print(f"-> {EDGES_OUT}")


if __name__ == "__main__":
    main()
