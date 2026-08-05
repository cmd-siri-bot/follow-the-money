from django.contrib import admin

from .models import FactBudgetLine


@admin.register(FactBudgetLine)
class FactBudgetLineAdmin(admin.ModelAdmin):
    list_display = (
        "program",
        "service",
        "fiscal_year",
        "expense_or_revenue",
        "category_name",
        "commitment_item",
        "amount_display",
    )
    list_filter = ("budget_type", "fiscal_year", "expense_or_revenue", "program")
    search_fields = ("program", "service", "activity", "category_name", "commitment_item")

    @admin.display(description="Amount")
    def amount_display(self, obj):
        return f"${obj.amount_cents / 100:,.2f}"
