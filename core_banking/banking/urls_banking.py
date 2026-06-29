from django.urls import path
from . import views

urlpatterns = [
    path('alive', views.app_aliveness_test, name='aliveness'),

    path('transactions/', views.transaction_list, name='transaction_list'),
    path('deposit/', views.deposit_create, name='deposit_create'),
    path('withdraw/', views.withdraw_create, name='withdraw_create'),
    path('transfer/', views.transfer_create, name='transfer_create'),

    path('loans/request/', views.loan_request_create, name='loan_request_create'),
    path('loans/', views.loan_list, name='loan_list'),
    path('loans/<int:loan_id>/approve/', views.loan_approve, name='loan_approve'),
    path('loans/<int:loan_id>/installments/', views.loan_installments, name='loan_installments'),
    path("loan/reject/<int:loan_id>/", views.loan_reject, name="loan_reject"),

]
