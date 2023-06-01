from django.urls import path
from gui import views

urlpatterns = [
    path('login', views.login, name='Login View'),
    path('docs', views.docs, name='Login View'),
]