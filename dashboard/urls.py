from django.urls import path
from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("clients/", views.clients, name="clients"),
    path("clients/add/", views.add_client, name="add_client"),
    path("clients/<int:pk>/edit/", views.edit_client, name="edit_client"),
    path("clients/<int:pk>/delete/", views.delete_client, name="delete_client"),
    path("documents/", views.documents, name="documents"),
    path("documents/<int:pk>/delete/", views.delete_document, name="delete_document"),
    path("documents/<int:pk>/download/", views.download_document, name="download_document"),
    path("documents/<int:pk>/review/", views.review_document, name="review_document"),
    path("cases/", views.tax_cases, name="tax_cases"),
    path("cases/<int:pk>/", views.edit_tax_case, name="edit_tax_case"),
    path("cases/<int:pk>/tasks/add/", views.add_tax_case_task, name="add_tax_case_task"),
    path("case-tasks/<int:pk>/toggle/", views.toggle_tax_case_task, name="toggle_tax_case_task"),
    path("cases/<int:pk>/files/upload/", views.upload_tax_case_file, name="upload_tax_case_file"),
    path("case-files/<int:pk>/download/", views.download_tax_case_file, name="download_tax_case_file"),
    path("activity/", views.activity_history, name="activity_history"),
    path("tax-returns/", views.tax_returns, name="tax_returns"),
    path("tax-returns/<int:pk>/edit/", views.edit_tax_return, name="edit_tax_return"),
    path("invoices/", views.invoices, name="invoices"),
    path("invoices/<int:pk>/status/", views.update_invoice_status, name="update_invoice_status"),
    path("reports/", views.reports, name="reports"),
    path("reports/clients.csv", views.export_clients, name="export_clients"),
]
