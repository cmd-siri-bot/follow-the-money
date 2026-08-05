from django.contrib import admin

from .models import FactLobbyingCommunication, FactLobbyingRegistration


class FactLobbyingCommunicationInline(admin.TabularInline):
    model = FactLobbyingCommunication
    extra = 0
    fields = ("poh_name", "poh_office", "communication_date", "communication_method")
    readonly_fields = fields


@admin.register(FactLobbyingRegistration)
class FactLobbyingRegistrationAdmin(admin.ModelAdmin):
    list_display = (
        "subject_matter_number",
        "registrant",
        "registrant_type",
        "beneficiary",
        "firm",
        "status",
        "effective_date",
    )
    list_filter = ("registrant_type", "status")
    search_fields = ("subject_matter_number", "subject_matter", "particulars")
    autocomplete_fields = ("registrant", "beneficiary", "firm")
    inlines = [FactLobbyingCommunicationInline]


@admin.register(FactLobbyingCommunication)
class FactLobbyingCommunicationAdmin(admin.ModelAdmin):
    list_display = ("registration", "poh_name", "poh_office", "communication_date", "communication_method")
    list_filter = ("communication_method",)
    search_fields = ("poh_name", "poh_office")
    autocomplete_fields = ("registration", "poh_entity", "lobbyist_entity")
