from django.contrib import messages
import csv
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import FileResponse, HttpResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from .forms import (
    ClientDocumentForm,
    ClientDocumentReviewForm,
    ClientForm,
    ClientInvoiceForm,
    TaxCaseFileForm,
    TaxCaseForm,
    TaxCaseTaskForm,
    TaxReturnForm,
)
from .models import (
    ActivityLog,
    Client,
    ClientDocument,
    ClientInvoice,
    TaxCase,
    TaxCaseFile,
    TaxCaseTask,
    TaxReturn,
)
from .notifications import notify_client, record_activity


def staff_required(view):
    @login_required(login_url="staff_login")
    def wrapped(request, *args, **kwargs):
        profile = getattr(request.user, "profile", None)
        if not (
            request.user.is_staff
            or (
                profile
                and profile.role in {"STAFF", "ADMIN"}
                and profile.account_status == "ACTIVE"
            )
        ):
            messages.error(request, "Please sign in with a staff account to access the management system.")
            return redirect("client_portal")
        return view(request, *args, **kwargs)
    return wrapped

@staff_required
def home(request):
    stats = {
        "clients": Client.objects.count(),
        "new": Client.objects.filter(status="New").count(),
        "progress": Client.objects.filter(status="In Progress").count(),
        "completed": Client.objects.filter(status="Completed").count(),
    }
    recent_clients = Client.objects.all().order_by("-created_at")[:5]
    return render(request, "dashboard/index.html", {
        "stats": stats,
        "recent_clients": recent_clients
    })

@staff_required
def clients(request):
    query = request.GET.get("q", "")
    client_list = Client.objects.all().order_by("-created_at")
    if query:
        client_list = client_list.filter(full_name__icontains=query)
    return render(request, "dashboard/clients.html", {
        "clients": client_list,
        "query": query
    })

@staff_required
def add_client(request):
    if request.method == "POST":
        form = ClientForm(request.POST)
        if form.is_valid():
            client = form.save()
            record_activity(
                request.user,
                "Client record created",
                "Client record was added by staff.",
                client=client,
            )
            messages.success(request, "Client has been added successfully.")
            return redirect("clients")
    else:
        form = ClientForm()
    return render(request, "dashboard/client_form.html", {"form": form, "title": "Add New Client"})

@staff_required
def edit_client(request, pk):
    client = get_object_or_404(Client, pk=pk)
    if request.method == "POST":
        form = ClientForm(request.POST, instance=client)
        if form.is_valid():
            form.save()
            record_activity(
                request.user,
                "Client record updated",
                "Client profile information was updated by staff.",
                client=client,
            )
            messages.success(request, "Client information updated successfully.")
            return redirect("clients")
    else:
        form = ClientForm(instance=client)
    return render(request, "dashboard/client_form.html", {
        "form": form, "title": "Edit Client", "client": client
    })

@staff_required
def delete_client(request, pk):
    client = get_object_or_404(Client, pk=pk)
    if request.method == "POST":
        record_activity(
            request.user,
            "Client record deleted",
            f"Client record for {client.full_name} was deleted.",
            client=client,
        )
        client.delete()
        messages.success(request, "Client deleted successfully.")
        return redirect("clients")
    return render(request, "dashboard/client_confirm_delete.html", {"client": client})

@staff_required
def documents(request):
    document_list = ClientDocument.objects.select_related("client")
    if request.method == "POST":
        form = ClientDocumentForm(request.POST, request.FILES)
        if form.is_valid():
            document = form.save()
            record_activity(
                request.user,
                "Document shared",
                f"{document.title} was shared with the client.",
                client=document.client,
                tax_case=document.tax_case,
            )
            notify_client(
                document.client,
                "A document was shared with you",
                f"Our team has shared '{document.title}' in your client portal.",
                tax_case=document.tax_case,
            )
            messages.success(request, "Document uploaded and linked to the client.")
            return redirect("documents")
    else:
        form = ClientDocumentForm()
    return render(request, "dashboard/documents.html", {"documents": document_list, "form": form})


@staff_required
def delete_document(request, pk):
    document = get_object_or_404(ClientDocument, pk=pk)
    if request.method == "POST":
        record_activity(
            request.user,
            "Document deleted",
            f"{document.title} was deleted.",
            client=document.client,
            tax_case=document.tax_case,
        )
        document.file.delete(save=False)
        document.delete()
        messages.success(request, "Document deleted.")
    return redirect("documents")


