"""Import lobbying registrations/communications from Follow the Money's
already-ingested interim CSVs (data/interim/lobbyist_*.csv) into
TorontoSpends' relational schema.

Per docs/00-scope.md §3's reuse map: the lobbyist registry ZIP has no
CKAN datastore (docs/08-decision-log.md, 2026-08-02), so re-fetching and
re-parsing it from scratch would just redo work Follow the Money already
did. This adapter instead reads its already-cleaned interim output and
reshapes it into fact_lobbying_registration / fact_lobbying_communication
rows -- the relational join Follow the Money models as graph edges
instead. See docs/08-decision-log.md 2026-08-03 "Lobbyist/donor deep-dive
scoping" for where that source data came from.

Batched against remote Postgres (Supabase), not row-by-row: the first
version used Entity.objects.get_or_create() per row, which is one round
trip per unique entity (~13,800 of them) plus one per registration/
communication write. Fine against local sqlite, impractically slow over
a real network connection -- it never finished. This version resolves
every entity in a handful of bulk queries, then bulk_creates everything.
"""
import csv
import datetime
import sys
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

sys.path.insert(0, str(settings.BASE_DIR.parent))
from common.normalize_names import normalize_name, org_key  # noqa: E402,F401

from apps.entities.models import Entity
from apps.entities.resolution import chunks as _chunks
from apps.entities.resolution import resolve_entities
from apps.lobbying.models import FactLobbyingCommunication, FactLobbyingRegistration

DATASET_URL = "https://open.toronto.ca/dataset/lobbyist-registry/"
INTERIM_DIR = settings.BASE_DIR.parent / "data" / "interim"
RAW_ZIP = settings.BASE_DIR.parent / "data" / "raw" / "lobbyist_registry" / "lobbyactivity.zip"
WRITE_CHUNK = 200  # fact-table bulk_create -- FK + unique-index writes are heavier per row; 1000 hit Supabase's statement timeout


def _retrieved_at() -> datetime.datetime:
    """No stored fetch timestamp exists for this interim data (it predates
    TorontoSpends). Approximate with the raw ZIP's file mtime rather than
    inventing a date -- flagged as an approximation, not asserted as the
    real fetch time."""
    if RAW_ZIP.exists():
        return timezone.make_aware(datetime.datetime.fromtimestamp(RAW_ZIP.stat().st_mtime))
    return timezone.now()


def _read_csv(name: str) -> list[dict]:
    path = INTERIM_DIR / name
    if not path.exists():
        raise CommandError(f"Expected interim file not found: {path}")
    with path.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def _parse_date(value: str):
    if not value:
        return None
    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%m/%d/%Y"):
        try:
            return datetime.datetime.strptime(value.strip(), fmt).date()
        except ValueError:
            continue
    return None


