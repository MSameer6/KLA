import tempfile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from unittest.mock import patch

from dashboard.models import ActivityLog, Client, ClientDocument, ClientInvoice, ClientNotification, TaxCase
from .forms import ClientRegisterForm


class ClientRegistrationTests(TestCase):
    def setUp(self):
        self.media_dir = tempfile.TemporaryDirectory()
        self.settings_override = override_settings(MEDIA_ROOT=self.media_dir.name)
        self.settings_override.enable()
        self.addCleanup(self.settings_override.disable)
        self.addCleanup(self.media_dir.cleanup)

    def registration_data(self):
        return {
            "first_name": "Amina",
            "last_name": "Khan",
            "username": "amina-khan",
            "email": "amina@example.com",
            "password": "Secure-test-password-2026",
            "confirm_password": "Secure-test-password-2026",
            "cnic": "12345-1234567-1",
            "phone": "03001234567",
            "address": "Lahore",
            "ntn": "1234567-8",
            "business_details": "Khan Consulting",
            "tax_information": "Registered for filing.",
            "needs_ntn_return": "on",
            "needs_sales_tax": "on",
            "needs_income_tax": "on",
            "case_details": "Please help with my registrations and returns.",
        }

    def test_registration_creates_cases_and_multiple_supporting_documents(self):
        data = self.registration_data()
        files = [
            SimpleUploadedFile("identity.pdf", b"identity", content_type="application/pdf"),
            SimpleUploadedFile("tax-record.jpg", b"tax record", content_type="image/jpeg"),
        ]

        response = self.client.post(
            "/client/register/",
            data={**data, "supporting_files": files},
        )

        self.assertRedirects(response, "/client/portal/")
        client = Client.objects.get(email="amina@example.com")
        self.assertEqual(client.user.username, "amina-khan")
        self.assertEqual(client.ntn, "1234567-8")
        self.assertEqual(client.business_details, "Khan Consulting")
        self.assertTrue(ClientNotification.objects.filter(client=client, title="Registration received").exists())
        self.assertCountEqual(
            client.tax_cases.values_list("service_type", flat=True),
            ["NTN Registration", "Return Filing", "Sales Tax", "Income Tax"],
        )
        self.assertTrue(all(case.notes == data["case_details"] for case in TaxCase.objects.filter(client=client)))
        self.assertCountEqual(
            client.documents.values_list("title", flat=True),
            ["identity.pdf", "tax-record.jpg"],
        )
        self.assertEqual(ClientDocument.objects.filter(client=client).count(), 2)
        invoice = ClientInvoice.objects.get(client=client)
        self.assertEqual(invoice.amount, 45000)
        self.assertIn("discounted from PKR 7,000", invoice.description)
        self.assertIn("PKR 20,000/month; first month", invoice.description)
        portal_response = self.client.get("/client/portal/")
        self.assertContains(portal_response, "Documents &amp; cases")
        self.assertContains(portal_response, "Client details")
        self.assertContains(portal_response, "My documents")
        self.assertContains(portal_response, "My tax cases")
        self.assertContains(portal_response, "identity.pdf")
        self.assertContains(portal_response, "Recent updates")
        self.assertContains(portal_response, "Registration received")
        self.assertNotContains(portal_response, "Tell us how we can help")
        self.assertNotContains(portal_response, "request-success-dialog")
        self.assertNotContains(portal_response, invoice.invoice_number)
        self.assertNotContains(portal_response, "Invoices &amp; payments")

    def test_registration_rejects_unsupported_supporting_files(self):
        data = self.registration_data()
        data["supporting_files"] = SimpleUploadedFile("payload.exe", b"not allowed")

        response = self.client.post("/client/register/", data=data)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "File extension")
        self.assertFalse(Client.objects.exists())

    def test_registration_shows_validation_error_for_existing_username(self):
        from django.contrib.auth.models import User

        User.objects.create_user(username="amina-khan", password="existing-password")
        data = self.registration_data()

        response = self.client.post("/client/register/", data=data)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "This username is already taken. Please choose another one.")
        self.assertEqual(User.objects.filter(username="amina-khan").count(), 1)
        self.assertFalse(Client.objects.exists())

    def test_registration_handles_username_taken_after_form_validation(self):
        from django.contrib.auth.models import User

        original_is_valid = ClientRegisterForm.is_valid

        def validate_then_claim_username(form):
            is_valid = original_is_valid(form)
            if is_valid:
                User.objects.create_user(username="amina-khan", password="Existing-password-2026")
            return is_valid

        with patch.object(ClientRegisterForm, "is_valid", validate_then_claim_username):
            response = self.client.post("/client/register/", data=self.registration_data())

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "This username is already taken. Please choose another one.")
        self.assertEqual(User.objects.filter(username="amina-khan").count(), 1)
        self.assertFalse(Client.objects.exists())

    def test_public_registration_popup_only_shows_account_and_contact_fields(self):
        response = self.client.get("/")
        dialog = response.content.decode().split('<dialog class="client-register-dialog"', 1)[1].split("</dialog>", 1)[0]

        for field_label in ("First name", "Last name", "Username", "Email address", "Password", "Confirm password", "CNIC", "Phone"):
            self.assertIn(field_label, dialog)
        for removed_content in ("Address", "Business details", "Tax information", "Services Required", "Case &amp; Supporting Files", "supporting-file-input"):
            self.assertNotIn(removed_content, dialog)
        self.assertIn("your portal later", dialog)

    def test_standalone_registration_keeps_full_form(self):
        response = self.client.get("/client/register/")

        self.assertContains(response, "Address")
        self.assertContains(response, "Business details")
        self.assertContains(response, "Services Required")
        self.assertContains(response, "Case &amp; Supporting Files")

    def test_client_can_submit_profile_services_and_files_after_registration(self):
        data = self.registration_data()
        for key in ("address", "ntn", "business_details", "tax_information", "needs_ntn_return", "needs_sales_tax", "needs_income_tax", "case_details"):
            data.pop(key)
        registration_response = self.client.post("/client/register/", data=data)
        self.assertRedirects(registration_response, "/client/portal/")
        client = Client.objects.get(email="amina@example.com")

        file = SimpleUploadedFile("tax-record.pdf", b"tax record", content_type="application/pdf")
        response = self.client.post(
            "/client/service-request/",
            data={
                "address": "Lahore",
                "ntn": "1234567-8",
                "business_details": "Khan Consulting",
                "tax_information": "Registered for filing.",
                "needs_ntn_return": "on",
                "needs_income_tax": "on",
                "case_details": "Please assist with registration and filing.",
                "supporting_files": [file],
            },
        )

        self.assertRedirects(response, "/client/portal/")
        client.refresh_from_db()
        self.assertEqual(client.address, "Lahore")
        self.assertEqual(client.ntn, "1234567-8")
        self.assertEqual(client.business_details, "Khan Consulting")
        self.assertEqual(client.tax_information, "Registered for filing.")
        self.assertTrue(client.needs_ntn_return)
        self.assertTrue(client.needs_income_tax)
        self.assertFalse(client.needs_sales_tax)
        self.assertCountEqual(
            client.tax_cases.values_list("service_type", flat=True),
            ["NTN Registration", "Return Filing", "Income Tax"],
        )
        self.assertEqual(ClientInvoice.objects.get(client=client).amount, 25000)
        document = ClientDocument.objects.get(client=client)
        self.assertEqual(document.client_id, client.pk)
        self.assertEqual(document.title, "tax-record.pdf")
        self.assertTrue(ClientNotification.objects.filter(client=client, title="Profile and service request updated").exists())
        self.assertTrue(ActivityLog.objects.filter(client=client, action="Client profile and service request updated").exists())

    def test_submitting_client_request_returns_to_workspace_without_popup(self):
        registration_response = self.client.post("/client/register/", data=self.registration_data())
        self.assertRedirects(registration_response, "/client/portal/")

        response = self.client.post(
            "/client/service-request/",
            data={
                "address": "Lahore",
                "needs_income_tax": "on",
                "case_details": "Please assist with my return.",
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Documents &amp; cases")
        self.assertContains(response, "Your profile details, service requests, and documents have been submitted.")
        self.assertNotContains(response, "request-success-dialog")
        self.assertNotContains(response, "Tell us how we can help")

    def test_repeated_service_submission_does_not_duplicate_active_cases_or_invoice(self):
        data = self.registration_data()
        registration_response = self.client.post("/client/register/", data=data)
        self.assertRedirects(registration_response, "/client/portal/")
        client = Client.objects.get(email="amina@example.com")
        initial_case_count = client.tax_cases.count()

        response = self.client.post(
            "/client/service-request/",
            data={
                "address": "Lahore",
                "needs_ntn_return": "on",
                "needs_sales_tax": "on",
                "needs_income_tax": "on",
            },
        )

        self.assertRedirects(response, "/client/portal/")
        self.assertEqual(client.tax_cases.count(), initial_case_count)
        self.assertEqual(ClientInvoice.objects.filter(client=client).count(), 1)