@login_required(login_url="client_login")
def download_document(request, pk):
    document = get_object_or_404(ClientDocument, pk=pk)
    profile = getattr(request.user, "profile", None)
    is_staff = request.user.is_staff or (profile and profile.role in {"STAFF", "ADMIN"})
    owns_document = (
        document.client.user_id == request.user.pk
        or (
            document.client.user_id is None
            and bool(document.client.email and request.user.email)
            and document.client.email.lower() == request.user.email.lower()
        )
    )
    if not is_staff and not owns_document:
        return HttpResponseForbidden("You are not allowed to access this document.")
    return FileResponse(document.file.open("rb"), as_attachment=False, filename=document.file.name.rsplit("/", 1)[-1])


@staff_required
def review_document(request, pk):
    document = get_object_or_404(ClientDocument.objects.select_related("client", "tax_case"), pk=pk)
    if request.method == "POST":
        form = ClientDocumentReviewForm(request.POST, instance=document)
        if form.is_valid():
            reviewed_document = form.save(commit=False)
            reviewed_document.reviewed_by = request.user
            reviewed_document.reviewed_at = timezone.now()
            reviewed_document.save()
            detail = reviewed_document.reviewer_notes or "Please check your document status in the portal."
            if reviewed_document.missing_or_corrected_request:
                detail = f"{detail}\nAction requested: {reviewed_document.missing_or_corrected_request}".strip()
            record_activity(
                request.user,
                f"Document {reviewed_document.review_status.lower()}",
                f"{reviewed_document.title}: {detail}",
                client=reviewed_document.client,
                tax_case=reviewed_document.tax_case,
            )
            notify_client(
                reviewed_document.client,
                f"Document {reviewed_document.review_status.lower()}",
                f"Your document '{reviewed_document.title}' has been reviewed. {detail}",
                tax_case=reviewed_document.tax_case,
            )
            messages.success(request, "Document review saved and the client was notified.")
            return redirect("documents")
    else:
        form = ClientDocumentReviewForm(instance=document)
    return render(request, "dashboard/document_review_form.html", {
        "document": document,
        "form": form,
    })


@staff_required
def tax_cases(request):
    if request.method == "POST":
        form = TaxCaseForm(request.POST)
        form.fields["assigned_to"].queryset = User.objects.filter(
            Q(is_staff=True) | Q(profile__role="STAFF", profile__account_status="ACTIVE")
        ).distinct()
        if form.is_valid():
            tax_case = form.save()
            record_activity(
                request.user,
                "Case created",
                f"{tax_case.service_type} case created for {tax_case.client.full_name}.",
                client=tax_case.client,
                tax_case=tax_case,
            )
            notify_client(
                tax_case.client,
                "Service case created",
                f"A {tax_case.service_type} case has been opened. Current status: {tax_case.status}.",
                tax_case=tax_case,
            )
            messages.success(request, "Service case created.")
            return redirect("edit_tax_case", pk=tax_case.pk)
    else:
        form = TaxCaseForm()
        form.fields["assigned_to"].queryset = User.objects.filter(
            Q(is_staff=True) | Q(profile__role="STAFF", profile__account_status="ACTIVE")
        ).distinct()
    return render(request, "dashboard/tax_cases.html", {
        "tax_cases": TaxCase.objects.select_related("client", "assigned_to").prefetch_related("tasks"),
        "form": form,
    })


@staff_required
def edit_tax_case(request, pk):
    tax_case = get_object_or_404(TaxCase.objects.select_related("client", "assigned_to"), pk=pk)
    original = {
        "status": tax_case.status,
        "assigned_to_id": tax_case.assigned_to_id,
        "payment_verified": tax_case.payment_verified,
    }
    if request.method == "POST":
        form = TaxCaseForm(request.POST, instance=tax_case)
        form.fields["assigned_to"].queryset = User.objects.filter(
            Q(is_staff=True) | Q(profile__role="STAFF", profile__account_status="ACTIVE")
        ).distinct()
        if form.is_valid():
            tax_case = form.save(commit=False)
            if tax_case.status == "Completed" and not tax_case.completed_date:
                tax_case.completed_date = timezone.localdate()
            elif tax_case.status != "Completed":
                tax_case.completed_date = None
            tax_case.save()
            changes = []
            if original["status"] != tax_case.status:
                changes.append(f"Status changed to {tax_case.status}.")
            if original["assigned_to_id"] != tax_case.assigned_to_id:
                assignee = tax_case.assigned_to.get_full_name() or tax_case.assigned_to.username if tax_case.assigned_to else "Unassigned"
                changes.append(f"Assigned adviser: {assignee}.")
            if original["payment_verified"] != tax_case.payment_verified:
                record_activity(
                    request.user,
                    "Payment verification updated",
                    f"Payment verification set to {'confirmed' if tax_case.payment_verified else 'not confirmed'} for {tax_case.service_type}.",
                    client=tax_case.client,
                    tax_case=tax_case,
                )
            if changes:
                description = " ".join(changes)
                record_activity(
                    request.user,
                    "Case updated",
                    description,
                    client=tax_case.client,
                    tax_case=tax_case,
                )
                notify_client(
                    tax_case.client,
                    "Case progress updated",
                    f"Your {tax_case.service_type} case was updated. {description}",
                    tax_case=tax_case,
                )
            messages.success(request, "Case changes saved.")
            return redirect("edit_tax_case", pk=tax_case.pk)
    else:
        form = TaxCaseForm(instance=tax_case)
        form.fields["assigned_to"].queryset = User.objects.filter(
            Q(is_staff=True) | Q(profile__role="STAFF", profile__account_status="ACTIVE")
        ).distinct()
    return render(request, "dashboard/tax_case_form.html", {
        "tax_case": tax_case,
        "form": form,
        "task_form": TaxCaseTaskForm(),
        "file_form": TaxCaseFileForm(),
    })


