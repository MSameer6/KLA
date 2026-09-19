from django.contrib import messages
import csv
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.models import Count, Q
from django.http import FileResponse, HttpResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from accounts.forms import AccountManagementForm, StaffCreateForm
from accounts.models import Profile
from .forms import ClientDocumentForm, ClientForm, DocumentReviewForm, ServiceConfigurationForm, TaxCaseForm, TaxCaseTaskForm, TaxReturnForm
from .models import ActivityLog, Client, ClientDocument, Service, TaxCase, TaxCaseTask, TaxReturn


def staff_required(view):
    @login_required(login_url="staff_login")
    def wrapped(request, *args, **kwargs):
        profile = request.user.profile
        if not (request.user.is_staff or profile.role in ("STAFF", "ADMIN")) or not profile.is_active_account:
            messages.error(request, "Please sign in with a staff account to access the management system.")
            return redirect("client_portal")
        return view(request, *args, **kwargs)
    return wrapped

def admin_required(view):
    @staff_required
    def wrapped(request, *args, **kwargs):
        if not (request.user.is_superuser or request.user.profile.role == "ADMIN"):
            messages.error(request, "Administrator permission is required for that action.")
            return redirect("home")
        return view(request, *args, **kwargs)
    return wrapped

def staff_permission(permission_name):
    def decorator(view):
        @staff_required
        def wrapped(request, *args, **kwargs):
            profile = request.user.profile
            if not (request.user.is_superuser or profile.role == "ADMIN" or getattr(profile, permission_name)):
                messages.error(request, "Your staff account is not authorized for that action.")
                return redirect("home")
            return view(request, *args, **kwargs)
        return wrapped
    return decorator

@staff_required
def home(request):
    stats = {
        "clients": Client.objects.count(),
        "new": Client.objects.filter(status="New").count(),
        "progress": Client.objects.filter(status="In Progress").count(),
        "completed": Client.objects.filter(status="Completed").count(),
        "pending_reviews": ClientDocument.objects.filter(review_status="Pending").count(),
        "active_cases": TaxCase.objects.exclude(status="Completed").count(),
    }
    recent_clients = Client.objects.all().order_by("-created_at")[:5]
    return render(request, "dashboard/index.html", {
        "stats": stats,
        "recent_clients": recent_clients
    })

@staff_permission("can_manage_clients")
def clients(request):
    query = request.GET.get("q", "").strip()
    status = request.GET.get("status", "")
    service = request.GET.get("service", "")
    case_status = request.GET.get("case_status", "")
    client_list = Client.objects.all().order_by("-created_at")
    if query:
        client_list = client_list.filter(Q(full_name__icontains=query) | Q(cnic__icontains=query) | Q(phone__icontains=query) | Q(email__icontains=query) | Q(ntn__icontains=query))
    if status:
        client_list = client_list.filter(status=status)
    if service:
        client_list = client_list.filter(tax_cases__service_type=service)
    if case_status:
        client_list = client_list.filter(tax_cases__status=case_status)
    client_list = client_list.distinct()
    return render(request, "dashboard/clients.html", {
        "clients": client_list,
        "query": query, "selected_status": status, "selected_service": service,
        "selected_case_status": case_status, "statuses": Client.STATUS_CHOICES,
        "service_types": TaxCase.SERVICE_TYPES, "case_statuses": TaxCase.STATUS_CHOICES,
    })


@staff_permission("can_manage_clients")
def client_detail(request, pk):
    client = get_object_or_404(Client.objects.select_related("user"), pk=pk)
    documents = client.documents.select_related("reviewed_by")
    tax_cases = client.tax_cases.select_related("assigned_to").prefetch_related("tasks")
    activity_filter = Q(client=client) | Q(description__icontains=client.full_name)
    if client.user_id:
        activity_filter |= Q(user=client.user)
    activities = ActivityLog.objects.filter(activity_filter).select_related("user")[:20]
    return render(request, "dashboard/client_detail.html", {
        "client": client, "documents": documents, "tax_cases": tax_cases, "activities": activities,
    })

