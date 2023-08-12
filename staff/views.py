from django.shortcuts import render

# Create your views here.

def login(request):
    return render(request, 'auth/login.html')
    

def docs(request):
    return render(request, 'docs/views.html')
    