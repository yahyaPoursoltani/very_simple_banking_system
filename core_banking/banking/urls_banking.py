from django.urls import path
from . import views

urlpatterns = [
    path('alive', views.app_aliveness_test, name='aliveness'),

    path('transactions/', views.transaction_list, name='transaction_list'),
    path('deposit/', views.deposit_create, name='deposit_create'),
    path('withdraw/', views.withdraw_create, name='withdraw_create'),
    path('transfer/', views.transfer_create, name='transfer_create'),
]
