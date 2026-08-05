"""Import City community grant allocations into FactGrant.

Source confirmed live 2026-08-05 during the Oct-20 grant-program-cut
decision (docs/08-decision-log.md, "Grant program cut for Oct 20
confirmed"): a single CKAN dataset (`community-grants-allocations`)
covers every City grant program -- 105 distinct funding-program codes as
of that check -- through two datastore-active resources:

- "Community Grants Allocations since 2022" (per-organization rows)
- "Community Grants Programs since 2022" (code -> full program name)

Unlike the operating budget (one XLSX file per year, no live API) or the
lobbyist registry (a ZIP with no datastore), this one is a normal
paginated CKAN datastore_search table, so common/ckan_client.py's
existing fetch_resource() works directly -- no new fetch code needed.
"""
import sys

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

sys.path.insert(0, str(settings.BASE_DIR.parent))
from common.ckan_client import fetch_and_save  # noqa: E402

from apps.entities.models import Entity
from apps.entities.resolution import chunks, resolve_entities
from apps.grants.models import FactGrant

DATASET_URL = "https://open.toronto.ca/dataset/community-grants-allocations/"
ALLOCATIONS_RESOURCE_ID = "866f95c3-49ac-496e-91ee-1cbffd662cdb"
PROGRAMS_RESOURCE_ID = "e8ae0064-43f8-4cb4-988f-41336f2f3c06"
RAW_DIR = settings.BASE_DIR.parent / "data" / "raw" / "grants"
WRITE_CHUNK = 200  # see apps/entities/resolution.py's docstring for why this isn't 1000


def _to_cents(value) -> int:
    try:
        return round(float(str(value).replace(",", "").strip() or 0) * 100)
    except (ValueError, TypeError):
        return 0


def _to_int(value, default=0) -> int:
    try:
        return int(float(value))
    except (ValueError, TypeError):
        return default


class Command(BaseCommand):
    help = "Import community grant allocations from the City's open data CKAN datastore."

    def handle(self, *args, **options):
        retrieved_at = timezone.now()

        programs = fetch_and_save(PROGRAMS_RESOURCE_ID, RAW_DIR / "programs.json")
        program_names = {
            r["Field Name / Item / Column name"]: r["Description / Definition"] for r in programs
        }
        self.stdout.write(f"Loaded {len(programs)} program codes.")

        allocations = fetch_and_save(ALLOCATIONS_RESOURCE_ID, RAW_DIR / "allocations.json")
        self.stdout.write(f"Loaded {len(allocations)} grant allocation rows.")

        needed: dict[tuple[str, str], str] = {}
        for row in allocations:
            name = (row.get("Organization") or "").strip()
            if not name:
                continue
            key = Entity.compute_match_key(Entity.ORG, name)
            if key:
                needed.setdefault((Entity.ORG, key), name)

        self.stdout.write(f"Resolving {len(needed)} distinct recipient organizations...")
        entities = resolve_entities(needed)
        self.stdout.write(self.style.SUCCESS(f"{len(entities)} entities resolved (fetched + created)."))

        grant_objs = []
        skipped_no_year = 0
        for row in allocations:
            org_name = (row.get("Organization") or "").strip()
            recipient = None
            if org_name:
                key = Entity.compute_match_key(Entity.ORG, org_name)
                recipient = entities.get((Entity.ORG, key)) if key else None

            code = (row.get("Funding Program") or "").strip()
            amount_cents = _to_cents(row.get("Total Funding Amount"))
            fiscal_year = _to_int(row.get("date_from_filename"), default=0)
            if not fiscal_year:
                skipped_no_year += 1
                continue

            grant_objs.append(FactGrant(
                source_url=DATASET_URL,
                retrieved_at=retrieved_at,
                fiscal_year=fiscal_year,
                funding_program_code=code,
                funding_program_name=program_names.get(code, ""),
                division=(row.get("Division") or "").strip(),
                recipient=recipient,
                recipient_name_raw=org_name,
                ward=(row.get("Ward") or "").strip(),
                service_area=(row.get("Service Area") or "").strip(),
                total_number_of_grants=_to_int(row.get("Total Number of Grants"), default=1),
                amount_cents=amount_cents,
            ))

        with transaction.atomic():
            FactGrant.objects.all().delete()
            for chunk in chunks(grant_objs, WRITE_CHUNK):
                FactGrant.objects.bulk_create(chunk)

        self.stdout.write(self.style.SUCCESS(
            f"Grants: {len(grant_objs)} loaded, {skipped_no_year} skipped (no parseable fiscal year)."
        ))
