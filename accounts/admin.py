from django.contrib import admin
from .models import Profile

@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "role", "account_status", "can_manage_clients", "can_manage_documents", "can_manage_tax_work")
    list_filter = ("role", "account_status")
    search_fields = ("user__username", "user__email")
