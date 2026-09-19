from django.urls import path
from . import views

urlpatterns = [
    path("accounts/login/", views.login_router, name="login"),
    path("client/login/", views.client_login, name="client_login"),
    path("client/register/", views.client_register, name="client_register"),
    path("client/portal/", views.client_portal, name="client_portal"),
    path("client/profile/", views.client_profile, name="client_profile"),
    path("client/profile/edit/", views.edit_client_profile, name="edit_client_profile"),
    path("client/documents/", views.client_documents, name="client_documents"),
    path("client/cases/<int:pk>/", views.client_case_detail, name="client_case_detail"),
    path("staff/login/", views.staff_login, name="staff_login"),
    path("staff/register/", views.staff_register, name="staff_register"),
    path("logout/", views.user_logout, name="logout"),
]
