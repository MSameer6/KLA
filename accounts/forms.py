from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import AuthenticationForm
from dashboard.models import ActivityLog, Client, Service
from .models import Profile
from dashboard.models import ClientDocument
from dashboard.forms import validate_uploaded_document

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

class ClientRegisterForm(BaseRegisterForm):
    cnic = forms.CharField(max_length=20, label="CNIC / NIC number", widget=forms.TextInput(attrs={"placeholder": "XXXXX-XXXXXXX-X"}))
    phone = forms.CharField(max_length=20, label="Contact number", widget=forms.TextInput(attrs={"placeholder": "03XXXXXXXXX"}))
    address = forms.CharField(label="Residential or business address", widget=forms.Textarea(attrs={"placeholder": "Enter your complete address", "rows": 3}))
    business_details = forms.CharField(required=False, widget=forms.Textarea(attrs={"placeholder": "Business name, type and relevant details (if applicable)", "rows": 3}))
    ntn = forms.CharField(required=False, label="Existing NTN", widget=forms.TextInput(attrs={"placeholder": "Enter NTN if applicable"}))
    tax_information = forms.CharField(label="Tax-related information", widget=forms.Textarea(attrs={"placeholder": "Briefly provide relevant tax information", "rows": 3}))
    requested_services = forms.MultipleChoiceField(choices=(), label="Services required", widget=forms.CheckboxSelectMultiple, help_text="Select one or more services you need.")
    supporting_document = forms.FileField(required=False, label="Supporting document", help_text="Optional: upload a document to include with your registration.")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        services = list(Service.objects.filter(is_active=True))
        # A safe fallback preserves registration until the initial service
        # configuration migration has been applied.
        self.services_by_name = {service.name: service for service in services}
        self.fields["requested_services"].choices = [(service.name, service.name) for service in services] or Client.SERVICE_CHOICES

    def clean_cnic(self):
        cnic = self.cleaned_data["cnic"].strip()
        if Client.objects.filter(cnic__iexact=cnic).exists():
            raise forms.ValidationError("A client profile with this CNIC / NIC number already exists.")
        return cnic

    def clean(self):
        cleaned_data = super().clean()
        selected_services = cleaned_data.get("requested_services", [])
        for service_name in selected_services:
            service = self.services_by_name.get(service_name)
            if not service:
                continue
            for field_name in service.required_registration_fields:
                if field_name in self.fields and not cleaned_data.get(field_name):
                    label = self.fields[field_name].label
                    self.add_error(field_name, f"{label} is required for {service.name}.")
        return cleaned_data

    def clean_supporting_document(self):
        document = self.cleaned_data.get("supporting_document")
        return validate_uploaded_document(document) if document else document

class ClientProfileForm(forms.ModelForm):
    """Client-editable fields only; staff workflow status stays staff-managed."""
    class Meta:
        model = Client
        fields = ["full_name", "cnic", "phone", "email", "address", "business_details", "ntn", "tax_information", "requested_services"]
        widgets = {
            "full_name": forms.TextInput(attrs={"placeholder": "Your full name"}),
            "cnic": forms.TextInput(attrs={"placeholder": "XXXXX-XXXXXXX-X"}),
            "phone": forms.TextInput(attrs={"placeholder": "03XXXXXXXXX"}),
            "email": forms.EmailInput(attrs={"placeholder": "Email address"}),
            "address": forms.Textarea(attrs={"rows": 3, "placeholder": "Residential or business address"}),
            "business_details": forms.Textarea(attrs={"rows": 3, "placeholder": "Business name, type and relevant details"}),
            "ntn": forms.TextInput(attrs={"placeholder": "Existing NTN, if applicable"}),
            "tax_information": forms.Textarea(attrs={"rows": 3, "placeholder": "Relevant tax information"}),
            "requested_services": forms.CheckboxSelectMultiple(choices=Client.SERVICE_CHOICES),
        }

    def clean_cnic(self):
        cnic = self.cleaned_data["cnic"].strip()
        if Client.objects.filter(cnic__iexact=cnic).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("A client profile with this CNIC / NIC number already exists.")
        return cnic

