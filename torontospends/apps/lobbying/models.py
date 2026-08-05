from django.db import models

from apps.entities.models import Entity, SourcedFact


class FactLobbyingRegistration(SourcedFact):
    """One active lobbyist registration (a 'subject matter' in the
    registry's own terms). Field set is mapped directly against the real
    columns in Follow the Money's already-ingested
    data/interim/lobbyist_subject_matters.csv /
    lobbyist_beneficiaries.csv / lobbyist_firms.csv -- not guessed, per
    the reuse map in docs/00-scope.md §3.
    """

    REGISTRANT_TYPE_CHOICES = [
        ("In-house", "In-house"),
        ("Consultant", "Consultant"),
        ("Voluntary", "Voluntary Unpaid"),
    ]

    subject_matter_number = models.CharField(max_length=50, unique=True, db_index=True)
    status = models.CharField(max_length=50)
    registrant_type = models.CharField(max_length=20, choices=REGISTRANT_TYPE_CHOICES)
    registrant = models.ForeignKey(
        Entity, on_delete=models.PROTECT, related_name="lobbying_registrations_as_registrant"
    )
    registrant_position_title = models.CharField(max_length=300, blank=True, default="")
    # The client/beneficiary the registrant lobbies on behalf of. For
    # Consultant-type registrants this is distinct from the firm they work
    # for (firm_entity below); for In-house it's typically the same org.
    beneficiary = models.ForeignKey(
        Entity, null=True, blank=True, on_delete=models.SET_NULL, related_name="lobbying_registrations_as_beneficiary"
    )
    firm = models.ForeignKey(
        Entity, null=True, blank=True, on_delete=models.SET_NULL, related_name="lobbying_registrations_as_firm"
    )
    subject_matter = models.CharField(max_length=300, blank=True, default="")
    particulars = models.TextField(blank=True, default="")
    initial_approval_date = models.DateField(null=True, blank=True)
    effective_date = models.DateField(null=True, blank=True)
    proposed_start_date = models.DateField(null=True, blank=True)
    proposed_end_date = models.DateField(null=True, blank=True)

    class Meta:
        indexes = [models.Index(fields=["registrant_type", "status"])]

    def __str__(self):
        return f"{self.subject_matter_number}: {self.subject_matter}"


class FactLobbyingCommunication(SourcedFact):
    """One logged lobbying contact with a public office holder, from
    Follow the Money's already-ingested
    data/interim/lobbyist_communications.csv (140,921 rows, 89,443 with a
    named POH). Per docs/08-decision-log.md's 2026-08-03 correction: this
    is evidence contact happened at least once, NOT a volume/intensity
    measure -- the registry only logs what's voluntarily filed. Any
    dashboard or flag built on this table must not present contact counts
    as a "who was lobbied the most" ranking.
    """

    registration = models.ForeignKey(
        FactLobbyingRegistration, on_delete=models.CASCADE, related_name="communications"
    )
    poh_office = models.CharField(max_length=300, blank=True, default="")
    poh_type = models.CharField(max_length=100, blank=True, default="")
    poh_position = models.CharField(max_length=300, blank=True, default="")
    poh_name = models.CharField(max_length=300, blank=True, default="")
    poh_entity = models.ForeignKey(
        Entity, null=True, blank=True, on_delete=models.SET_NULL, related_name="lobbying_contacts_received"
    )
    # Not a short category -- real data includes "Other:<free text>" tails up to
    # 140 chars (verified against lobbyist_communications.csv before widening this).
    communication_method = models.CharField(max_length=500, blank=True, default="")
    communication_date = models.DateField(null=True, blank=True)
    lobbyist_entity = models.ForeignKey(
        Entity, null=True, blank=True, on_delete=models.SET_NULL, related_name="lobbying_contacts_made"
    )

    class Meta:
        indexes = [models.Index(fields=["communication_date"])]

    def __str__(self):
        return f"{self.registration.subject_matter_number} -> {self.poh_name} ({self.communication_date})"
