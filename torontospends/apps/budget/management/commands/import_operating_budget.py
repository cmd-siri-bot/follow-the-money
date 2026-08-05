"""Import the City's approved operating budget (program summary by
expenditure category) into FactBudgetLine.

Source confirmed live 2026-08-05 against
https://open.toronto.ca/dataset/budget-operating-budget-program-summary-by-expenditure-category/ :
one XLSX per fiscal year, sheet "Open Data", columns Program / Service /
Activity / Expense-Revenue / Category Name / Sub-Category Name /
Commitment item / <year> (the amount column is literally named after the
fiscal year, so it's read positionally as "whatever the last column is",
not by a fixed name). Schema checked stable across FY2022-2025 before
this was written -- not guessed. As of this writing the dataset's own
last refresh was 2026-02-25, so no FY2026 resource exists yet; add its
resource id to RESOURCES below once the City publishes it.
"""
import datetime
import sys
from pathlib import Path

import pandas as pd
from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

sys.path.insert(0, str(settings.BASE_DIR.parent))
from common.ckan_client import fetch_file  # noqa: E402

from apps.budget.models import FactBudgetLine

DATASET_URL = (
    "https://open.toronto.ca/dataset/"
    "budget-operating-budget-program-summary-by-expenditure-category/"
)
RAW_DIR = settings.BASE_DIR.parent / "data" / "raw" / "operating_budget"

# fiscal_year -> CKAN resource id, confirmed live 2026-08-05
RESOURCES = {
    2025: "f9def3c1-a97f-4d31-bc58-c0494d750b80",
    2024: "ee996e45-c0a4-4b52-9d5d-a408b3f9cbfa",
    2023: "a6f7a8e8-e497-4f77-9881-daba429ea981",
    2022: "9e5f9a63-fdeb-46e4-9f5f-8143038de56d",
}


class Command(BaseCommand):
    help = "Import the City's approved operating budget summary, one fiscal year at a time."

    def add_arguments(self, parser):
        parser.add_argument(
            "--years", nargs="*", type=int, default=None,
            help="Subset of fiscal years to (re)import, e.g. --years 2024 2025. Default: all.",
        )
        parser.add_argument("--force-download", action="store_true", help="Re-download even if cached.")

    def handle(self, *args, **options):
        years = options["years"] or sorted(RESOURCES.keys())
        retrieved_at = timezone.now()

        for year in years:
            if year not in RESOURCES:
                self.stderr.write(self.style.WARNING(f"No known resource id for {year}, skipping."))
                continue
            self.import_year(year, RESOURCES[year], retrieved_at, options["force_download"])

    def import_year(self, year: int, resource_id: str, retrieved_at: datetime.datetime, force: bool):
        out_path = RAW_DIR / f"approved-operating-budget-summary-{year}.xlsx"
        fetch_file(resource_id, out_path, force=force)
        self.stdout.write(f"[{year}] using {out_path}")

        df = pd.read_excel(out_path, sheet_name="Open Data")
        # Amount column is named after the fiscal year (int or str depending
        # on the file) -- always the last real data column, not a fixed name.
        amount_col = df.columns[7]

        rows = []
        skipped_blank = 0
        for _, r in df.iterrows():
            program = str(r.get("Program", "")).strip()
            if not program or program.lower() == "nan":
                skipped_blank += 1
                continue
            amount = r.get(amount_col)
            amount_cents = 0 if pd.isna(amount) else round(float(amount) * 100)
            rows.append(FactBudgetLine(
                source_url=DATASET_URL,
                retrieved_at=retrieved_at,
                budget_type="operating",
                fiscal_year=year,
                program=program,
                service=str(r.get("Service", "")).strip(),
                activity=str(r.get("Activity", "")).strip(),
                expense_or_revenue=str(r.get("Expense/Revenue", "")).strip(),
                category_name=str(r.get("Category Name", "")).strip(),
                sub_category_name=str(r.get("Sub-Category Name", "")).strip(),
                commitment_item=str(r.get("Commitment item", "")).strip(),
                amount_cents=amount_cents,
            ))

        with transaction.atomic():
            deleted, _ = FactBudgetLine.objects.filter(fiscal_year=year, budget_type="operating").delete()
            FactBudgetLine.objects.bulk_create(rows, batch_size=2000)

        self.stdout.write(self.style.SUCCESS(
            f"[{year}] {len(rows)} lines loaded ({deleted} prior rows replaced, "
            f"{skipped_blank} blank rows skipped)."
        ))
