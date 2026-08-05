from django.db import models

from apps.entities.models import SourcedFact


class FactBudgetLine(SourcedFact):
    """One line item from a City operating (or, later, capital) budget.

    Field names match the real, verified columns in the City's
    "Operating Budget Program Summary by Expenditure Category" open-data
    XLSX files (checked live 2026-08-05 against FY2022-2025, schema
    stable across all four) -- not the earlier guessed field set. That
    dataset has no vendor/supplier dimension (this is a program-level
    budget summary, not a transaction ledger -- vendor-level detail is
    the contracts data's job, per docs/00-scope.md §3's reuse map), so
    there's no vendor_entity FK here.
    """

    BUDGET_TYPE_CHOICES = [("operating", "Operating"), ("capital", "Capital")]
    EXPENSE_REVENUE_CHOICES = [("Expenses", "Expenses"), ("Revenues", "Revenues")]

    budget_type = models.CharField(max_length=10, choices=BUDGET_TYPE_CHOICES, default="operating")
    fiscal_year = models.PositiveIntegerField()
    program = models.CharField(max_length=300)  # top-level division/agency, e.g. "311 Toronto"
    service = models.CharField(max_length=300, blank=True, default="")
    activity = models.CharField(max_length=300, blank=True, default="")
    expense_or_revenue = models.CharField(max_length=10, choices=EXPENSE_REVENUE_CHOICES)
    category_name = models.CharField(max_length=200, blank=True, default="")
    sub_category_name = models.CharField(max_length=200, blank=True, default="")
    commitment_item = models.CharField(max_length=300, blank=True, default="")
    amount_cents = models.BigIntegerField()

    class Meta:
        indexes = [
            models.Index(fields=["fiscal_year", "program"]),
            models.Index(fields=["budget_type", "fiscal_year"]),
            models.Index(fields=["expense_or_revenue"]),
        ]

    @property
    def amount_dollars(self):
        return self.amount_cents / 100

    def __str__(self):
        return f"{self.program} / {self.service} ({self.fiscal_year}): ${self.amount_dollars:,.2f}"
