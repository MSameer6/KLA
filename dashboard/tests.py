from decimal import Decimal
import tempfile

from django.contrib.auth.models import User
from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from .models import (
    ActivityLog,
    Client,
    ClientDocument,
    ClientInvoice,
    ClientNotification,
    TaxCase,
    TaxCaseFile,
    TaxCaseTask,
)


class ClientInvoiceTests(TestCase):
    def setUp(self):
        self.staff = User.objects.create_user(
            username="invoice-staff",
            password="test-password",
            is_staff=True,
        )
        self.client_user = User.objects.create_user(
            username="invoice-client",
            password="test-password",
            email="client@example.com",
        )
        self.client_record = Client.objects.create(
            full_name="Invoice Client",
            cnic="11111-1111111-1",
            phone="03001234567",
            email=self.client_user.email,
        )
        self.invoice = ClientInvoice.objects.create(
            client=self.client_record,
            description="Tax filing service",
            amount=Decimal("12500.00"),
        )

    def test_staff_can_create_invoice_and_mark_it_paid(self):
        self.client.force_login(self.staff)
        response = self.client.post(reverse("invoices"), {
            "client": self.client_record.pk,
            "description": "Consultation",
            "amount": "2500.00",
            "due_date": "",
        })

        self.assertRedirects(response, reverse("invoices"))
        consultation = ClientInvoice.objects.get(description="Consultation")
        self.assertEqual(consultation.created_by, self.staff)

        response = self.client.post(reverse("update_invoice_status", args=[consultation.pk]), {
            "status": "Paid",
        })
        self.assertRedirects(response, reverse("invoices"))
        consultation.refresh_from_db()
        self.assertEqual(consultation.status, "Paid")

    def test_invoice_amount_must_be_positive(self):
        self.client.force_login(self.staff)

        response = self.client.post(reverse("invoices"), {
            "client": self.client_record.pk,
            "description": "Invalid amount",
            "amount": "0",
            "due_date": "",
        })

        self.assertEqual(response.status_code, 200)
        self.assertFalse(ClientInvoice.objects.filter(description="Invalid amount").exists())

    def test_client_portal_shows_client_workspace_and_current_case_status(self):
        case = TaxCase.objects.create(
            client=self.client_record,
            service_type="Income Tax",
            status="Filing in Progress",
        )
        notification = ClientNotification.objects.create(
            client=self.client_record,
            tax_case=case,
            title="Return filing started",
            message="Our team has started preparing your return.",
        )
        self.client.force_login(self.client_user)

        response = self.client.get(reverse("client_portal"))

        self.assertContains(response, "Documents &amp; cases")
        self.assertContains(response, "Client details")
        self.assertContains(response, "My documents")
        self.assertContains(response, "My tax cases")
        self.assertContains(response, "Filing in Progress")
        self.assertContains(response, "Return filing started")
        self.assertContains(response, notification.message)
        self.assertNotContains(response, "Tell us how we can help")
        self.assertNotContains(response, '<details class="document-upload-panel service-request-panel" id="profile-request" open')
        self.assertNotContains(response, self.invoice.invoice_number)
        self.assertNotContains(response, "Choose how to pay")
        self.invoice.refresh_from_db()
        self.assertEqual(self.invoice.status, "Pending")

    def test_existing_client_gets_initial_invoice_for_selected_services(self):
        self.client_record.needs_ntn_return = True
        self.client_record.needs_income_tax = True
        self.client_record.save(update_fields=["needs_ntn_return", "needs_income_tax"])
        self.client.force_login(self.client_user)

        response = self.client.get(reverse("client_portal"))

        self.assertNotContains(response, "Pay online")
        generated_invoice = ClientInvoice.objects.get(
            client=self.client_record,
            description__startswith="Initial service fees:",
        )
        self.assertEqual(generated_invoice.amount, Decimal("25000.00"))

    def test_client_does_not_see_another_clients_invoice(self):
        other_client = Client.objects.create(
            full_name="Another Client",
            cnic="22222-2222222-2",
            phone="03007654321",
            email="another@example.com",
        )
        other_invoice = ClientInvoice.objects.create(
            client=other_client,
            description="Private service",
            amount=Decimal("900.00"),
        )
        self.client.force_login(self.client_user)

        response = self.client.get(reverse("client_portal"))

        self.assertNotContains(response, self.invoice.invoice_number)
        self.assertNotContains(response, other_invoice.invoice_number)
        self.assertNotContains(response, "Private service")

    def test_staff_dashboard_pages_load_for_staff(self):
        self.client.force_login(self.staff)
        route_names = [
            "home",
            "clients",
            "add_client",
            "documents",
            "tax_cases",
            "activity_history",
            "tax_returns",
            "invoices",
            "reports",
            "export_clients",
        ]

        for route_name in route_names:
            with self.subTest(route=route_name):
                response = self.client.get(reverse(route_name))
                self.assertEqual(response.status_code, 200)

    def test_client_is_redirected_away_from_staff_invoice_management(self):
        self.client.force_login(self.client_user)

        response = self.client.get(reverse("invoices"))

        self.assertRedirects(response, reverse("client_portal"))


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class ClientWorkflowTests(TestCase):
    def setUp(self):
        self.media_dir = tempfile.TemporaryDirectory()
        self.settings_override = override_settings(MEDIA_ROOT=self.media_dir.name)
        self.settings_override.enable()
        self.addCleanup(self.settings_override.disable)
        self.addCleanup(self.media_dir.cleanup)

        self.staff = User.objects.create_user(
            username="workflow-staff",
            password="staff-password",
            email="staff@example.com",
            is_staff=True,
        )
        self.client_user = User.objects.create_user(
            username="workflow-client",
            password="client-password",
            email="workflow@example.com",
        )
        self.client_record = Client.objects.create(
            user=self.client_user,
            full_name="Workflow Client",
            cnic="33333-3333333-3",
            phone="03001234567",
            email=self.client_user.email,
        )
        self.tax_case = TaxCase.objects.create(
            client=self.client_record,
            service_type="Income Tax",
        )

    def test_staff_service_cases_page_handles_unassigned_cases(self):
        self.client.force_login(self.staff)

        response = self.client.get(reverse("tax_cases"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "All service cases")
        self.assertContains(response, "Unassigned")
        self.assertContains(response, self.client_record.full_name)

    def test_staff_must_confirm_external_payment_before_starting_work(self):
        self.client.force_login(self.staff)
        route = reverse("edit_tax_case", args=[self.tax_case.pk])
        post_data = {
            "client": self.client_record.pk,
            "service_type": "Income Tax",
            "assigned_to": "",
            "status": "Processing Started",
            "target_date": "",
            "notes": "",
        }

        response = self.client.post(route, post_data)

        self.assertEqual(response.status_code, 200)
        self.tax_case.refresh_from_db()
        self.assertEqual(self.tax_case.status, "Newly Registered")
        self.assertContains(response, "Confirm payment outside the demo portal")

        response = self.client.post(route, {**post_data, "payment_verified": "on"})

        self.assertRedirects(response, route)
        self.tax_case.refresh_from_db()
        self.assertTrue(self.tax_case.payment_verified)
        self.assertEqual(self.tax_case.status, "Processing Started")
        self.assertTrue(ClientNotification.objects.filter(client=self.client_record, tax_case=self.tax_case).exists())
        self.assertTrue(ActivityLog.objects.filter(action="Case updated", tax_case=self.tax_case).exists())

    def test_client_uploads_document_and_staff_review_notifies_client(self):
        self.client.force_login(self.client_user)
        upload = SimpleUploadedFile("tax-record.pdf", b"sample", content_type="application/pdf")

        response = self.client.post(reverse("client_documents"), {
            "tax_case": self.tax_case.pk,
            "title": "Tax record",
            "document_type": "Tax",
            "notes": "Current tax record",
            "file": upload,
        })

        self.assertRedirects(response, reverse("client_portal"))
        document = ClientDocument.objects.get(client=self.client_record, title="Tax record")
        self.assertEqual(document.tax_case, self.tax_case)
        self.assertTrue(ActivityLog.objects.filter(action="Client document uploaded", client=self.client_record).exists())
        self.client.logout()
        self.assertEqual(self.client.get(document.file.url).status_code, 404)

        self.client.force_login(self.staff)
        response = self.client.post(reverse("review_document", args=[document.pk]), {
            "review_status": "Rejected",
            "reviewer_notes": "",
            "missing_or_corrected_request": "Please upload a clearer copy.",
        })

        self.assertRedirects(response, reverse("documents"))
        document.refresh_from_db()
        self.assertEqual(document.review_status, "Rejected")
        self.assertEqual(document.reviewed_by, self.staff)
        self.assertTrue(ClientNotification.objects.filter(client=self.client_record).exists())
        self.assertEqual(mail.outbox[-1].to, [self.client_user.email])

    def test_client_can_read_case_updates_and_mark_notifications_read(self):
        notification = ClientNotification.objects.create(
            client=self.client_record,
            tax_case=self.tax_case,
            title="Case progress updated",
            message="Your case is under review.",
        )
        self.client.force_login(self.client_user)

        response = self.client.get(reverse("client_case_detail", args=[self.tax_case.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Your case is under review.")

        response = self.client.post(reverse("mark_notification_read", args=[notification.pk]))

        self.assertRedirects(response, reverse("client_case_detail", args=[self.tax_case.pk]))
        notification.refresh_from_db()
        self.assertTrue(notification.is_read)

    def test_client_portal_shows_workspace_and_keeps_request_form_collapsed(self):
        self.tax_case.delete()
        self.client.force_login(self.client_user)

        response = self.client.get(reverse("client_portal"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Documents &amp; cases")
        self.assertContains(response, "Client details")
        self.assertContains(response, "Recent updates")
        self.assertContains(response, "My documents")
        self.assertContains(response, "My tax cases")
        self.assertContains(response, "No documents uploaded yet")
        self.assertContains(response, "No tax cases yet")
        self.assertContains(response, "Profile details &amp; service request")
        self.assertContains(response, 'name="address"')
        self.assertContains(response, 'name="ntn"')
        self.assertContains(response, 'name="business_details"')
        self.assertContains(response, 'name="tax_information"')
        self.assertContains(response, 'name="supporting_files"')
        self.assertContains(response, f'action="{reverse("client_service_request")}"')
        self.assertNotContains(response, '<details class="document-upload-panel service-request-panel" id="profile-request" open')
        self.assertNotContains(response, "Application status")
        self.assertNotContains(response, "Invoices &amp; payments")
        self.assertEqual(response.context["document_count"], 0)
        self.assertEqual(response.context["pending_document_count"], 0)
        self.assertEqual(response.context["case_count"], 0)

    def test_client_documents_url_redirects_to_combined_portal(self):
        self.client.force_login(self.client_user)

        response = self.client.get(reverse("client_documents"))

        self.assertRedirects(response, reverse("client_portal"))

    def test_client_cannot_download_another_clients_case_file(self):
        other_client = Client.objects.create(
            full_name="Other Client",
            cnic="44444-4444444-4",
            phone="03007654321",
            email="other@example.com",
        )
        other_case = TaxCase.objects.create(client=other_client, service_type="Sales Tax")
        case_file = TaxCaseFile.objects.create(
            case=other_case,
            title="Private file",
            file=SimpleUploadedFile("private.pdf", b"private", content_type="application/pdf"),
        )
        self.client.force_login(self.client_user)

        response = self.client.get(reverse("download_tax_case_file", args=[case_file.pk]))

        self.assertEqual(response.status_code, 403)

    def test_clients_with_blank_emails_cannot_access_each_others_files(self):
        blank_email_client = Client.objects.create(
            full_name="Blank Email Client",
            cnic="55555-5555555-5",
            phone="03007654321",
            email="",
        )
        blank_email_case = TaxCase.objects.create(
            client=blank_email_client,
            service_type="Sales Tax",
        )
        case_file = TaxCaseFile.objects.create(
            case=blank_email_case,
            title="Private blank-email file",
            file=SimpleUploadedFile("blank-private.pdf", b"private", content_type="application/pdf"),
        )
        self.client.force_login(self.client_user)

        response = self.client.get(reverse("download_tax_case_file", args=[case_file.pk]))

        self.assertEqual(response.status_code, 403)

    def test_staff_can_upload_case_file_and_manage_internal_tasks(self):
        self.client.force_login(self.staff)
        response = self.client.post(
            reverse("upload_tax_case_file", args=[self.tax_case.pk]),
            {
                "title": "Filed return",
                "file": SimpleUploadedFile("filed-return.pdf", b"filed", content_type="application/pdf"),
            },
        )

        self.assertRedirects(response, reverse("edit_tax_case", args=[self.tax_case.pk]))
        self.assertTrue(TaxCaseFile.objects.filter(case=self.tax_case).exists())
        self.assertTrue(ClientNotification.objects.filter(client=self.client_record, title="A case file is ready").exists())

        response = self.client.post(reverse("add_tax_case_task", args=[self.tax_case.pk]), {
            "title": "Verify source documents",
            "details": "Internal work item",
            "due_date": "",
        })
        self.assertRedirects(response, reverse("edit_tax_case", args=[self.tax_case.pk]))
        task = TaxCaseTask.objects.get(case=self.tax_case)
        self.assertTrue(ActivityLog.objects.filter(action="Internal task added", tax_case=self.tax_case).exists())

        self.client.post(reverse("toggle_tax_case_task", args=[task.pk]))
        task.refresh_from_db()
        self.assertTrue(task.is_complete)

    def test_staff_registration_requires_admin_approval_before_login(self):
        login_page = self.client.get(reverse("staff_login"))
        self.assertContains(login_page, "Request staff access")
        self.assertContains(login_page, 'class="staff-register-dialog"')
        self.assertContains(login_page, 'id="id_staff-register-username"')

        response = self.client.post(reverse("staff_register"), {
            "staff-register-first_name": "Public",
            "staff-register-last_name": "Applicant",
            "staff-register-username": "public-applicant",
            "staff-register-email": "public-applicant@example.com",
            "staff-register-password": "Secure-test-password-2026",
            "staff-register-confirm_password": "Secure-test-password-2026",
        })

        self.assertRedirects(response, reverse("staff_login"))
        user = User.objects.get(username="public-applicant")
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertEqual(user.profile.role, "STAFF")
        self.assertEqual(user.profile.account_status, "PENDING")

        response = self.client.post(reverse("staff_login"), {
            "username": "public-applicant",
            "password": "Secure-test-password-2026",
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Your staff account is not active.")
        self.assertNotIn("_auth_user_id", self.client.session)

        user.profile.account_status = "ACTIVE"
        user.profile.save(update_fields=["account_status"])
        response = self.client.post(reverse("staff_login"), {
            "username": "public-applicant",
            "password": "Secure-test-password-2026",
        })
        self.assertRedirects(response, reverse("home"))
        self.assertEqual(self.client.session["_auth_user_id"], str(user.pk))
