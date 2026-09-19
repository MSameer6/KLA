from django import forms
from django.contrib.auth.models import User
from .models import Client, ClientDocument, Service, TaxCase, TaxCaseTask, TaxReturn

ALLOWED_DOCUMENT_EXTENSIONS = {"pdf", "jpg", "jpeg", "png", "doc", "docx"}
MAX_DOCUMENT_SIZE = 10 * 1024 * 1024

def validate_uploaded_document(upload):
    if upload.size > MAX_DOCUMENT_SIZE:
        raise forms.ValidationError("File size must be 10 MB or less.")
    extension = upload.name.rsplit(".", 1)[-1].lower() if "." in upload.name else ""
    if extension not in ALLOWED_DOCUMENT_EXTENSIONS:
        raise forms.ValidationError("Upload a PDF, JPG, PNG, DOC, or DOCX file.")
    return upload

class ServiceConfigurationForm(forms.ModelForm):
    required_registration_fields = forms.MultipleChoiceField(
        choices=Service.FIELD_CHOICES,
        required=False,
        widget=forms.CheckboxSelectMultiple,
        help_text="Selected fields become required when a client chooses this service during registration.",
    )

    class Meta:
        model = Service
        fields = ["name", "is_active", "required_registration_fields"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

class ClientForm(forms.ModelForm):
    class Meta:
        model = Client
        fields = ["full_name", "cnic", "phone", "email", "address", "business_details", "ntn", "tax_information", "requested_services", "status"]
        widgets = {
            "full_name": forms.TextInput(attrs={"class": "form-control", "placeholder": "Enter client's full name"}),
            "cnic": forms.TextInput(attrs={"class": "form-control", "placeholder": "XXXXX-XXXXXXX-X"}),
            "phone": forms.TextInput(attrs={"class": "form-control", "placeholder": "03XXXXXXXXX"}),
            "email": forms.EmailInput(attrs={"class": "form-control", "placeholder": "example@email.com"}),
            "address": forms.Textarea(attrs={"class": "form-control", "rows": 3, "placeholder": "Enter complete address"}),
            "business_details": forms.Textarea(attrs={"class": "form-control", "rows": 3, "placeholder": "Business name, type and relevant details"}),
            "ntn": forms.TextInput(attrs={"class": "form-control", "placeholder": "Enter NTN (optional)"}),
            "tax_information": forms.Textarea(attrs={"class": "form-control", "rows": 3, "placeholder": "Relevant tax information"}),
            "requested_services": forms.CheckboxSelectMultiple(choices=Client.SERVICE_CHOICES),
            "status": forms.Select(attrs={"class": "form-select"}),
        }


class ClientDocumentForm(forms.ModelForm):
    class Meta:
        model = ClientDocument
        fields = ["client", "title", "document_type", "file", "notes"]
        widgets = {
            "client": forms.Select(attrs={"class": "form-select"}),
            "title": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. CNIC copy"}),
            "document_type": forms.Select(attrs={"class": "form-select"}),
            "file": forms.ClearableFileInput(attrs={"class": "form-control"}),
            "notes": forms.Textarea(attrs={"class": "form-control", "rows": 2, "placeholder": "Optional note for the client"}),
        }

    def clean_file(self):
        return validate_uploaded_document(self.cleaned_data["file"])


class DocumentReviewForm(forms.ModelForm):
    class Meta:
        model = ClientDocument
        fields = ["review_status", "reviewer_notes", "missing_or_corrected_request"]
        widgets = {
            "review_status": forms.Select(attrs={"class": "form-select"}),
            "reviewer_notes": forms.Textarea(attrs={"class": "form-control", "rows": 3, "placeholder": "Explain the review outcome to the client"}),
            "missing_or_corrected_request": forms.Textarea(attrs={"class": "form-control", "rows": 3, "placeholder": "Specify the document or correction needed"}),
        }


class TaxCaseForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["assigned_to"].queryset = User.objects.filter(profile__role__in=["STAFF", "ADMIN"], profile__account_status="ACTIVE").order_by("first_name", "username")

    class Meta:
        model = TaxCase
        fields = ["client", "service_type", "status", "assigned_to", "target_date", "completed_date", "notes"]
        widgets = {
            "client": forms.Select(attrs={"class": "form-select"}), "service_type": forms.Select(attrs={"class": "form-select"}),
            "status": forms.Select(attrs={"class": "form-select"}), "assigned_to": forms.Select(attrs={"class": "form-select"}),
            "target_date": forms.DateInput(attrs={"class": "form-control", "type": "date"}), "completed_date": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "notes": forms.Textarea(attrs={"class": "form-control", "rows": 4, "placeholder": "Internal case notes and handover context"}),
        }


class TaxCaseTaskForm(forms.ModelForm):
    class Meta:
        model = TaxCaseTask
        fields = ["title", "details", "due_date"]
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. Verify CNIC details"}),
            "details": forms.Textarea(attrs={"class": "form-control", "rows": 2, "placeholder": "Optional internal instructions"}),
            "due_date": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
        }


class TaxReturnForm(forms.ModelForm):
    class Meta:
        model = TaxReturn
        fields = ["client", "tax_type", "tax_year", "due_date", "filing_reference", "status", "notes"]
        widgets = {
            "client": forms.Select(attrs={"class": "form-select"}),
            "tax_type": forms.Select(attrs={"class": "form-select"}),
            "tax_year": forms.TextInput(attrs={"class": "form-control", "placeholder": "2025-2026"}),
            "due_date": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "filing_reference": forms.TextInput(attrs={"class": "form-control", "placeholder": "Optional filing reference"}),
            "status": forms.Select(attrs={"class": "form-select"}),
            "notes": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }
