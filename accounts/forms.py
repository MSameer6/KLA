from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import AuthenticationForm
from django.core.validators import FileExtensionValidator
from dashboard.models import Client


class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultipleFileField(forms.FileField):
    widget = MultipleFileInput

    def clean(self, data, initial=None):
        if not data:
            return []
        files = data if isinstance(data, (list, tuple)) else [data]
        return [super().clean(upload, initial) for upload in files]


class BaseRegisterForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput(attrs={"placeholder": "Create a strong password"}))
    confirm_password = forms.CharField(widget=forms.PasswordInput(attrs={"placeholder": "Confirm your password"}))
    class Meta:
        model = User
        fields = ["first_name", "last_name", "username", "email"]
        widgets = {
            "first_name": forms.TextInput(attrs={"placeholder": "First name"}),
            "last_name": forms.TextInput(attrs={"placeholder": "Last name"}),
            "username": forms.TextInput(attrs={"placeholder": "Choose username"}),
            "email": forms.EmailInput(attrs={"placeholder": "Email address"}),
        }
    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get("password") != cleaned_data.get("confirm_password"):
            raise forms.ValidationError("Passwords do not match.")
        return cleaned_data

    def clean_username(self):
        username = self.cleaned_data["username"].strip()
        if User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError("This username is already taken. Please choose another one.")
        return username


class ClientRegisterForm(BaseRegisterForm):
    cnic = forms.CharField(max_length=20, label="CNIC", widget=forms.TextInput(attrs={"placeholder": "XXXXX-XXXXXXX-X"}))
    phone = forms.CharField(max_length=20, label="Phone", widget=forms.TextInput(attrs={"placeholder": "03XXXXXXXXX"}))
    address = forms.CharField(required=False, label="Address", widget=forms.Textarea(attrs={"rows": 2, "placeholder": "Address (optional)"}))
    ntn = forms.CharField(required=False, max_length=30, label="NTN", widget=forms.TextInput(attrs={"placeholder": "NTN (if available)"}))
    business_details = forms.CharField(required=False, label="Business details", widget=forms.Textarea(attrs={"rows": 2, "placeholder": "Business name and activity (optional)"}))
    tax_information = forms.CharField(required=False, label="Tax information", widget=forms.Textarea(attrs={"rows": 2, "placeholder": "Relevant tax information (optional)"}))
    needs_ntn_return = forms.BooleanField(required=False, label="NTN & Return Filing")
    needs_sales_tax = forms.BooleanField(required=False, label="Sales Tax")
    needs_income_tax = forms.BooleanField(required=False, label="Income Tax")
    case_details = forms.CharField(
        required=False,
        label="Case details (optional)",
        widget=forms.Textarea(attrs={"rows": 3, "placeholder": "Tell us briefly what you need help with"}),
    )
    supporting_files = MultipleFileField(
        required=False,
        label="Supporting files (optional)",
        widget=MultipleFileInput(attrs={
            "accept": ".pdf,.jpg,.jpeg,.png,.doc,.docx",
            "class": "supporting-file-input",
        }),
        validators=[FileExtensionValidator(["pdf", "jpg", "jpeg", "png", "doc", "docx"])],
        help_text="Select one or more PDF, JPG, PNG, DOC or DOCX files (maximum 10 MB each).",
    )

    def clean_supporting_files(self):
        files = self.cleaned_data["supporting_files"]
        if any(upload.size > 10 * 1024 * 1024 for upload in files):
            raise forms.ValidationError("Each file must be 10 MB or smaller.")
        return files

    def clean_cnic(self):
        cnic = self.cleaned_data["cnic"].strip()
        email = self.data.get("email", "").strip()
        if Client.objects.filter(cnic=cnic).exclude(email__iexact=email).exists():
            raise forms.ValidationError("This CNIC is already registered. Please contact the office.")
        return cnic

    def clean_email(self):
        email = self.cleaned_data["email"].strip()
        if self.instance.pk is None and User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("An account with this email already exists. Please log in.")
        if self.instance.pk is None and Client.objects.filter(
            email__iexact=email,
            user__isnull=False,
        ).exists():
            raise forms.ValidationError("This client record is already linked to an account. Please log in or contact the office.")
        return email


