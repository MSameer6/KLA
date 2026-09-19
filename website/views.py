from django.shortcuts import render


def home(request):
    return render(request, "website/home.html")


def about(request):
    return render(request, "website/about.html")


def services(request):
    return render(request, "website/services.html")


def contact(request):
    return render(request, "website/contact.html")