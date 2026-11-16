from django import forms
from .models import (
    Client,
    ClientDocument,
    ClientInvoice,
    TaxCase,
    TaxCaseFile,
    TaxCaseTask,
    TaxReturn,
)

class ClientForm(forms.ModelForm):
    class Meta:
        model = Client
        fields = ["full_name", "cnic", "phone", "email", "address", "ntn", "needs_ntn_return", "needs_sales_tax", "needs_income_tax", "status"]
        widgets = {
            "full_name": forms.TextInput(attrs={"class": "form-control", "placeholder": "Enter client's full name"}),
            "cnic": forms.TextInput(attrs={"class": "form-control", "placeholder": "XXXXX-XXXXXXX-X"}),
            "phone": forms.TextInput(attrs={"class": "form-control", "placeholder": "03XXXXXXXXX"}),
            "email": forms.EmailInput(attrs={"class": "form-control", "placeholder": "example@email.com"}),
            "address": forms.Textarea(attrs={"class": "form-control", "rows": 3, "placeholder": "Enter complete address"}),
            "ntn": forms.TextInput(attrs={"class": "form-control", "placeholder": "Enter NTN (optional)"}),
            "status": forms.Select(attrs={"class": "form-select"}),
            "needs_ntn_return": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "needs_sales_tax": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "needs_income_tax": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }


class ClientDocumentForm(forms.ModelForm):
    class Meta:
        model = ClientDocument
        fields = ["client", "tax_case", "title", "document_type", "file", "notes"]
        widgets = {
            "client": forms.Select(attrs={"class": "form-select"}),
            "tax_case": forms.Select(attrs={"class": "form-select"}),
            "title": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. CNIC copy"}),
            "document_type": forms.Select(attrs={"class": "form-select"}),
            "file": forms.ClearableFileInput(attrs={"class": "form-control"}),
            "notes": forms.Textarea(attrs={"class": "form-control", "rows": 2, "placeholder": "Optional note for the client"}),
        }

    def clean_file(self):
        uploaded_file = self.cleaned_data["file"]
        if uploaded_file.size > 10 * 1024 * 1024:
            raise forms.ValidationError("Each file must be 10 MB or smaller.")
        return uploaded_file

    def clean(self):
        cleaned_data = super().clean()
        tax_case = cleaned_data.get("tax_case")
        client = cleaned_data.get("client")
        if tax_case and client and tax_case.client_id != client.pk:
            self.add_error("tax_case", "Choose a case belonging to the selected client.")
        return cleaned_data


class ClientDocumentUploadForm(forms.ModelForm):
    class Meta:
        model = ClientDocument
        fields = ["tax_case", "title", "document_type", "file", "notes"]
        widgets = {
            "tax_case": forms.Select(attrs={"class": "form-select"}),
            "title": forms.TextInput(attrs={"class": "form-control"}),
            "document_type": forms.Select(attrs={"class": "form-select"}),
            "file": forms.ClearableFileInput(attrs={"class": "form-control"}),
            "notes": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
        }

    def __init__(self, client, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["tax_case"].queryset = TaxCase.objects.filter(client=client)
        self.fields["tax_case"].required = False

    def clean_file(self):
        uploaded_file = self.cleaned_data["file"]
        if uploaded_file.size > 10 * 1024 * 1024:
            raise forms.ValidationError("Each file must be 10 MB or smaller.")
        return uploaded_file


class ClientDocumentReviewForm(forms.ModelForm):
    class Meta:
        model = ClientDocument
        fields = ["review_status", "reviewer_notes", "missing_or_corrected_request"]
        widgets = {
            "review_status": forms.Select(attrs={"class": "form-select"}),
            "reviewer_notes": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "missing_or_corrected_request": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get("review_status") == "Rejected" and not (
            cleaned_data.get("reviewer_notes") or cleaned_data.get("missing_or_corrected_request")
        ):
            self.add_error(
                "reviewer_notes",
                "Provide a reason or tell the client what corrected document is needed.",
            )
        return cleaned_data


class TaxCaseForm(forms.ModelForm):
    class Meta:
        model = TaxCase
        fields = [
            "client", "service_type", "assigned_to", "status",
            "target_date", "payment_verified", "notes",
        ]
        widgets = {
            "client": forms.Select(attrs={"class": "form-select"}),
            "service_type": forms.Select(attrs={"class": "form-select"}),
            "assigned_to": forms.Select(attrs={"class": "form-select"}),
            "status": forms.Select(attrs={"class": "form-select"}),
            "target_date": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "payment_verified": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "notes": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
        }

    def clean(self):
        cleaned_data = super().clean()
        work_statuses = {"Processing Started", "Filing in Progress", "Completed"}
        if cleaned_data.get("status") in work_statuses and not cleaned_data.get("payment_verified"):
            self.add_error(
                "payment_verified",
                "Confirm payment outside the demo portal before starting or completing work.",
            )
        return cleaned_data


class TaxCaseTaskForm(forms.ModelForm):
    class Meta:
        model = TaxCaseTask
        fields = ["title", "details", "due_date"]
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-control"}),
            "details": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
            "due_date": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
        }


class TaxCaseFileForm(forms.ModelForm):
    class Meta:
        model = TaxCaseFile
        fields = ["title", "file"]
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-control"}),
            "file": forms.ClearableFileInput(attrs={"class": "form-control"}),
        }

    def clean_file(self):
        uploaded_file = self.cleaned_data["file"]
        if uploaded_file.size > 10 * 1024 * 1024:
            raise forms.ValidationError("Each file must be 10 MB or smaller.")
        return uploaded_file


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


class ClientInvoiceForm(forms.ModelForm):
    class Meta:
        model = ClientInvoice
        fields = ["client", "description", "amount", "due_date"]
        widgets = {
            "client": forms.Select(attrs={"class": "form-select"}),
            "description": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. Income tax return preparation"}),
            "amount": forms.NumberInput(attrs={"class": "form-control", "min": "0.01", "step": "0.01", "placeholder": "0.00"}),
            "due_date": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
        }

    def clean_amount(self):
        amount = self.cleaned_data["amount"]
        if amount <= 0:
            raise forms.ValidationError("Invoice amount must be greater than zero.")
        return amount
