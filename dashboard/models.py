from django.db import models
from django.core.validators import FileExtensionValidator
from django.contrib.auth.models import User

class Service(models.Model):
    FIELD_CHOICES = [
        ("full_name", "Full name"), ("cnic", "CNIC / NIC number"), ("phone", "Contact number"),
        ("email", "Email address"), ("address", "Address"), ("business_details", "Business details"),
        ("ntn", "Existing NTN"), ("tax_information", "Tax information"),
    ]
    name = models.CharField(max_length=80, unique=True)
    is_active = models.BooleanField(default=True)
    required_registration_fields = models.JSONField(default=list, blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

class ActivityLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="system_activities")
    client = models.ForeignKey("Client", on_delete=models.SET_NULL, null=True, blank=True, related_name="activity_logs")
    tax_case = models.ForeignKey("TaxCase", on_delete=models.SET_NULL, null=True, blank=True, related_name="activity_logs")
    action = models.CharField(max_length=120)
    description = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.action} — {self.created_at:%d %b %Y}"

class Client(models.Model):
    SERVICE_CHOICES = [
        ("NTN Registration", "NTN Registration"),
        ("Income Tax", "Income Tax"),
        ("Sales Tax", "Sales Tax"),
        ("Return Filing", "Return Filing"),
    ]
    STATUS_CHOICES = [
        ("New", "New"),
        ("Under Review", "Under Review"),
        ("Information Pending", "Information Pending"),
        ("In Progress", "In Progress"),
        ("Completed", "Completed"),
    ]

    # Legacy staff-created records can remain unlinked; portal registrations
    # always receive this account link when the profile is created.
    user = models.OneToOneField(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="client_profile")
    full_name = models.CharField(max_length=150)
    cnic = models.CharField(max_length=20, unique=True)
    phone = models.CharField(max_length=20)
    email = models.EmailField(blank=True)
    address = models.TextField(blank=True)
    business_details = models.TextField(blank=True)
    ntn = models.CharField(max_length=30, blank=True)
    tax_information = models.TextField(blank=True)
    requested_services = models.JSONField(default=list, blank=True)
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
    REVIEW_STATUS_CHOICES = [("Pending", "Pending"), ("Approved", "Approved"), ("Rejected", "Rejected")]
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name="documents")
    title = models.CharField(max_length=150)
    document_type = models.CharField(max_length=20, choices=DOCUMENT_TYPES, default="Other")
    file = models.FileField(upload_to="client_documents/%Y/%m/", validators=[FileExtensionValidator(["pdf", "jpg", "jpeg", "png", "doc", "docx"])], help_text="PDF, JPG, PNG, DOC or DOCX; maximum 10 MB.")
    notes = models.TextField(blank=True)
    review_status = models.CharField(max_length=10, choices=REVIEW_STATUS_CHOICES, default="Pending")
    reviewer_notes = models.TextField(blank=True, help_text="Visible to the client.")
    missing_or_corrected_request = models.TextField(blank=True, verbose_name="Missing or corrected document request")
    reviewed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="reviewed_client_documents")
    reviewed_at = models.DateTimeField(null=True, blank=True)
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


class TaxCase(models.Model):
    """A service request owned by one client; clients may have many cases."""
    SERVICE_TYPES = [("NTN Registration", "NTN Registration"), ("Income Tax", "Income Tax"), ("Sales Tax", "Sales Tax"), ("Return Filing", "Return Filing")]
    STATUS_CHOICES = [("Newly Registered", "Newly Registered"), ("Under Review", "Under Review"), ("Information Pending", "Information Pending"), ("Processing Started", "Processing Started"), ("Filing in Progress", "Filing in Progress"), ("Completed", "Completed")]
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name="tax_cases")
    service_type = models.CharField(max_length=30, choices=SERVICE_TYPES)
    status = models.CharField(max_length=25, choices=STATUS_CHOICES, default="Newly Registered")
    assigned_to = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="assigned_tax_cases", verbose_name="Staff / tax adviser")
    opened_date = models.DateField(auto_now_add=True)
    target_date = models.DateField(null=True, blank=True, verbose_name="Target completion date")
    completed_date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True, verbose_name="Case notes")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self):
        return f"{self.client} — {self.service_type}"


class TaxCaseTask(models.Model):
    case = models.ForeignKey(TaxCase, on_delete=models.CASCADE, related_name="tasks")
    title = models.CharField(max_length=160)
    details = models.TextField(blank=True)
    is_complete = models.BooleanField(default=False)
    due_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["is_complete", "due_date", "created_at"]
