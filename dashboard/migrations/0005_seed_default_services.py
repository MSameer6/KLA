from django.db import migrations


def seed_default_services(apps, schema_editor):
    Service = apps.get_model("dashboard", "Service")
    defaults = {
        "NTN Registration": ["full_name", "cnic", "phone", "email", "address", "tax_information"],
        "Income Tax": ["full_name", "cnic", "phone", "email", "address", "tax_information"],
        "Sales Tax": ["full_name", "cnic", "phone", "email", "address", "business_details", "tax_information"],
        "Return Filing": ["full_name", "cnic", "phone", "email", "address", "tax_information"],
    }
    for name, required_fields in defaults.items():
        Service.objects.get_or_create(name=name, defaults={"required_registration_fields": required_fields, "is_active": True})


def remove_default_services(apps, schema_editor):
    Service = apps.get_model("dashboard", "Service")
    Service.objects.filter(name__in=["NTN Registration", "Income Tax", "Sales Tax", "Return Filing"]).delete()


class Migration(migrations.Migration):
    dependencies = [("dashboard", "0004_service_activitylog")]
    operations = [migrations.RunPython(seed_default_services, remove_default_services)]
