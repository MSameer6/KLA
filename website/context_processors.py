from accounts.forms import ClientRegisterForm, LoginForm


def client_registration(request):
    if request.user.is_authenticated:
        return {}
    return {
        "client_registration_form": ClientRegisterForm(),
        "client_login_form": LoginForm(request),
    }
