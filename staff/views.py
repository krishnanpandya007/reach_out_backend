from django.shortcuts import render, redirect
from django.urls import reverse as core_reverse
from django.contrib.auth import authenticate, login as core_login
from django.contrib.auth import logout as core_logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from time import perf_counter
from rest_framework.decorators import permission_classes
from rest_framework.permissions import IsAuthenticated, IsAdminUser
import sys
from django.conf import settings
if(settings.BASE_DIR not in sys.path): sys.path.append(settings.BASE_DIR)
from auth2.models import Profile, LoginHistory

# Create your views here.

def login(request):
    if(request.method == 'POST'):
        username = request.POST.get('username')
        password = request.POST.get('password')

        print(f"{username = }, {password = }")

        user = authenticate(username=username, password=password)

        if ((user is not None) and user.is_staff):
            core_login(request, user)
            return redirect('Console View')
        else:
            messages.error(request, "Incorrect staff credentials!")
            return render(request, 'auth/login.html')

    else:
        if(request.GET.get('error_message')):
            messages.error(request, request.GET.get('error_message'))

        return render(request, 'auth/login.html')
    
@login_required(login_url='/login')
def docs(request):
    return render(request, 'docs/views.html')

@login_required(login_url='/login')
def console(request):

    if(not request.user.is_staff):
        core_logout(request)
        return redirect(core_reverse('Login View') +"?error_message=Access denied")

    if(request.method == 'POST'):
        # get radio (action type) along with filters ex, name:krishnan pandya&
        print('DEBUG:REQUEST::', request.GET)
        print('DEBUG:REQUEST::', request.POST)
        filter_user_name = request.POST.get('filter_user_name')        
        filter_general_filters = request.POST.get('filter_general_filters')  
        last_seen = request.POST.get('last_seen') == 'on'      
        isp_location = request.POST.get('isp_location') == 'on'      
        login_activity = request.POST.get('login_activity') == 'on'      
        active_users = request.POST.get('active_users') == 'on'      
        user_info = request.POST.get('user_info') == 'on'      

        # filter dataset according to filter values (ex. name & general filters)

        first_name:str
        last_name:str
        profiles = None

        # Start timer to measure execution time overall
        timer_start = perf_counter()

        if(len(filter_user_name) > 0):
            # time to filter profiles by their name
            first_name, *last_name = filter_user_name.split(" ")

            if(last_name):
                last_name = last_name[0]
            else:
                last_name = ''

            profiles = Profile.objects.filter(first_name__icontains=first_name, last_name__icontains=last_name)
        else:
            profiles = Profile.objects.all()

        # Now we are applying general filters to name_filtered profiles
        # Firstly check if filter type is valid or use switch case instead for this, throw flash message if unknown key found or ignore it
        # Maybe check dime delta to turn those results & if possible db calls
        requested_page = 1
        page_length = 10 # Each page contains 10 results max.
        

        for general_filter in filter_general_filters.split(' '):
            if(str(general_filter).count(':') != 1):
                print("Invalid general filter")
                continue
            print("DEBUG: this is general filter::", general_filter)
            filter_name, filter_value = general_filter.split(':')

            match(filter_name):

                case 'city':

                    profiles = profiles.filter(point__city__icontains=filter_value)

                case 'page':
                    # IMP: keep this filter at bottom of all filters
                    # Paginate `profile` queryset and set `requested_page` to given value
                    if(str(filter_value).isnumeric()):
                        requested_page = int(filter_value)

                case _:
                    print("Invalid filter_name")

        paginator = Paginator(profiles, page_length)
        page_obj:None

        try:
            page_obj = paginator.get_page(int(requested_page))
        except PageNotAnInteger:
            # if page_number is not an integer then assign the first page
            page_obj = paginator.page(1)
        except EmptyPage:
            # if page is empty then return last page
            page_obj = paginator.page(paginator.num_pages)

        timer_stop = perf_counter()

        time_taken = timer_stop - timer_start
        time_taken = round(float(time_taken), 3)

        total_pages = paginator.num_pages
        # at end show, Page 1 / 13, each contains max 5 entries.-> maybe add another filter: page:2
        return render(request, 'console.html', context={ 'no_of_results': paginator.count, 'time_taken': f"{time_taken} seconds.", 'last_seen': last_seen, 'isp_location': isp_location, 'login_activity': login_activity, 'active_users': active_users, 'user_info': user_info, 'query_set': page_obj.object_list, 'current_page': requested_page, 'total_pages': total_pages, 'page_size': page_length })
    else:
        return render(request, 'console.html')

def logout(request):
    core_logout(request)
    return redirect('Login View')