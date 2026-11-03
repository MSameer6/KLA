from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("dashboard", "0002_clientdocument_taxreturn"),
    ]

    operations = [
        migrations.AddField(
            model_name="client",
            name="needs_ntn_return",
            field=models.BooleanField(default=False, verbose_name="NTN & Return Filing"),
        ),
        migrations.AddField(
            model_name="client",
            name="needs_sales_tax",
            field=models.BooleanField(default=False, verbose_name="Sales Tax"),
        ),
        migrations.AddField(
            model_name="client",
            name="needs_income_tax",
            field=models.BooleanField(default=False, verbose_name="Income Tax"),
        ),
    ]
