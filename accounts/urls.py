from django.urls import path
from . import views

urlpatterns = [
    path("accounts/login/", views.login_router, name="login"),
    path("client/login/", views.client_login, name="client_login"),
    path("client/register/", views.client_register, name="client_register"),
    path("client/portal/", views.client_portal, name="client_portal"),
    path("client/service-request/", views.client_service_request, name="client_service_request"),
    path("client/documents/", views.client_documents, name="client_documents"),
    path("client/cases/<int:pk>/", views.client_case_detail, name="client_case_detail"),
    path("client/notifications/<int:pk>/read/", views.mark_notification_read, name="mark_notification_read"),
    path("staff/login/", views.staff_login, name="staff_login"),
    path("staff/register/", views.staff_register, name="staff_register"),
    path("logout/", views.user_logout, name="logout"),
]
