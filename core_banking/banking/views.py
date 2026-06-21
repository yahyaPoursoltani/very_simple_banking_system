from django.shortcuts import render

# Create your views here.
from django.shortcuts import render
from django.http import HttpResponse


# Create your views here.
def app_aliveness_test(request):
    return HttpResponse("banking app is alive!!")
