from django.contrib import admin

from .models import Group, Membership


class MembershipInline(admin.TabularInline):
    model = Membership
    extra = 0


@admin.register(Group)
class GroupAdmin(admin.ModelAdmin):
    list_display = ("name", "base_currency", "created_by", "created_at")
    inlines = [MembershipInline]