@staff_permission("can_manage_clients")
def add_client(request):
    if request.method == "POST":
        form = ClientForm(request.POST)
        if form.is_valid():
            client = form.save()
            ActivityLog.objects.create(user=request.user, client=client, action="Client created", description=f"Created client profile for {client.full_name}.")
            messages.success(request, "Client has been added successfully.")
            return redirect("clients")
    else:
        form = ClientForm()
    return render(request, "dashboard/client_form.html", {"form": form, "title": "Add New Client"})

@staff_permission("can_manage_clients")
def edit_client(request, pk):
    client = get_object_or_404(Client, pk=pk)
    if request.method == "POST":
        form = ClientForm(request.POST, instance=client)
        if form.is_valid():
            form.save()
            ActivityLog.objects.create(user=request.user, client=client, action="Client profile updated", description=f"Updated client profile for {client.full_name}.")
            messages.success(request, "Client information updated successfully.")
            return redirect("clients")
    else:
        form = ClientForm(instance=client)
    return render(request, "dashboard/client_form.html", {
        "form": form, "title": "Edit Client", "client": client
    })

@staff_permission("can_manage_clients")
def delete_client(request, pk):
    client = get_object_or_404(Client, pk=pk)
    if request.method == "POST":
        client.delete()
        messages.success(request, "Client deleted successfully.")
        return redirect("clients")
    return render(request, "dashboard/client_confirm_delete.html", {"client": client})

@staff_permission("can_manage_documents")
def documents(request):
    document_list = ClientDocument.objects.select_related("client")
    if request.method == "POST":
        form = ClientDocumentForm(request.POST, request.FILES)
        if form.is_valid():
            document = form.save()
            ActivityLog.objects.create(user=request.user, client=document.client, action="Document uploaded", description=f"Uploaded {document.title} for {document.client.full_name}.")
            messages.success(request, "Document uploaded and linked to the client.")
            return redirect("documents")
    else:
        form = ClientDocumentForm()
    return render(request, "dashboard/documents.html", {"documents": document_list, "form": form})


@staff_permission("can_manage_documents")
def review_document(request, pk):
    document = get_object_or_404(ClientDocument, pk=pk)
    if request.method == "POST":
        form = DocumentReviewForm(request.POST, instance=document)
        if form.is_valid():
            reviewed = form.save(commit=False)
            reviewed.reviewed_by = request.user
            reviewed.reviewed_at = timezone.now()
            reviewed.save()
            ActivityLog.objects.create(user=request.user, client=document.client, action="Document reviewed", description=f"{document.title} for {document.client.full_name} marked {document.review_status}.")
            messages.success(request, "Document review saved and made visible to the client.")
            return redirect("documents")
    else:
        form = DocumentReviewForm(instance=document)
    return render(request, "dashboard/document_review_form.html", {"form": form, "document": document})


@staff_permission("can_manage_documents")
def delete_document(request, pk):
    document = get_object_or_404(ClientDocument, pk=pk)
    if request.method == "POST":
        document.file.delete(save=False)
        document.delete()
        messages.success(request, "Document deleted.")
    return redirect("documents")


@login_required(login_url="client_login")
def download_document(request, pk):
    document = get_object_or_404(ClientDocument, pk=pk)
    is_staff = request.user.is_staff or getattr(request.user.profile, "role", "CLIENT") == "STAFF"
    if not is_staff:
        linked_user_id = document.client.user_id
        legacy_email_match = linked_user_id is None and bool(request.user.email) and document.client.email.lower() == request.user.email.lower()
        if linked_user_id != request.user.id and not legacy_email_match:
            return HttpResponseForbidden("You are not allowed to access this document.")
    return FileResponse(document.file.open("rb"), as_attachment=False, filename=document.file.name.rsplit("/", 1)[-1])

