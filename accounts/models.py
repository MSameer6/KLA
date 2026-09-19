from django.db import models
from django.contrib.auth.models import User

class Profile(models.Model):
    ROLE_CHOICES = (
        ("CLIENT", "Client"),
        ("STAFF", "Staff"),
        ("ADMIN", "Administrator"),
    )
    ACCOUNT_STATUS_CHOICES = (
        ("ACTIVE", "Active"),
        ("PENDING", "Pending approval"),
        ("SUSPENDED", "Suspended"),
    )
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default="CLIENT")
    account_status = models.CharField(max_length=12, choices=ACCOUNT_STATUS_CHOICES, default="ACTIVE")
    can_manage_clients = models.BooleanField(default=True)
    can_manage_documents = models.BooleanField(default=True)
    can_manage_tax_work = models.BooleanField(default=True)

    @property
    def is_active_account(self):
        return self.account_status == "ACTIVE" and self.user.is_active

    def __str__(self):
        return f"{self.user.username} - {self.role}"