@staff_required
def add_tax_case_task(request, pk):
    tax_case = get_object_or_404(TaxCase, pk=pk)
    if request.method == "POST":
        form = TaxCaseTaskForm(request.POST)
        if form.is_valid():
            task = form.save(commit=False)
            task.case = tax_case
            task.save()
            record_activity(
                request.user,
                "Internal task added",
                f"Task added: {task.title}.",
                client=tax_case.client,
                tax_case=tax_case,
            )
            messages.success(request, "Internal task added.")
        else:
            errors = "; ".join(
                f"{field}: {', '.join(error_list)}"
                for field, error_list in form.errors.items()
            )
            messages.error(request, f"The task could not be saved: {errors}")
    return redirect("edit_tax_case", pk=pk)


@staff_required
def toggle_tax_case_task(request, pk):
    task = get_object_or_404(TaxCaseTask.objects.select_related("case__client"), pk=pk)
    if request.method == "POST":
        task.is_complete = not task.is_complete
        task.save(update_fields=["is_complete"])
        state = "completed" if task.is_complete else "reopened"
        record_activity(
            request.user,
            "Internal task updated",
            f"Task {state}: {task.title}.",
            client=task.case.client,
            tax_case=task.case,
        )
        messages.success(request, f"Task {state}.")
    return redirect("edit_tax_case", pk=task.case_id)


@staff_required
def upload_tax_case_file(request, pk):
    tax_case = get_object_or_404(TaxCase.objects.select_related("client"), pk=pk)
    if request.method == "POST":
        form = TaxCaseFileForm(request.POST, request.FILES)
        if form.is_valid():
            case_file = form.save(commit=False)
            case_file.case = tax_case
            case_file.uploaded_by = request.user
            case_file.save()
            record_activity(
                request.user,
                "Case file shared",
                f"{case_file.title} was uploaded to the case.",
                client=tax_case.client,
                tax_case=tax_case,
            )
            notify_client(
                tax_case.client,
                "A case file is ready",
                f"Our team has shared '{case_file.title}' for your {tax_case.service_type} case.",
                tax_case=tax_case,
            )
            messages.success(request, "Case file uploaded and the client was notified.")
        else:
            errors = "; ".join(
                f"{field}: {', '.join(error_list)}"
                for field, error_list in form.errors.items()
            )
            messages.error(request, f"The case file could not be uploaded: {errors}")
    return redirect("edit_tax_case", pk=pk)


@login_required(login_url="client_login")
def download_tax_case_file(request, pk):
    case_file = get_object_or_404(TaxCaseFile.objects.select_related("case__client"), pk=pk)
    profile = getattr(request.user, "profile", None)
    is_staff = request.user.is_staff or (profile and profile.role in {"STAFF", "ADMIN"})
    email_matches_unlinked_client = (
        case_file.case.client.user_id is None
        and bool(case_file.case.client.email and request.user.email)
        and case_file.case.client.email.lower() == request.user.email.lower()
    )
    if not is_staff and case_file.case.client.user_id != request.user.pk and not email_matches_unlinked_client:
        return HttpResponseForbidden("You are not allowed to access this case file.")
    return FileResponse(
        case_file.file.open("rb"),
        as_attachment=False,
        filename=case_file.file.name.rsplit("/", 1)[-1],
    )


@staff_required
def activity_history(request):
    query = request.GET.get("q", "").strip()
    activities = ActivityLog.objects.select_related("user", "client", "tax_case")
    if query:
        activities = activities.filter(
            Q(action__icontains=query)
            | Q(description__icontains=query)
            | Q(client__full_name__icontains=query)
            | Q(user__username__icontains=query)
        )
    return render(request, "dashboard/activity_history.html", {
        "activities": activities[:200],
        "query": query,
    })

