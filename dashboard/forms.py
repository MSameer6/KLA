from django import forms
from .models import Client, ClientDocument, TaxReturn

class ClientForm(forms.ModelForm):
    class Meta:
        model = Client
        fields = ["full_name", "cnic", "phone", "email", "address", "ntn", "status"]
        widgets = {
            "full_name": forms.TextInput(attrs={"class": "form-control", "placeholder": "Enter client's full name"}),
            "cnic": forms.TextInput(attrs={"class": "form-control", "placeholder": "XXXXX-XXXXXXX-X"}),
            "phone": forms.TextInput(attrs={"class": "form-control", "placeholder": "03XXXXXXXXX"}),
            "email": forms.EmailInput(attrs={"class": "form-control", "placeholder": "example@email.com"}),
            "address": forms.Textarea(attrs={"class": "form-control", "rows": 3, "placeholder": "Enter complete address"}),
            "ntn": forms.TextInput(attrs={"class": "form-control", "placeholder": "Enter NTN (optional)"}),
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
