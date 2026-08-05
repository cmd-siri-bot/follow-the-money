from django.db import models

from apps.entities.models import Entity, SourcedFact


class FactGrant(SourcedFact):
    """One organization's grant allocation under a City community grant
    program, for one fiscal year.

    Field names match the real, verified columns in the City's
    "Community Grants Allocations" open-data CKAN dataset (resource
    "Community Grants Allocations since 2022", checked live 2026-08-05
    during the Oct-20 grant-program-cut decision -- see
    docs/08-decision-log.md's "Grant program cut for Oct 20 confirmed"
    entry). One row per organization per program per year; a single
    organization can have multiple rows across years or programs.

    Unlike the operating budget dataset, this one already covers every
    City grant program (105 distinct codes as of the last check) through
    a single unified source -- not per-program adapters.
    """

    fiscal_year = models.PositiveIntegerField()
    # Not always a short acronym -- some rows carry the full program name
    # directly here instead of a code (e.g. "Strategic Policy and Management
    # Services  Event Sponsorships", 60 chars), verified against real data.
    funding_program_code = models.CharField(max_length=300)  # e.g. "TAC", "CSP", or occasionally a full name
    funding_program_name = models.CharField(max_length=300, blank=True, default="")  # looked up from the programs resource
    division = models.CharField(max_length=300, blank=True, default="")
    recipient = models.ForeignKey(Entity, null=True, blank=True, on_delete=models.SET_NULL, related_name="grants_received")
    recipient_name_raw = models.CharField(max_length=500)  # kept even when recipient resolution fails, so nothing is silently dropped
    # Not a single ward -- city-wide programs list many, comma-separated (up to
    # 243 chars observed; verified against the real data before widening this).
    ward = models.CharField(max_length=1000, blank=True, default="")
    service_area = models.CharField(max_length=50, blank=True, default="")  # City-Wide / Local / Neighbourhood, per the source's own field notes -- not enforced as a hard choice in case other values appear
    total_number_of_grants = models.PositiveIntegerField(default=1)
    amount_cents = models.BigIntegerField()

    class Meta:
        indexes = [
            models.Index(fields=["fiscal_year", "funding_program_code"]),
            models.Index(fields=["funding_program_code"]),
        ]

    @property
    def amount_dollars(self):
        return self.amount_cents / 100

    def __str__(self):
        return f"{self.recipient_name_raw} -- {self.funding_program_code} ({self.fiscal_year}): ${self.amount_dollars:,.2f}"
