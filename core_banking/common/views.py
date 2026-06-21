from django.shortcuts import render

# Create your views here.
from django.shortcuts import render
from django.http import HttpResponse
from django.db import connection

# Create your views here.
def app_aliveness_test(request):
    return HttpResponse("common app is alive!!")


def home_page(request):
    return render(request, "home.html")


def contact_page(request):
    return render(request, "contact.html")


def test_db(request):

    with connection.cursor() as cursor:
        cursor.execute("SELECT COUNT(*) FROM Customer")
        result = cursor.fetchone()

    return HttpResponse(f"Customers: {result[0]}")
