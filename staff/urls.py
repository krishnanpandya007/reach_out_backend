from django.urls import path
from staff import views

urlpatterns = [
    path('login', views.login, name='Login View'),
    path('docs', views.docs, name='Login View'),
]