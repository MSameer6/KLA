from django.contrib import admin
from .models import Client

@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ("full_name", "cnic", "phone", "ntn", "status", "created_at")
    search_fields = ("full_name", "cnic", "phone", "ntn")
    list_filter = ("status",)
