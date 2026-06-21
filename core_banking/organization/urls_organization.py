from django.urls import path
from . import views

app_name = 'organization'

urlpatterns = [
    path('users/', views.bank_user_list, name='bank_user_list'),
    path('users/create/', views.bank_user_create, name='bank_user_create'),
    path('users/<int:user_id>/edit/', views.bank_user_edit, name='bank_user_edit'),
    path('alive', views.app_aliveness_test, name='aliveness')
]