class Command(BaseCommand):
    help = "Import lobbying registrations and communications from Follow the Money's interim CSVs."

    def handle(self, *args, **options):
        retrieved_at = _retrieved_at()

        subject_matters = _read_csv("lobbyist_subject_matters.csv")
        beneficiaries = {r["subject_matter_number"]: r for r in _read_csv("lobbyist_beneficiaries.csv")}
        firms = {r["subject_matter_number"]: r for r in _read_csv("lobbyist_firms.csv")}
        communications = _read_csv("lobbyist_communications.csv")
        self.stdout.write(
            f"Loaded {len(subject_matters)} subject matters, {len(beneficiaries)} beneficiaries, "
            f"{len(firms)} firms, {len(communications)} communications."
        )

        # --- Pass 1: figure out every entity we'll need, across both files, before touching the DB.
        needed: dict[tuple[str, str], str] = {}

        def note(entity_type, name):
            name = (name or "").strip()
            if not name:
                return None
            key = Entity.compute_match_key(entity_type, name)
            if not key:
                return None
            needed.setdefault((entity_type, key), name)
            return (entity_type, key)

        sm_entity_keys = {}  # sm_number -> (registrant_key, beneficiary_key, firm_key)
        for row in subject_matters:
            sm_number = row["SMNumber"]
            registrant_name = " ".join(
                p for p in (row.get("registrant_FirstName"), row.get("registrant_LastName")) if p
            ).strip()
            registrant_key = note(Entity.PERSON, registrant_name)
            beneficiary_row = beneficiaries.get(sm_number)
            beneficiary_key = note(Entity.ORG, beneficiary_row["Name"]) if beneficiary_row else None
            firm_row = firms.get(sm_number)
            firm_key = note(Entity.ORG, firm_row["Name"]) if firm_row else None
            sm_entity_keys[sm_number] = (registrant_key, beneficiary_key, firm_key)

        comm_entity_keys = []  # per communications row, in order: (poh_key, lobbyist_key)
        for row in communications:
            poh_key = note(Entity.PERSON, row.get("POH_Name", ""))
            lobbyist_name = " ".join(
                p for p in (row.get("LobbyistFirstName"), row.get("LobbyistLastName")) if p
            ).strip()
            lobbyist_key = note(Entity.PERSON, lobbyist_name)
            comm_entity_keys.append((poh_key, lobbyist_key))

        self.stdout.write(f"Resolving {len(needed)} distinct entities...")
        entities = resolve_entities(needed)
        self.stdout.write(self.style.SUCCESS(f"{len(entities)} entities resolved (fetched + created)."))

        # --- Pass 2: build registration rows, full refresh (delete + bulk_create, no per-row queries).
        registration_objs = []
        for row in subject_matters:
            sm_number = row["SMNumber"]
            registrant_key, beneficiary_key, firm_key = sm_entity_keys[sm_number]
            if registrant_key is None:
                continue  # no usable registrant name -- skip rather than create a blank entity
            registration_objs.append(FactLobbyingRegistration(
                source_url=DATASET_URL,
                retrieved_at=retrieved_at,
                subject_matter_number=sm_number,
                status=row.get("Status", ""),
                registrant_type=row.get("registrant_Type", ""),
                registrant=entities[registrant_key],
                registrant_position_title=row.get("registrant_PositionTitle", ""),
                beneficiary=entities[beneficiary_key] if beneficiary_key else None,
                firm=entities[firm_key] if firm_key else None,
                subject_matter=row.get("SubjectMatter", ""),
                particulars=row.get("Particulars", ""),
                initial_approval_date=_parse_date(row.get("InitialApprovalDate")),
                effective_date=_parse_date(row.get("EffectiveDate")),
                proposed_start_date=_parse_date(row.get("ProposedStartDate")),
                proposed_end_date=_parse_date(row.get("ProposedEndDate")),
            ))

        with transaction.atomic():
            FactLobbyingRegistration.objects.all().delete()
            for chunk in _chunks(registration_objs, WRITE_CHUNK):
                FactLobbyingRegistration.objects.bulk_create(chunk)

        self.stdout.write(self.style.SUCCESS(f"Registrations: {len(registration_objs)} loaded."))

        # --- Pass 3: communications, referencing the just-created registrations by subject_matter_number.
        registration_by_sm = {r.subject_matter_number: r for r in registration_objs}

        communication_objs = []
        comm_skipped_no_registration = 0
        for row, (poh_key, lobbyist_key) in zip(communications, comm_entity_keys):
            registration = registration_by_sm.get(row["subject_matter_number"])
            if registration is None:
                comm_skipped_no_registration += 1
                continue
            communication_objs.append(FactLobbyingCommunication(
                source_url=DATASET_URL,
                retrieved_at=retrieved_at,
                registration=registration,
                poh_office=row.get("POH_Office", ""),
                poh_type=row.get("POH_Type", ""),
                poh_position=row.get("POH_Position", ""),
                poh_name=row.get("POH_Name", ""),
                poh_entity=entities[poh_key] if poh_key else None,
                communication_method=row.get("CommunicationMethod", ""),
                communication_date=_parse_date(row.get("CommunicationDate")),
                lobbyist_entity=entities[lobbyist_key] if lobbyist_key else None,
            ))

        with transaction.atomic():
            FactLobbyingCommunication.objects.all().delete()
            for chunk in _chunks(communication_objs, WRITE_CHUNK):
                FactLobbyingCommunication.objects.bulk_create(chunk)

        self.stdout.write(self.style.SUCCESS(
            f"Communications: {len(communication_objs)} loaded, {comm_skipped_no_registration} skipped "
            f"(no matching registration)."
        ))
