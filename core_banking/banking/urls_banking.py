from django.urls import path
from . import views

urlpatterns = [
    path('alive', views.app_aliveness_test, name='aliveness')
]
