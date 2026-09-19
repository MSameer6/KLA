from django.contrib import admin
from .models import ActivityLog, Client, ClientDocument, Service, TaxCase, TaxCaseTask, TaxReturn

@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ("full_name", "cnic", "phone", "ntn", "status", "created_at")
    search_fields = ("full_name", "cnic", "phone", "ntn")
    list_filter = ("status",)

@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ("name", "is_active")
    list_filter = ("is_active",)

@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    list_display = ("action", "user", "created_at")
    list_filter = ("action", "created_at")
    search_fields = ("action", "description", "user__username")
    readonly_fields = ("user", "action", "description", "created_at")

admin.site.register(ClientDocument)
admin.site.register(TaxReturn)
admin.site.register(TaxCase)
admin.site.register(TaxCaseTask)