@staff_permission("can_manage_tax_work")
def tax_cases(request):
    cases = TaxCase.objects.select_related("client", "assigned_to").prefetch_related("tasks")
    if request.method == "POST":
        form = TaxCaseForm(request.POST)
        if form.is_valid():
            tax_case = form.save()
            ActivityLog.objects.create(user=request.user, client=tax_case.client, tax_case=tax_case, action="Tax case created", description=f"Created {tax_case.service_type} case for {tax_case.client.full_name}.")
            messages.success(request, "Tax case created successfully.")
            return redirect("tax_cases")
    else:
        form = TaxCaseForm()
    return render(request, "dashboard/tax_cases.html", {"tax_cases": cases, "form": form})


@staff_permission("can_manage_tax_work")
def edit_tax_case(request, pk):
    tax_case = get_object_or_404(TaxCase, pk=pk)
    if request.method == "POST":
        previous_status, previous_assignee = tax_case.status, tax_case.assigned_to
        form = TaxCaseForm(request.POST, instance=tax_case)
        if form.is_valid():
            form.save()
            ActivityLog.objects.create(user=request.user, client=tax_case.client, tax_case=tax_case, action="Tax case updated", description=f"Updated {tax_case.service_type} case for {tax_case.client.full_name}.")
            if previous_status != tax_case.status:
                ActivityLog.objects.create(user=request.user, client=tax_case.client, tax_case=tax_case, action="Case status changed", description=f"{tax_case.service_type} case status changed from {previous_status} to {tax_case.status}.")
            if previous_assignee != tax_case.assigned_to:
                assigned_name = tax_case.assigned_to.get_full_name() or tax_case.assigned_to.username if tax_case.assigned_to else "Unassigned"
                ActivityLog.objects.create(user=request.user, client=tax_case.client, tax_case=tax_case, action="Case assignment changed", description=f"{tax_case.service_type} case assigned to {assigned_name}.")
            messages.success(request, "Tax case updated.")
            return redirect("edit_tax_case", pk=tax_case.pk)
    else:
        form = TaxCaseForm(instance=tax_case)
    return render(request, "dashboard/tax_case_form.html", {"form": form, "tax_case": tax_case, "task_form": TaxCaseTaskForm()})


@staff_permission("can_manage_tax_work")
def add_tax_case_task(request, pk):
    tax_case = get_object_or_404(TaxCase, pk=pk)
    if request.method == "POST":
        form = TaxCaseTaskForm(request.POST)
        if form.is_valid():
            task = form.save(commit=False)
            task.case = tax_case
            task.save()
            ActivityLog.objects.create(user=request.user, client=tax_case.client, tax_case=tax_case, action="Case task added", description=f"Added task '{task.title}' to {tax_case.service_type} case for {tax_case.client.full_name}.")
            messages.success(request, "Internal task added.")
    return redirect("edit_tax_case", pk=tax_case.pk)


@staff_permission("can_manage_tax_work")
def toggle_tax_case_task(request, pk):
    task = get_object_or_404(TaxCaseTask, pk=pk)
    if request.method == "POST":
        task.is_complete = not task.is_complete
        task.save(update_fields=["is_complete"])
        ActivityLog.objects.create(user=request.user, client=task.case.client, tax_case=task.case, action="Case task updated", description=f"Marked task '{task.title}' {'complete' if task.is_complete else 'open'} for {task.case.client.full_name}.")
    return redirect("edit_tax_case", pk=task.case_id)