class ClientDocumentUploadForm(forms.ModelForm):
    class Meta:
        model = ClientDocument
        fields = ["title", "document_type", "file", "notes"]
        widgets = {
            "title": forms.TextInput(attrs={"placeholder": "For example: CNIC copy"}),
            "document_type": forms.Select(),
            "file": forms.ClearableFileInput(),
            "notes": forms.Textarea(attrs={"rows": 3, "placeholder": "Optional note for Khan Law Associates"}),
        }

    def clean_file(self):
        return validate_uploaded_document(self.cleaned_data["file"])

class StaffRegisterForm(BaseRegisterForm):
    pass

class LoginForm(AuthenticationForm):
    username = forms.CharField(widget=forms.TextInput(attrs={"placeholder": "Username"}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={"placeholder": "Password"}))

class StaffCreateForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput(attrs={"class": "form-control"}))
    account_status = forms.ChoiceField(choices=Profile.ACCOUNT_STATUS_CHOICES, widget=forms.Select(attrs={"class": "form-select"}))
    can_manage_clients = forms.BooleanField(required=False, initial=True, widget=forms.CheckboxInput(attrs={"class": "form-check-input"}))
    can_manage_documents = forms.BooleanField(required=False, initial=True, widget=forms.CheckboxInput(attrs={"class": "form-check-input"}))
    can_manage_tax_work = forms.BooleanField(required=False, initial=True, widget=forms.CheckboxInput(attrs={"class": "form-check-input"}))

    class Meta:
        model = User
        fields = ["first_name", "last_name", "username", "email"]
        widgets = {
            "first_name": forms.TextInput(attrs={"class": "form-control"}),
            "last_name": forms.TextInput(attrs={"class": "form-control"}),
            "username": forms.TextInput(attrs={"class": "form-control"}),
            "email": forms.EmailInput(attrs={"class": "form-control"}),
        }

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"])
        user.is_active = self.cleaned_data["account_status"] == "ACTIVE"
        if commit:
            user.save()
            profile = user.profile
            profile.role = "STAFF"
            profile.account_status = self.cleaned_data["account_status"]
            profile.can_manage_clients = self.cleaned_data["can_manage_clients"]
            profile.can_manage_documents = self.cleaned_data["can_manage_documents"]
            profile.can_manage_tax_work = self.cleaned_data["can_manage_tax_work"]
            profile.save()
        return user

class AccountManagementForm(forms.Form):
    role = forms.ChoiceField(choices=Profile.ROLE_CHOICES, widget=forms.Select(attrs={"class": "form-select"}))
    account_status = forms.ChoiceField(choices=Profile.ACCOUNT_STATUS_CHOICES, widget=forms.Select(attrs={"class": "form-select"}))
    can_manage_clients = forms.BooleanField(required=False, widget=forms.CheckboxInput(attrs={"class": "form-check-input"}))
    can_manage_documents = forms.BooleanField(required=False, widget=forms.CheckboxInput(attrs={"class": "form-check-input"}))
    can_manage_tax_work = forms.BooleanField(required=False, widget=forms.CheckboxInput(attrs={"class": "form-check-input"}))

    def __init__(self, *args, user=None, **kwargs):
        self.managed_user = user
        initial = kwargs.setdefault("initial", {})
        if user and not args:
            initial.update({
                "role": user.profile.role, "account_status": user.profile.account_status,
                "can_manage_clients": user.profile.can_manage_clients,
                "can_manage_documents": user.profile.can_manage_documents,
                "can_manage_tax_work": user.profile.can_manage_tax_work,
            })
        super().__init__(*args, **kwargs)

    def save(self):
        profile = self.managed_user.profile
        profile.role = self.cleaned_data["role"]
        profile.account_status = self.cleaned_data["account_status"]
        profile.can_manage_clients = self.cleaned_data["can_manage_clients"]
        profile.can_manage_documents = self.cleaned_data["can_manage_documents"]
        profile.can_manage_tax_work = self.cleaned_data["can_manage_tax_work"]
        profile.save()
        self.managed_user.is_active = profile.account_status == "ACTIVE"
        self.managed_user.save(update_fields=["is_active"])
        return profile
