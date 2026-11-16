from django.shortcuts import get_object_or_404, render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.db import IntegrityError, transaction
from django.utils.http import url_has_allowed_host_and_scheme
from .forms import ClientRegisterForm, ClientDetailsForm, ClientServiceRequestForm, LoginForm
from dashboard.billing import create_initial_service_invoice
from dashboard.forms import ClientDocumentUploadForm
from dashboard.models import Client, ClientDocument, ClientInvoice, ClientNotification, TaxCase
from dashboard.notifications import notify_client, record_activity


def create_selected_service_cases(client, selected_services, case_details=""):
    case_services = []
    if selected_services["needs_ntn_return"]:
        case_services.extend(["NTN Registration", "Return Filing"])
    if selected_services["needs_sales_tax"]:
        case_services.append("Sales Tax")
    if selected_services["needs_income_tax"]:
        case_services.append("Income Tax")
    created_cases = []
    for service_type in case_services:
        if client.tax_cases.exclude(status="Completed").filter(service_type=service_type).exists():
            continue
        case, created = TaxCase.objects.get_or_create(
            client=client,
            service_type=service_type,
            status="Newly Registered",
            defaults={"notes": case_details},
        )
        if created:
            created_cases.append(case)
    return created_cases


def client_register(request):
    if request.user.is_authenticated:
        return redirect("client_portal")

    if request.method == "POST":
        form = ClientRegisterForm(request.POST, request.FILES)
        if form.is_valid():
            with transaction.atomic():
                user = form.save(commit=False)
                user.set_password(form.cleaned_data["password"])
                try:
                    with transaction.atomic():
                        user.save()
                except IntegrityError:
                    if User.objects.filter(username__iexact=user.username).exists():
                        form.add_error(
                            "username",
                            "This username is already taken. Please choose another one.",
                        )
                        return render(request, "accounts/client_register.html", {"form": form})
                    raise
                user.profile.role = "CLIENT"
                user.profile.save()
                client = Client.objects.filter(email__iexact=user.email).first()
                if client is None:
                    client = Client.objects.create(
                        full_name=user.get_full_name() or user.username,
                        cnic=form.cleaned_data["cnic"],
                        phone=form.cleaned_data["phone"],
                        email=user.email,
                        address=form.cleaned_data["address"],
                        ntn=form.cleaned_data["ntn"],
                        business_details=form.cleaned_data["business_details"],
                        tax_information=form.cleaned_data["tax_information"],
                        user=user,
                        needs_ntn_return=form.cleaned_data["needs_ntn_return"],
                        needs_sales_tax=form.cleaned_data["needs_sales_tax"],
                        needs_income_tax=form.cleaned_data["needs_income_tax"],
                    )
                else:
                    client.user = user
                    client.full_name = user.get_full_name() or user.username
                    client.cnic = form.cleaned_data["cnic"]
                    client.phone = form.cleaned_data["phone"]
                    client.email = user.email
                    client.address = form.cleaned_data["address"]
                    client.needs_ntn_return = form.cleaned_data["needs_ntn_return"]
                    client.needs_sales_tax = form.cleaned_data["needs_sales_tax"]
                    client.needs_income_tax = form.cleaned_data["needs_income_tax"]
                    client.ntn = form.cleaned_data["ntn"]
                    client.business_details = form.cleaned_data["business_details"]
                    client.tax_information = form.cleaned_data["tax_information"]
                    client.save(update_fields=[
                        "user", "full_name", "cnic", "phone", "email", "address",
                        "needs_ntn_return", "needs_sales_tax", "needs_income_tax",
                        "ntn", "business_details", "tax_information",
                    ])

                selected_services = {
                    field_name: form.cleaned_data[field_name]
                    for field_name in ("needs_ntn_return", "needs_sales_tax", "needs_income_tax")
                }
                create_selected_service_cases(client, selected_services, form.cleaned_data["case_details"])
                create_initial_service_invoice(client, selected_services)
                for upload in form.cleaned_data["supporting_files"]:
                    ClientDocument.objects.create(
                        client=client,
                        title=upload.name[:150],
                        document_type="Other",
                        file=upload,
                    )
                record_activity(
                    user,
                    "Client registered",
                    "Client account and initial service requests were created.",
                    client=client,
                )
            login(request, user)
            notify_client(
                client,
                "Registration received",
                "Your service request has been received. Our team will review your details and documents. Work will begin after staff verifies payment separately.",
            )
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
        if user.is_staff or getattr(user.profile, "role", "CLIENT") in {"STAFF", "ADMIN"}:
            messages.error(request, "This is the Client Login. Staff must use Staff Login.")
        else:
            login(request, user)
            next_url = request.POST.get("next") or request.GET.get("next")
            if next_url and url_has_allowed_host_and_scheme(next_url, {request.get_host()}):
                return redirect(next_url)
            return redirect("client_portal")
    return render(request, "accounts/client_login.html", {"form": form})