@staff_permission("can_manage_clients")
def reports(request):
    date_from = request.GET.get("date_from", "")
    date_to = request.GET.get("date_to", "")
    case_list = TaxCase.objects.all()
    if date_from:
        case_list = case_list.filter(opened_date__gte=date_from)
    if date_to:
        case_list = case_list.filter(opened_date__lte=date_to)
    client_statuses = {status: Client.objects.filter(status=status).count() for status, _ in Client.STATUS_CHOICES}
    case_statuses = {status: case_list.filter(status=status).count() for status, _ in TaxCase.STATUS_CHOICES}
    service_groups = case_list.values("service_type").annotate(count=Count("id")).order_by("service_type")
    return render(request, "dashboard/reports.html", {
        "total_clients": Client.objects.count(), "total_documents": ClientDocument.objects.count(),
        "total_cases": case_list.count(), "active_cases": case_list.exclude(status="Completed").count(),
        "completed_cases": case_list.filter(status="Completed").count(),
        "pending_cases": case_list.filter(status="Information Pending").count(),
        "client_statuses": client_statuses, "case_statuses": case_statuses,
        "service_groups": service_groups, "date_from": date_from, "date_to": date_to,
    })


@staff_permission("can_manage_clients")
def activity_history(request):
    query = request.GET.get("q", "").strip()
    logs = ActivityLog.objects.select_related("user", "client", "tax_case")
    if query:
        logs = logs.filter(Q(action__icontains=query) | Q(description__icontains=query) | Q(client__full_name__icontains=query) | Q(user__username__icontains=query))
    return render(request, "dashboard/activity_history.html", {"activities": logs[:250], "query": query})


@staff_permission("can_manage_clients")
def export_clients(request):
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="kla-client-report.csv"'
    writer = csv.writer(response)
    writer.writerow(["Client", "CNIC", "Phone", "Email", "NTN", "Status", "Created"])
    for client in Client.objects.all().order_by("full_name"):
        writer.writerow([client.full_name, client.cnic, client.phone, client.email, client.ntn, client.status, client.created_at.strftime("%Y-%m-%d")])
    return response

@admin_required
def administration(request):
    users = User.objects.select_related("profile").order_by("username")
    return render(request, "dashboard/administration.html", {"users": users, "activities": ActivityLog.objects.select_related("user")[:20]})

@admin_required
def create_staff(request):
    if request.method == "POST":
        form = StaffCreateForm(request.POST)
        if form.is_valid():
            user = form.save()
            ActivityLog.objects.create(user=request.user, action="Staff account created", description=f"Administrator created staff account for {user.username}.")
            messages.success(request, "Staff account created. Its approval status and permissions have been saved.")
            return redirect("administration")
    else:
        form = StaffCreateForm()
    return render(request, "dashboard/staff_account_form.html", {"form": form, "title": "Create Staff Account"})

@admin_required
def manage_account(request, pk):
    managed_user = get_object_or_404(User.objects.select_related("profile"), pk=pk)
    if request.method == "POST":
        form = AccountManagementForm(request.POST, user=managed_user)
        if form.is_valid():
            form.save()
            ActivityLog.objects.create(user=request.user, action="Account access updated", description=f"Administrator updated role, status, or permissions for {managed_user.username}.")
            messages.success(request, "Account role, approval status, and permissions were updated.")
            return redirect("administration")
    else:
        form = AccountManagementForm(user=managed_user)
    return render(request, "dashboard/staff_account_form.html", {"form": form, "title": f"Manage {managed_user.username}", "managed_user": managed_user})

@admin_required
def service_configurations(request):
    services = Service.objects.all()
    return render(request, "dashboard/service_configurations.html", {"services": services})

@admin_required
def edit_service_configuration(request, pk=None):
    service = get_object_or_404(Service, pk=pk) if pk else None
    if request.method == "POST":
        form = ServiceConfigurationForm(request.POST, instance=service)
        if form.is_valid():
            configured_service = form.save()
            ActivityLog.objects.create(user=request.user, action="Service registration rules updated", description=f"Administrator updated registration fields for {configured_service.name}.")
            messages.success(request, "Service registration rules were saved.")
            return redirect("service_configurations")
    else:
        form = ServiceConfigurationForm(instance=service)
    return render(request, "dashboard/staff_account_form.html", {"form": form, "title": "Add Service" if service is None else f"Configure {service.name}"})
