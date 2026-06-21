from django.urls import path
from . import views

urlpatterns = [
    path('alive/', views.app_aliveness_test, name='aliveness'),
    path('', views.home_page, name='homepage'),
    path('contact/', views.contact_page, name='contact'),
    path("testdb/", views.test_db, name="testDB")

]
