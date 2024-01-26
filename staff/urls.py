from django.urls import path
from staff import views

urlpatterns = [
    path('login', views.login, name='Login View'),
    path('docs', views.docs, name='Docs View'),
    path('console', views.console, name='Console View'),
    path('logout', views.logout, name='Logout View'),
]