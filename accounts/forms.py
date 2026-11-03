from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import AuthenticationForm
from dashboard.models import Client

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
    cnic = forms.CharField(max_length=20, label="CNIC", widget=forms.TextInput(attrs={"placeholder": "XXXXX-XXXXXXX-X"}))
    phone = forms.CharField(max_length=20, label="Phone", widget=forms.TextInput(attrs={"placeholder": "03XXXXXXXXX"}))
    address = forms.CharField(required=False, label="Address", widget=forms.Textarea(attrs={"rows": 2, "placeholder": "Address (optional)"}))
    needs_ntn_return = forms.BooleanField(required=False, label="NTN & Return Filing")
    needs_sales_tax = forms.BooleanField(required=False, label="Sales Tax")
    needs_income_tax = forms.BooleanField(required=False, label="Income Tax")

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
        return email


class ClientDetailsForm(forms.Form):
    cnic = forms.CharField(max_length=20, label="CNIC", widget=forms.TextInput(attrs={"placeholder": "XXXXX-XXXXXXX-X"}))
    phone = forms.CharField(max_length=20, label="Phone", widget=forms.TextInput(attrs={"placeholder": "03XXXXXXXXX"}))
    address = forms.CharField(required=False, label="Address", widget=forms.Textarea(attrs={"rows": 2, "placeholder": "Address (optional)"}))
    needs_ntn_return = forms.BooleanField(required=False, label="NTN & Return Filing")
    needs_sales_tax = forms.BooleanField(required=False, label="Sales Tax")
    needs_income_tax = forms.BooleanField(required=False, label="Income Tax")

    def clean_cnic(self):
        cnic = self.cleaned_data["cnic"].strip()
        if Client.objects.filter(cnic=cnic).exists():
            raise forms.ValidationError("This CNIC is already registered. Please contact the office.")
        return cnic

class StaffRegisterForm(BaseRegisterForm):
    pass

class LoginForm(AuthenticationForm):
    username = forms.CharField(widget=forms.TextInput(attrs={"placeholder": "Username"}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={"placeholder": "Password"}))
