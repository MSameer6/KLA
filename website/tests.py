from django.test import TestCase


class PublicWebsiteSmokeTests(TestCase):
    def test_public_pages_load(self):
        for path in ["/", "/about/", "/services/", "/contact/"]:
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 200)

    def test_client_register_buttons_open_compact_registration_dialog(self):
        response = self.client.get("/")

        self.assertRegex(
            response.content.decode(),
            r'src="/static/js/auth(?:\.[a-f0-9]+)?\.js\?v=20261114-1"',
        )
        self.assertContains(response, 'class="client-register-dialog"')
        self.assertContains(response, 'data-open-client-registration')
        self.assertContains(response, "Account &amp; contact details")
        self.assertContains(response, 'name="first_name"')
        self.assertContains(response, 'name="email"')
        self.assertContains(response, 'name="cnic"')
        self.assertContains(response, 'name="phone"')
        self.assertNotContains(response, 'name="address"')
        self.assertNotContains(response, 'name="ntn"')
        self.assertNotContains(response, 'name="business_details"')
        self.assertNotContains(response, 'name="tax_information"')
        self.assertNotContains(response, 'name="supporting_files"')
        self.assertNotContains(response, "Services Required")

    def test_public_pages_include_client_login_popup_and_switch_link(self):
        response = self.client.get("/")

        self.assertContains(response, '<dialog class="client-register-dialog"')
        self.assertContains(response, 'class="client-register-dialog client-login-dialog"')
        self.assertContains(response, 'data-open-client-login')
        self.assertContains(response, 'action="/client/login/"')
        self.assertContains(response, 'name="username"')
        self.assertContains(response, 'name="password"')
        self.assertContains(response, "Secure Client Login")
        self.assertContains(response, "Create an account")
        self.assertContains(response, "Already registered?")
