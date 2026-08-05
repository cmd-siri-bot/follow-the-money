from django.contrib import admin

from .models import FactGrant


@admin.register(FactGrant)
class FactGrantAdmin(admin.ModelAdmin):
    list_display = (
        "recipient_name_raw",
        "funding_program_code",
        "funding_program_name",
        "fiscal_year",
        "ward",
        "service_area",
        "amount_display",
    )
    list_filter = ("fiscal_year", "funding_program_code", "service_area")
    search_fields = ("recipient_name_raw", "funding_program_code", "funding_program_name", "division")
    autocomplete_fields = ("recipient",)

    @admin.display(description="Amount")
    def amount_display(self, obj):
        return f"${obj.amount_dollars:,.2f}"