def staff_register(request):
    messages.info(request, "Staff accounts are created by an administrator. Please contact the office.")
    return redirect("staff_login")

def staff_login(request):
    if request.user.is_authenticated and (
        request.user.is_staff
        or (
            getattr(request.user.profile, "role", "CLIENT") in {"STAFF", "ADMIN"}
            and request.user.profile.account_status == "ACTIVE"
        )
    ):
        return redirect("home")

    form = LoginForm(request, data=request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.get_user()
        profile = getattr(user, "profile", None)
        if user.is_staff or (
            profile
            and profile.role in {"STAFF", "ADMIN"}
            and profile.account_status == "ACTIVE"
        ):
            login(request, user)
            next_url = request.POST.get("next") or request.GET.get("next")
            if next_url and url_has_allowed_host_and_scheme(next_url, {request.get_host()}):
                return redirect(next_url)
            return redirect("home")
        if profile and profile.role in {"STAFF", "ADMIN"}:
            messages.error(request, "Your staff account is not active. Please contact an administrator.")
            return render(request, "accounts/staff_login.html", {"form": form})
        messages.error(request, "This account is not authorized as staff.")
    return render(request, "accounts/staff_login.html", {"form": form})


def user_logout(request):
    logout(request)
    messages.success(request, "You have been logged out successfully.")
    return redirect("website_home")


@login_required(login_url="client_login")
def client_portal(request):
    if request.user.is_staff or getattr(request.user.profile, "role", "CLIENT") in {"STAFF", "ADMIN"}:
        return redirect("home")
    client = get_client_for_user(request.user)
    details_form = None
    if client is None:
        if request.method == "POST":
            details_form = ClientDetailsForm(request.POST)
            if details_form.is_valid():
                data = details_form.cleaned_data
                with transaction.atomic():
                    client = Client.objects.create(
                        full_name=request.user.get_full_name() or request.user.username,
                        cnic=data["cnic"],
                        phone=data["phone"],
                        email=request.user.email,
                        address=data["address"],
                        ntn=data["ntn"],
                        business_details=data["business_details"],
                        tax_information=data["tax_information"],
                        user=request.user,
                        needs_ntn_return=data["needs_ntn_return"],
                        needs_sales_tax=data["needs_sales_tax"],
                        needs_income_tax=data["needs_income_tax"],
                    )
                    selected_services = {
                        field_name: data[field_name]
                        for field_name in ("needs_ntn_return", "needs_sales_tax", "needs_income_tax")
                    }
                    create_selected_service_cases(client, selected_services, data["case_details"])
                    create_initial_service_invoice(client, selected_services)
                    for upload in data["supporting_files"]:
                        ClientDocument.objects.create(
                            client=client,
                            title=upload.name[:150],
                            document_type="Other",
                            file=upload,
                        )
                    record_activity(
                        request.user,
                        "Client record completed",
                        "Client profile, service requests, and supporting files were submitted.",
                        client=client,
                    )
                notify_client(
                    client,
                    "Service request received",
                    "Your profile and selected services have been submitted. Our team will review your request and verify payment separately before work begins.",
                )
                messages.success(request, "Client record created. Your selected services and invoice are now in your portal.")
                return redirect("client_portal")
        else:
            details_form = ClientDetailsForm()
    else:
        create_initial_service_invoice(client, {
            "needs_ntn_return": client.needs_ntn_return,
            "needs_sales_tax": client.needs_sales_tax,
            "needs_income_tax": client.needs_income_tax,
        })
    context = _client_portal_context(
        client,
        details_form=details_form,
        upload_form=ClientDocumentUploadForm(client=client) if client else None,
        service_request_form=_client_service_request_form(client) if client else None,
    )
    return render(request, "accounts/client_portal.html", context)


def _client_service_request_form(client):
    fields = (
        "address",
        "ntn",
        "business_details",
        "tax_information",
        "needs_ntn_return",
        "needs_sales_tax",
        "needs_income_tax",
    )
    return ClientServiceRequestForm(initial={field: getattr(client, field) for field in fields})


def _client_portal_context(client, details_form=None, upload_form=None, service_request_form=None):
    documents = client.documents.select_related("tax_case") if client else ClientDocument.objects.none()
    tax_cases = client.tax_cases.all() if client else TaxCase.objects.none()
    return {
        "client": client,
        "details_form": details_form,
        "upload_form": upload_form,
        "service_request_form": service_request_form,
        "intake_form": service_request_form or details_form,
        "documents": documents,
        "document_count": documents.count(),
        "pending_document_count": documents.filter(review_status="Pending").count(),
        "tax_cases": tax_cases,
        "case_count": tax_cases.count(),
        "notifications": client.notifications.all()[:10] if client else [],
        "unread_notifications": client.notifications.filter(is_read=False).count() if client else 0,
        "tax_returns": client.tax_returns.all()[:5] if client else [],
        "invoices": ClientInvoice.objects.filter(client=client) if client else [],
    }


@login_required(login_url="client_login")
def client_service_request(request):
    if request.user.is_staff or getattr(request.user.profile, "role", "CLIENT") in {"STAFF", "ADMIN"}:
        return redirect("home")
    client = get_client_for_user(request.user)
    if client is None:
        messages.info(request, "Complete your client profile before requesting services.")
        return redirect("client_portal")

    if request.method == "POST":
        form = ClientServiceRequestForm(request.POST, request.FILES)
        if form.is_valid():
            data = form.cleaned_data
            selected_services = {
                field_name: data[field_name]
                for field_name in ("needs_ntn_return", "needs_sales_tax", "needs_income_tax")
            }
            with transaction.atomic():
                for field_name in (
                    "address",
                    "ntn",
                    "business_details",
                    "tax_information",
                    "needs_ntn_return",
                    "needs_sales_tax",
                    "needs_income_tax",
                ):
                    setattr(client, field_name, data[field_name])
                client.save(update_fields=[
                    "address",
                    "ntn",
                    "business_details",
                    "tax_information",
                    "needs_ntn_return",
                    "needs_sales_tax",
                    "needs_income_tax",
                ])
                new_cases = create_selected_service_cases(client, selected_services, data["case_details"])
                create_initial_service_invoice(client, selected_services)
                uploaded_documents = [
                    ClientDocument.objects.create(
                        client=client,
                        title=upload.name[:150],
                        document_type="Other",
                        file=upload,
                    )
                    for upload in data["supporting_files"]
                ]
                record_activity(
                    request.user,
                    "Client profile and service request updated",
                    f"Updated client details; {len(new_cases)} new case(s) and {len(uploaded_documents)} document(s) submitted.",
                    client=client,
                )
            notify_client(
                client,
                "Profile and service request updated",
                "Your profile details and any selected service requests or documents have been received. Our team will review them and verify payment separately before work begins.",
            )
            messages.success(request, "Your profile details, service requests, and documents have been submitted.")
            return redirect("client_portal")
    else:
        return redirect("client_portal")

    return render(request, "accounts/client_portal.html", _client_portal_context(
        client,
        upload_form=ClientDocumentUploadForm(client=client),
        service_request_form=form,
    ))


@login_required(login_url="client_login")
def client_documents(request):
    if request.user.is_staff or getattr(request.user.profile, "role", "CLIENT") in {"STAFF", "ADMIN"}:
        return redirect("home")
    client = get_client_for_user(request.user)
    if client is None:
        messages.info(request, "Complete your client profile before uploading documents.")
        return redirect("client_portal")
    if request.method != "POST":
        return redirect("client_portal")
    form = ClientDocumentUploadForm(client=client, data=request.POST, files=request.FILES)
    if form.is_valid():
        document = form.save(commit=False)
        document.client = client
        document.save()
        record_activity(
            request.user,
            "Client document uploaded",
            f"{document.title} was uploaded for review.",
            client=client,
            tax_case=document.tax_case,
        )
        messages.success(request, "Document uploaded. Our team will review it and notify you of the result.")
        return redirect("client_portal")
    return render(request, "accounts/client_portal.html", _client_portal_context(
        client,
        upload_form=form,
        service_request_form=_client_service_request_form(client),
    ))


@login_required(login_url="client_login")
def client_case_detail(request, pk):
    if request.user.is_staff or getattr(request.user.profile, "role", "CLIENT") in {"STAFF", "ADMIN"}:
        return redirect("home")
    client = get_client_for_user(request.user)
    if client is None:
        return redirect("client_portal")
    tax_case = get_object_or_404(
        TaxCase.objects.select_related("client").prefetch_related("files"),
        pk=pk,
        client=client,
    )
    return render(request, "accounts/client_case_detail.html", {
        "tax_case": tax_case,
        "activities": tax_case.notifications.all()[:30],
    })


@login_required(login_url="client_login")
def mark_notification_read(request, pk):
    if request.method != "POST":
        return redirect("client_portal")
    if request.user.is_staff or getattr(request.user.profile, "role", "CLIENT") in {"STAFF", "ADMIN"}:
        return redirect("home")
    client = get_client_for_user(request.user)
    if client is None:
        return redirect("client_portal")
    notification = get_object_or_404(ClientNotification, pk=pk, client=client)
    notification.is_read = True
    notification.save(update_fields=["is_read"])
    return redirect("client_case_detail", pk=notification.tax_case_id) if notification.tax_case_id else redirect("client_portal")


def get_client_for_user(user):
    return Client.objects.filter(user=user).first() or Client.objects.filter(
        user__isnull=True,
        email__iexact=user.email,
    ).exclude(email="").first()


def login_router(request):
    """Compatibility route for Django's standard protected-page redirect."""
    return redirect("staff_login" if request.GET.get("next", "").startswith("/staff/") else "client_login")
