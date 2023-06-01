from os import getenv
from django.db import transaction
from django.conf import settings
from django.http import HttpResponse
from oauth2_provider.views import TokenView

from json import loads, dumps
from string import digits, ascii_letters
import random
import sys
import urllib.parse
from requests import get, post
if(settings.BASE_DIR not in sys.path): sys.path.append(settings.BASE_DIR)

from constants import OAUTH_CORE_CLIENT_ID, OAUTH_CORE_CLIENT_SECRET, IPINFO_TOKEN

def get_staff_password(username):

    from hashlib import sha512
    m = sha512()
    m.update(bytes(username,'utf-8'))
    m.update(bytes(getenv('STAFF_PASSWORD_TRANSACTION_KEY', 'vn36DIW!N*Zn2&$nh!rZ3A&k3CykzLE2PpC5QfNBjyq^%2WYF9'),'utf-8'))
    return m.hexdigest()

def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip

def get_oauth2_tokens_response(request, identifier=None, refresh_token=None,password=None, c_id=OAUTH_CORE_CLIENT_ID, c_secret=OAUTH_CORE_CLIENT_SECRET):
    '''
    gets oauth2 tokens for given identifier (based on username,email, phone)
    for staff: its compulsary to provide `password` arg.
    '''
    if(refresh_token is None):
        request.data.update({"client_id": c_id, "client_secret": c_secret, "grant_type": "password", "username": identifier, "password": password or "dummy_weak_pass"})
    else:
        request.data.update({"client_id": c_id, "client_secret": c_secret, "grant_type": "refresh_token", "refresh_token": refresh_token})
        

    mutable_data = request.data.copy()
    request._request.POST = request._request.POST.copy()
    for key, value in mutable_data.items():
        request._request.POST[key] = value

    return TokenView.as_view()(request._request)

def modify_http_response_json_content(response:HttpResponse, edits:dict):

    if(response['Content-Type'] != 'application/json'):
        # NotSupported
        return response
    
    content=loads(response.content)
    for key, val in edits.items():
        content[key] = val
    response.content = dumps(content)

    return response

def generate_otp(length=5, complex=False, addon=''):
    choice_domain:str = digits if not complex else (digits + ascii_letters.replace('l', '').replace('i', '').replace('L', '').replace('I', '') +addon)
    return ''.join(random.choice(choice_domain) for i in range(length))

def format_phone_number(contact_number:str, client_country_calling_code:str):

    if(" " in contact_number[-10:]):
        contact_number = contact_number[:-10] + contact_number[-10:].replace(' ', '-')
    if("-" not in contact_number[-10:]):
        contact_number = contact_number[:-5] + '-' +  contact_number[-5:]
    if("+" not in contact_number):
        contact_number = client_country_calling_code + " " + contact_number
    else:
        if(contact_number[-12] != ' '):
            contact_number = contact_number[:-11] + ' ' + contact_number[-11:]
    return contact_number

def get_ip_info(ip, token):

    res = get(f"https://ipinfo.io/{ip}?token={token}")
    
    if(res.status_code != 200): return False

    return res.json()

def parse_lat_lon_of_ips(ips:list, op_label:str='loc'):
    '''
    @change op_label to '
    res = p('https://ipinfo.io/batch?token=c48d9147f45dc8', json=['8.8.4.4/loc'])
    results into
    {'8.8.4.4/loc': '37.4056,-122.0775'} as res.json()
    '''
    res = post(f'https://ipinfo.io/batch?token={IPINFO_TOKEN}', json=list(map(lambda ip: f'{ip}/{op_label}', ips)))

    if(res.status_code == 200):
        return [ [float(c) for c in val.split(',')] for val in res.json().values() if type(val) != dict] # [ [1, 2.0], [-34.345, 78.09], [lat, long] ]
    else:
        print("Unable to fetch locations based on IPs")
        return []
    

def is_valid_url(url):
    try:
        parsed = urllib.parse.urlparse(url)
        return all([parsed.scheme, parsed.netloc])
    except:
        return False