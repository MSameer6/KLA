from django.core.validators import FileExtensionValidator
from django.db import models
from django.conf import settings


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
    business_details = models.TextField(blank=True)
    requested_services = models.JSONField(blank=True, default=list)
    tax_information = models.TextField(blank=True)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="client_profile",
    )
    needs_ntn_return = models.BooleanField(default=False, verbose_name="NTN & Return Filing")
    needs_sales_tax = models.BooleanField(default=False, verbose_name="Sales Tax")
    needs_income_tax = models.BooleanField(default=False, verbose_name="Income Tax")
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default="New")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.full_name


class TaxCase(models.Model):
    SERVICE_TYPES = [
        ("NTN Registration", "NTN Registration"),
        ("Income Tax", "Income Tax"),
        ("Sales Tax", "Sales Tax"),
        ("Return Filing", "Return Filing"),
    ]
    STATUS_CHOICES = [
        ("Newly Registered", "Newly Registered"),
        ("Under Review", "Under Review"),
        ("Information Pending", "Information Pending"),
        ("Processing Started", "Processing Started"),
        ("Filing in Progress", "Filing in Progress"),
        ("Completed", "Completed"),
    ]
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name="tax_cases")
    service_type = models.CharField(max_length=30, choices=SERVICE_TYPES)
    status = models.CharField(max_length=25, choices=STATUS_CHOICES, default="Newly Registered")
    opened_date = models.DateField(auto_now_add=True)
    target_date = models.DateField(null=True, blank=True, verbose_name="Target completion date")
    completed_date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True, verbose_name="Case notes")
    payment_verified = models.BooleanField(
        default=False,
        help_text="Staff confirms payment outside this demo portal before work begins.",
    )
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_tax_cases",
        verbose_name="Staff / tax adviser",
    )
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

    def __str__(self):
        return self.title


class TaxCaseFile(models.Model):
    case = models.ForeignKey(TaxCase, on_delete=models.CASCADE, related_name="files")
    title = models.CharField(max_length=150)
    file = models.FileField(
        upload_to="tax_case_files/%Y/%m/",
        validators=[FileExtensionValidator(["pdf", "jpg", "jpeg", "png", "doc", "docx"])],
    )
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="uploaded_tax_case_files",
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-uploaded_at"]

    def __str__(self):
        return f"{self.case} — {self.title}"


class ClientNotification(models.Model):
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name="notifications")
    tax_case = models.ForeignKey(
        TaxCase,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="notifications",
    )
    title = models.CharField(max_length=150)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.client} — {self.title}"


class Service(models.Model):
    name = models.CharField(max_length=80, unique=True)
    is_active = models.BooleanField(default=True)
    required_registration_fields = models.JSONField(blank=True, default=list)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class ActivityLog(models.Model):
    action = models.CharField(max_length=120)
    description = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="system_activities",
    )
    client = models.ForeignKey(
        Client,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="activity_logs",
    )
    tax_case = models.ForeignKey(
        TaxCase,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="activity_logs",
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.action


class ClientDocument(models.Model):
    DOCUMENT_TYPES = [
        ("Identity", "Identity document"),
        ("Tax", "Tax document"),
        ("Financial", "Financial document"),
        ("Legal", "Legal document"),
        ("Other", "Other"),
    ]
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name="documents")
    tax_case = models.ForeignKey(
        TaxCase,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="documents",
    )
    title = models.CharField(max_length=150)
    document_type = models.CharField(max_length=20, choices=DOCUMENT_TYPES, default="Other")
    file = models.FileField(
        upload_to="client_documents/%Y/%m/",
        validators=[FileExtensionValidator(["pdf", "jpg", "jpeg", "png", "doc", "docx"])],
        help_text="PDF, JPG, PNG, DOC or DOCX; maximum 10 MB.",
    )
    notes = models.TextField(blank=True)
    review_status = models.CharField(
        max_length=10,
        choices=[("Pending", "Pending"), ("Approved", "Approved"), ("Rejected", "Rejected")],
        default="Pending",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_client_documents",
    )
    reviewer_notes = models.TextField(blank=True, help_text="Visible to the client.")
    missing_or_corrected_request = models.TextField(blank=True, verbose_name="Missing or corrected document request")
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


class ClientInvoice(models.Model):
    STATUS_CHOICES = [("Pending", "Pending"), ("Paid", "Paid")]

    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name="invoices")
    description = models.CharField(max_length=180)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    due_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="Pending")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_client_invoices",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(condition=models.Q(amount__gt=0), name="client_invoice_amount_positive"),
        ]

    @property
    def invoice_number(self):
        return f"KLA-{self.created_at:%Y}-{self.pk:05d}"

    def __str__(self):
        return f"{self.invoice_number} — {self.client}"
