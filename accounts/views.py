from django.shortcuts import get_object_or_404, render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils.http import url_has_allowed_host_and_scheme
from django.db import transaction
from .forms import ClientDocumentUploadForm, ClientProfileForm, ClientRegisterForm, StaffRegisterForm, LoginForm
from .models import Profile
from dashboard.models import Client, ClientDocument, TaxCase
from dashboard.models import ActivityLog


def client_register(request):
    if request.user.is_authenticated:
        return redirect("client_portal")

    if request.method == "POST":
        form = ClientRegisterForm(request.POST, request.FILES)
        if form.is_valid():
            with transaction.atomic():
                user = form.save(commit=False)
                user.set_password(form.cleaned_data["password"])
                user.save()
                user.profile.role = "CLIENT"
                user.profile.save()
                client = Client.objects.create(
                    user=user,
                    full_name=f"{user.first_name} {user.last_name}".strip(),
                    cnic=form.cleaned_data["cnic"], phone=form.cleaned_data["phone"], email=user.email,
                    address=form.cleaned_data["address"], business_details=form.cleaned_data["business_details"],
                    ntn=form.cleaned_data["ntn"], tax_information=form.cleaned_data["tax_information"],
                    requested_services=form.cleaned_data["requested_services"],
                )
                supporting_document = form.cleaned_data.get("supporting_document")
                if supporting_document:
                    ClientDocument.objects.create(
                        client=client,
                        title=supporting_document.name,
                        document_type="Other",
                        file=supporting_document,
                        notes="Submitted during client registration.",
                    )
                ActivityLog.objects.create(user=user, client=client, action="Client registration", description="Client account and linked profile were created.")
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
        if not user.profile.is_active_account:
            messages.error(request, "This account is pending approval or has been suspended.")
            return render(request, "accounts/client_login.html", {"form": form})
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
    messages.error(request, "Staff accounts are created and approved by an administrator.")
    return redirect("staff_login")

def staff_login(request):
    if request.user.is_authenticated and (request.user.is_staff or getattr(request.user.profile, "role", "CLIENT") == "STAFF"):
        return redirect("home")

    form = LoginForm(request, data=request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.get_user()
        if user.is_staff or getattr(user.profile, "role", "CLIENT") in ("STAFF", "ADMIN"):
            if not user.profile.is_active_account:
                messages.error(request, "This staff account is pending approval or has been suspended.")
                return render(request, "accounts/staff_login.html", {"form": form})
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

def client_for_user(user):
    """Resolve only the signed-in client's profile, preserving legacy records."""
    client = Client.objects.filter(user=user).first()
    if client is None and user.email:
        client = Client.objects.filter(email__iexact=user.email, user__isnull=True).first()
    return client


@login_required(login_url="client_login")
def client_portal(request):
    if request.user.is_staff or getattr(request.user.profile, "role", "CLIENT") == "STAFF":
        return redirect("home")
    client = client_for_user(request.user)
    return render(request, "accounts/client_portal.html", {
        "client": client,
        "documents": client.documents.all()[:5] if client else [],
        "tax_cases": client.tax_cases.all()[:5] if client else [],
    })

@login_required(login_url="client_login")
def client_profile(request):
    if request.user.is_staff or getattr(request.user.profile, "role", "CLIENT") == "STAFF":
        return redirect("home")
    client = client_for_user(request.user)
    if client is None:
        messages.error(request, "Your client profile could not be found. Please contact Khan Law Associates.")
        return redirect("client_portal")
    return render(request, "accounts/client_profile_detail.html", {"client": client})


@login_required(login_url="client_login")
def edit_client_profile(request):
    if request.user.is_staff or getattr(request.user.profile, "role", "CLIENT") == "STAFF":
        return redirect("home")
    client = client_for_user(request.user)
    if client is None:
        messages.error(request, "Your client profile could not be found. Please contact Khan Law Associates.")
        return redirect("client_portal")
    if request.method == "POST":
        form = ClientProfileForm(request.POST, instance=client)
        if form.is_valid():
            profile = form.save(commit=False)
            profile.user = request.user
            profile.save()
            if request.user.email != profile.email:
                request.user.email = profile.email
                request.user.save(update_fields=["email"])
            messages.success(request, "Your client profile has been updated.")
            ActivityLog.objects.create(user=request.user, client=profile, action="Client profile updated", description="Client updated personal, business, tax, or service information.")
            return redirect("client_profile")
    else:
        form = ClientProfileForm(instance=client)
    return render(request, "accounts/client_profile.html", {"form": form, "client": client})


@login_required(login_url="client_login")
def client_case_detail(request, pk):
    if request.user.is_staff or getattr(request.user.profile, "role", "CLIENT") == "STAFF":
        return redirect("home")
    client = client_for_user(request.user)
    if client is None:
        messages.error(request, "Your client profile could not be found. Please contact Khan Law Associates.")
        return redirect("client_portal")
    tax_case = get_object_or_404(TaxCase.objects.select_related("assigned_to"), pk=pk, client=client)
    activities = ActivityLog.objects.filter(tax_case=tax_case).select_related("user")[:30]
    return render(request, "accounts/client_case_detail.html", {"client": client, "tax_case": tax_case, "activities": activities})

@login_required(login_url="client_login")
def client_documents(request):
    if request.user.is_staff or getattr(request.user.profile, "role", "CLIENT") == "STAFF":
        return redirect("home")
    client = client_for_user(request.user)
    if client is None:
        messages.error(request, "Your client profile could not be found. Please contact Khan Law Associates.")
        return redirect("client_portal")
    if request.method == "POST":
        form = ClientDocumentUploadForm(request.POST, request.FILES)
        if form.is_valid():
            document = form.save(commit=False)
            document.client = client
            document.save()
            messages.success(request, "Your document has been uploaded and is ready for review.")
            ActivityLog.objects.create(user=request.user, client=client, action="Client document uploaded", description=f"Client uploaded document: {document.title}.")
            return redirect("client_documents")
    else:
        form = ClientDocumentUploadForm()
    return render(request, "accounts/client_documents.html", {"form": form, "client": client, "documents": client.documents.all(), "tax_cases": client.tax_cases.all()})


def login_router(request):
    """Compatibility route for Django's standard protected-page redirect."""
    return redirect("staff_login" if request.GET.get("next", "").startswith("/staff/") else "client_login")
