from django.urls import path
from . import views

urlpatterns = [
    path('create/', views.customer_create, name='customer_create'),
    path('list/', views.customer_list, name='customer_list'),
    path('accounts/', views.account_list, name='account_list'),
    path('accounts/create/', views.account_create, name='account_create'),
    path('alive', views.app_aliveness_test, name='aliveness')
]

