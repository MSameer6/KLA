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
    path("tax-returns/", views.tax_returns, name="tax_returns"),
    path("tax-returns/<int:pk>/edit/", views.edit_tax_return, name="edit_tax_return"),
    path("reports/", views.reports, name="reports"),
    path("reports/clients.csv", views.export_clients, name="export_clients"),
]
