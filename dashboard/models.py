from django.db import models

class Client(models.Model):
    STATUS_CHOICES = [
        ("New", "New"),
        ("Under Review", "Under Review"),
        ("Information Pending", "Information Pending"),
        ("In Progress", "In Progress"),
        ("Completed", "Completed"),
    ]

    full_name = models.CharField(max_length=150)
    cnic = models.CharField(max_length=20, unique=True)
    phone = models.CharField(max_length=20)
    email = models.EmailField(blank=True)
    address = models.TextField(blank=True)
    ntn = models.CharField(max_length=30, blank=True)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default="New")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.full_name


class ClientDocument(models.Model):
    DOCUMENT_TYPES = [
        ("Identity", "Identity document"),
        ("Tax", "Tax document"),
        ("Financial", "Financial document"),
        ("Legal", "Legal document"),
        ("Other", "Other"),
    ]
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name="documents")
    title = models.CharField(max_length=150)
    document_type = models.CharField(max_length=20, choices=DOCUMENT_TYPES, default="Other")
    file = models.FileField(upload_to="client_documents/%Y/%m/")
    notes = models.TextField(blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-uploaded_at"]

    def __str__(self):
        return f"{self.client} — {self.title}"


class TaxReturn(models.Model):
    TAX_TYPES = [("Income Tax", "Income Tax"), ("Sales Tax", "Sales Tax")]
    STATUS_CHOICES = [
        ("Draft", "Draft"), ("Information Pending", "Information Pending"),
        ("In Review", "In Review"), ("Filed", "Filed"), ("Completed", "Completed"),
    ]
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name="tax_returns")
    tax_type = models.CharField(max_length=20, choices=TAX_TYPES)
    tax_year = models.CharField(max_length=9, help_text="For example: 2025-2026")
    due_date = models.DateField(null=True, blank=True)
    filing_reference = models.CharField(max_length=80, blank=True)
    status = models.CharField(max_length=25, choices=STATUS_CHOICES, default="Draft")
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self):
        return f"{self.client} — {self.tax_type} {self.tax_year}"
