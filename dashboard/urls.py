from django.urls import path
from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("clients/", views.clients, name="clients"),
    path("clients/add/", views.add_client, name="add_client"),
    path("clients/<int:pk>/", views.client_detail, name="client_detail"),
    path("clients/<int:pk>/edit/", views.edit_client, name="edit_client"),
    path("clients/<int:pk>/delete/", views.delete_client, name="delete_client"),
    path("documents/", views.documents, name="documents"),
    path("documents/<int:pk>/delete/", views.delete_document, name="delete_document"),
    path("documents/<int:pk>/download/", views.download_document, name="download_document"),
    path("documents/<int:pk>/review/", views.review_document, name="review_document"),
    path("tax-cases/", views.tax_cases, name="tax_cases"),
    path("tax-cases/<int:pk>/", views.edit_tax_case, name="edit_tax_case"),
    path("tax-cases/<int:pk>/tasks/add/", views.add_tax_case_task, name="add_tax_case_task"),
    path("tax-case-tasks/<int:pk>/toggle/", views.toggle_tax_case_task, name="toggle_tax_case_task"),
    path("reports/", views.reports, name="reports"),
    path("reports/clients.csv", views.export_clients, name="export_clients"),
    path("activity/", views.activity_history, name="activity_history"),
    path("administration/", views.administration, name="administration"),
    path("administration/staff/create/", views.create_staff, name="create_staff"),
    path("administration/users/<int:pk>/", views.manage_account, name="manage_account"),
    path("administration/services/", views.service_configurations, name="service_configurations"),
    path("administration/services/add/", views.edit_service_configuration, name="add_service_configuration"),
    path("administration/services/<int:pk>/", views.edit_service_configuration, name="edit_service_configuration"),
]