class ClientDetailsForm(forms.Form):
    cnic = forms.CharField(max_length=20, label="CNIC", widget=forms.TextInput(attrs={"placeholder": "XXXXX-XXXXXXX-X"}))
    phone = forms.CharField(max_length=20, label="Phone", widget=forms.TextInput(attrs={"placeholder": "03XXXXXXXXX"}))
    address = forms.CharField(required=False, label="Address", widget=forms.Textarea(attrs={"rows": 2, "placeholder": "Address (optional)"}))
    ntn = forms.CharField(required=False, max_length=30, label="NTN", widget=forms.TextInput(attrs={"placeholder": "NTN (if available)"}))
    business_details = forms.CharField(required=False, label="Business details", widget=forms.Textarea(attrs={"rows": 2, "placeholder": "Business name and activity (optional)"}))
    tax_information = forms.CharField(required=False, label="Tax information", widget=forms.Textarea(attrs={"rows": 2, "placeholder": "Relevant tax information (optional)"}))
    needs_ntn_return = forms.BooleanField(required=False, label="NTN & Return Filing")
    needs_sales_tax = forms.BooleanField(required=False, label="Sales Tax")
    needs_income_tax = forms.BooleanField(required=False, label="Income Tax")
    case_details = forms.CharField(
        required=False,
        label="Case details (optional)",
        widget=forms.Textarea(attrs={"rows": 3, "placeholder": "Tell us what you need help with"}),
    )
    supporting_files = MultipleFileField(
        required=False,
        label="Supporting files (optional)",
        widget=MultipleFileInput(attrs={
            "accept": ".pdf,.jpg,.jpeg,.png,.doc,.docx",
            "class": "supporting-file-input",
        }),
        validators=[FileExtensionValidator(["pdf", "jpg", "jpeg", "png", "doc", "docx"])],
        help_text="PDF, JPG, PNG, DOC or DOCX; maximum 10 MB per file.",
    )

    def clean_cnic(self):
        cnic = self.cleaned_data["cnic"].strip()
        if Client.objects.filter(cnic=cnic).exists():
            raise forms.ValidationError("This CNIC is already registered. Please contact the office.")
        return cnic

    def clean_supporting_files(self):
        files = self.cleaned_data["supporting_files"]
        if any(upload.size > 10 * 1024 * 1024 for upload in files):
            raise forms.ValidationError("Each file must be 10 MB or smaller.")
        return files


class ClientServiceRequestForm(forms.Form):
    address = forms.CharField(
        required=False,
        label="Address",
        widget=forms.Textarea(attrs={"rows": 2, "placeholder": "Your residential or business address"}),
    )
    ntn = forms.CharField(
        required=False,
        max_length=30,
        label="NTN",
        widget=forms.TextInput(attrs={"placeholder": "NTN (if available)"}),
    )
    business_details = forms.CharField(
        required=False,
        label="Business details",
        widget=forms.Textarea(attrs={"rows": 2, "placeholder": "Business name and activity (if applicable)"}),
    )
    tax_information = forms.CharField(
        required=False,
        label="Tax information",
        widget=forms.Textarea(attrs={"rows": 2, "placeholder": "Relevant tax information"}),
    )
    needs_ntn_return = forms.BooleanField(required=False, label="NTN & Return Filing")
    needs_sales_tax = forms.BooleanField(required=False, label="Sales Tax")
    needs_income_tax = forms.BooleanField(required=False, label="Income Tax")
    case_details = forms.CharField(
        required=False,
        label="Case details (optional)",
        widget=forms.Textarea(attrs={"rows": 3, "placeholder": "Tell us what you need help with"}),
    )
    supporting_files = MultipleFileField(
        required=False,
        label="Supporting files (optional)",
        widget=MultipleFileInput(attrs={
            "accept": ".pdf,.jpg,.jpeg,.png,.doc,.docx",
            "class": "supporting-file-input",
        }),
        validators=[FileExtensionValidator(["pdf", "jpg", "jpeg", "png", "doc", "docx"])],
        help_text="PDF, JPG, PNG, DOC or DOCX; maximum 10 MB per file.",
    )

    def clean_supporting_files(self):
        files = self.cleaned_data["supporting_files"]
        if any(upload.size > 10 * 1024 * 1024 for upload in files):
            raise forms.ValidationError("Each file must be 10 MB or smaller.")
        return files


class StaffRegisterForm(BaseRegisterForm):
    pass

class LoginForm(AuthenticationForm):
    username = forms.CharField(widget=forms.TextInput(attrs={"placeholder": "Username"}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={"placeholder": "Password"}))
