from django.contrib import admin

from .models import Expense, ExpenseShare


class ExpenseShareInline(admin.TabularInline):
    model = ExpenseShare
    extra = 0


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ("description", "group", "amount", "paid_by", "date", "split_mode")
    inlines = [ExpenseShareInline]