@staff_required
def tax_returns(request):
    returns = TaxReturn.objects.select_related("client")
    if request.method == "POST":
        form = TaxReturnForm(request.POST)
        if form.is_valid():
            tax_return = form.save()
            record_activity(
                request.user,
                "Tax filing record created",
                f"{tax_return.tax_type} filing record for {tax_return.tax_year} was created.",
                client=tax_return.client,
            )
            notify_client(
                tax_return.client,
                "Tax filing record added",
                f"Our team added a {tax_return.tax_type} filing record for {tax_return.tax_year}. Current status: {tax_return.status}.",
            )
            messages.success(request, "Tax return saved successfully.")
            return redirect("tax_returns")
    else:
        form = TaxReturnForm()
    return render(request, "dashboard/tax_returns.html", {"tax_returns": returns, "form": form})


@staff_required
def invoices(request):
    if request.method == "POST":
        form = ClientInvoiceForm(request.POST)
        if form.is_valid():
            invoice = form.save(commit=False)
            invoice.created_by = request.user
            invoice.save()
            record_activity(
                request.user,
                "Invoice created",
                f"{invoice.invoice_number} for PKR {invoice.amount} was created.",
                client=invoice.client,
            )
            notify_client(
                invoice.client,
                "Invoice received",
                f"Invoice {invoice.invoice_number} for PKR {invoice.amount} is available in your portal. The online payment popup is a demo; arrange payment with the office.",
            )
            messages.success(request, f"Invoice {invoice.invoice_number} created.")
            return redirect("invoices")
    else:
        form = ClientInvoiceForm()
    return render(request, "dashboard/invoices.html", {
        "form": form,
        "invoices": ClientInvoice.objects.select_related("client").all(),
    })


@staff_required
def update_invoice_status(request, pk):
    if request.method != "POST":
        return redirect("invoices")
    invoice = get_object_or_404(ClientInvoice, pk=pk)
    status = request.POST.get("status")
    if status not in dict(ClientInvoice.STATUS_CHOICES):
        messages.error(request, "Choose a valid invoice status.")
    else:
        invoice.status = status
        invoice.save(update_fields=["status"])
        record_activity(
            request.user,
            "Invoice status updated",
            f"{invoice.invoice_number} was marked {status.lower()} by staff.",
            client=invoice.client,
        )
        notify_client(
            invoice.client,
            "Invoice status updated",
            f"Our office marked invoice {invoice.invoice_number} as {status.lower()}.",
        )
        messages.success(request, f"{invoice.invoice_number} marked {status.lower()}.")
    return redirect("invoices")


@staff_required
def edit_tax_return(request, pk):
    tax_return = get_object_or_404(TaxReturn, pk=pk)
    if request.method == "POST":
        form = TaxReturnForm(request.POST, instance=tax_return)
        if form.is_valid():
            previous_status = tax_return.status
            tax_return = form.save()
            record_activity(
                request.user,
                "Tax filing record updated",
                f"{tax_return.tax_type} filing record for {tax_return.tax_year} updated to {tax_return.status}.",
                client=tax_return.client,
            )
            if previous_status != tax_return.status:
                notify_client(
                    tax_return.client,
                    "Tax filing progress updated",
                    f"Your {tax_return.tax_type} filing for {tax_return.tax_year} is now {tax_return.status}.",
                )
            messages.success(request, "Tax return updated.")
            return redirect("tax_returns")
    else:
        form = TaxReturnForm(instance=tax_return)
    return render(request, "dashboard/tax_return_form.html", {"form": form, "tax_return": tax_return})

@staff_required
def reports(request):
    client_statuses = {status: Client.objects.filter(status=status).count() for status, _ in Client.STATUS_CHOICES}
    return_statuses = {status: TaxReturn.objects.filter(status=status).count() for status, _ in TaxReturn.STATUS_CHOICES}
    return render(request, "dashboard/reports.html", {
        "total_clients": Client.objects.count(), "total_documents": ClientDocument.objects.count(),
        "total_returns": TaxReturn.objects.count(), "client_statuses": client_statuses,
        "return_statuses": return_statuses,
    })


@staff_required
def export_clients(request):
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="kla-client-report.csv"'
    writer = csv.writer(response)
    writer.writerow(["Client", "CNIC", "Phone", "Email", "NTN", "Status", "Created"])
    for client in Client.objects.all().order_by("full_name"):
        writer.writerow([client.full_name, client.cnic, client.phone, client.email, client.ntn, client.status, client.created_at.strftime("%Y-%m-%d")])
    return response
