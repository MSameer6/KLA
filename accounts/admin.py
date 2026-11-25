from django.contrib import admin
from .models import Profile


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "role", "account_status")
    list_filter = ("role", "account_status")
    search_fields = ("user__username", "user__email", "user__first_name", "user__last_name")
