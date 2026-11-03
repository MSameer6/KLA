from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils.http import url_has_allowed_host_and_scheme
from .forms import ClientRegisterForm, ClientDetailsForm, StaffRegisterForm, LoginForm
from .models import Profile
from dashboard.models import Client


def client_register(request):
    if request.user.is_authenticated:
        return redirect("client_portal")

    if request.method == "POST":
        form = ClientRegisterForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.set_password(form.cleaned_data["password"])
            user.save()
            user.profile.role = "CLIENT"
            user.profile.save()
            client = Client.objects.filter(email__iexact=user.email).first()
            if client is None:
                Client.objects.create(
                    full_name=user.get_full_name() or user.username,
                    cnic=form.cleaned_data["cnic"],
                    phone=form.cleaned_data["phone"],
                    email=user.email,
                    address=form.cleaned_data["address"],
                    needs_ntn_return=form.cleaned_data["needs_ntn_return"],
                    needs_sales_tax=form.cleaned_data["needs_sales_tax"],
                    needs_income_tax=form.cleaned_data["needs_income_tax"],
                )
            else:
                client.needs_ntn_return = form.cleaned_data["needs_ntn_return"]
                client.needs_sales_tax = form.cleaned_data["needs_sales_tax"]
                client.needs_income_tax = form.cleaned_data["needs_income_tax"]
                client.save(update_fields=["needs_ntn_return", "needs_sales_tax", "needs_income_tax"])
            login(request, user)
            messages.success(request, "Registration successful. Welcome to your Client Portal!")
            return redirect("client_portal")
    else:
        form = ClientRegisterForm()
    return render(request, "accounts/client_register.html", {"form": form})


def client_login(request):
    if request.user.is_authenticated:
        return redirect("client_portal")

    form = LoginForm(request, data=request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.get_user()
        if user.is_staff or getattr(user.profile, "role", "CLIENT") == "STAFF":
            messages.error(request, "This is the Client Login. Staff must use Staff Login.")
        else:
            login(request, user)
            next_url = request.POST.get("next") or request.GET.get("next")
            if next_url and url_has_allowed_host_and_scheme(next_url, {request.get_host()}):
                return redirect(next_url)
            return redirect("client_portal")
    return render(request, "accounts/client_login.html", {"form": form})



def staff_register(request):
    if request.user.is_authenticated:
        return redirect("home" if (request.user.is_staff or getattr(request.user.profile, "role", "CLIENT") == "STAFF") else "client_portal")
    if request.method == "POST":
        form = StaffRegisterForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.set_password(form.cleaned_data["password"])
            user.save()
            user.profile.role = "STAFF"
            user.profile.save()
            login(request, user)
            messages.success(request, "Staff registration successful. Welcome to the Staff Dashboard!")
            return redirect("home")
    else:
        form = StaffRegisterForm()
    return render(request, "accounts/staff_register.html", {"form": form})

def staff_login(request):
    if request.user.is_authenticated and (request.user.is_staff or getattr(request.user.profile, "role", "CLIENT") == "STAFF"):
        return redirect("home")

    form = LoginForm(request, data=request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.get_user()
        if user.is_staff or getattr(user.profile, "role", "CLIENT") == "STAFF":
            login(request, user)
            next_url = request.POST.get("next") or request.GET.get("next")
            if next_url and url_has_allowed_host_and_scheme(next_url, {request.get_host()}):
                return redirect(next_url)
            return redirect("home")
        messages.error(request, "This account is not authorized as staff.")
    return render(request, "accounts/staff_login.html", {"form": form})


def user_logout(request):
    logout(request)
    messages.success(request, "You have been logged out successfully.")
    return redirect("website_home")


@login_required(login_url="client_login")
def client_portal(request):
    if request.user.is_staff or getattr(request.user.profile, "role", "CLIENT") == "STAFF":
        return redirect("home")
    client = Client.objects.filter(email__iexact=request.user.email).first()
    details_form = None
    if client is None:
        if request.method == "POST":
            details_form = ClientDetailsForm(request.POST)
            if details_form.is_valid():
                data = details_form.cleaned_data
                Client.objects.create(
                    full_name=request.user.get_full_name() or request.user.username,
                    cnic=data["cnic"], phone=data["phone"], email=request.user.email,
                    address=data["address"],
                    needs_ntn_return=data["needs_ntn_return"],
                    needs_sales_tax=data["needs_sales_tax"],
                    needs_income_tax=data["needs_income_tax"],
                )
                messages.success(request, "Aap ka client record ban gaya hai. Staff ab aap ka kaam aage barha sakta hai.")
                return redirect("client_portal")
        else:
            details_form = ClientDetailsForm()
    return render(request, "accounts/client_portal.html", {
        "client": client,
        "details_form": details_form,
        "documents": client.documents.all()[:5] if client else [],
        "tax_returns": client.tax_returns.all()[:5] if client else [],
    })


def login_router(request):
    """Compatibility route for Django's standard protected-page redirect."""
    return redirect("staff_login" if request.GET.get("next", "").startswith("/staff/") else "client_login")
