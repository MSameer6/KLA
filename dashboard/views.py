from django.contrib import messages
import csv
from django.contrib.auth.decorators import login_required
from django.http import FileResponse, HttpResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from .forms import ClientDocumentForm, ClientForm, TaxReturnForm
from .models import Client, ClientDocument, TaxReturn


def staff_required(view):
    @login_required(login_url="staff_login")
    def wrapped(request, *args, **kwargs):
        if not (request.user.is_staff or getattr(request.user.profile, "role", "CLIENT") == "STAFF"):
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
            form.save()
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
            form.save()
            messages.success(request, "Document uploaded and linked to the client.")
            return redirect("documents")
    else:
        form = ClientDocumentForm()
    return render(request, "dashboard/documents.html", {"documents": document_list, "form": form})


@staff_required
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
    if not is_staff and document.client.email.lower() != request.user.email.lower():
        return HttpResponseForbidden("You are not allowed to access this document.")
    return FileResponse(document.file.open("rb"), as_attachment=False, filename=document.file.name.rsplit("/", 1)[-1])

@staff_required
def tax_returns(request):
    returns = TaxReturn.objects.select_related("client")
    if request.method == "POST":
        form = TaxReturnForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Tax return saved successfully.")
            return redirect("tax_returns")
    else:
        form = TaxReturnForm()
    return render(request, "dashboard/tax_returns.html", {"tax_returns": returns, "form": form})


@staff_required
def edit_tax_return(request, pk):
    tax_return = get_object_or_404(TaxReturn, pk=pk)
    if request.method == "POST":
        form = TaxReturnForm(request.POST, instance=tax_return)
        if form.is_valid():
            form.save()
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
