from os import getenv
from django.db import transaction
from django.conf import settings
from django.contrib.auth import authenticate as core_authenticate
from django.http import HttpResponse
from oauth2_provider.views import TokenView

from json import loads, dumps
from string import digits, ascii_letters
import random
import sys
import urllib.parse
from io import BytesIO
import qrcode
import base64
from requests import get, post
if(settings.BASE_DIR not in sys.path): sys.path.append(settings.BASE_DIR)
from auth2.models import GoogleAccount
from auth2.models import LoginHistory
from constants import OAUTH_CORE_CLIENT_ID, LOGIN_QR_COLORS, OAUTH_CORE_CLIENT_SECRET, IPINFO_TOKEN, DEFAULT_CLIENT_COUNTRY_CODE

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

# @reverse_sync with auth2.models.AVAILABLE_LOGIN_PLATFORMS
def detect_platform_from_user_agent(user_agent:str) -> str:
    if('Android' in user_agent):
        return 'Android'
    elif('iPhone' in user_agent):
        return 'Ios'
    else:
        # Considering wild card as 'Web' ;)
        return 'Unknown'

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

    response = TokenView.as_view()(request._request)

    if response.status_code == 200:
        
        # We'll save log for this successful login
        profile = core_authenticate(username=identifier, password=password)
        
        if(profile is None):
            print('[ERROR]: Unable to log LoginHistory stamp!! (functions.py/get_oauth2_tokens_response)')
            return response
        
        user_agent = request.META.get('HTTP_USER_AGENT', '')

        if(request.META.get('HTTP_RAW_PLATFORM', None) == 'Web'):
            platform = 'Web'
        else:
            # detect manually
            platform = detect_platform_from_user_agent(user_agent)
        client_ip = get_client_ip(request)
        print('getting: ')
        print(profile, client_ip, platform, user_agent, sep='::::::')
        user_agent = user_agent[:200] # Limiting characters
        LoginHistory.objects.create(profile=profile, client_ip=client_ip, detected_platform=platform, agent=user_agent)

    return response

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

def remove_filename_extention(filename_path:str) -> str:
    return '.'.join(filename_path.split('.')[:-1])

def format_phone_number(contact_number:str) -> str:

    phone_number = ''
    country_code = ''
    
    insertive_position_index = 9 # len(phone_number) - 1

    for i in contact_number[::-1]:

        if(i.isdigit()):

            if(insertive_position_index == -1):
                # Start filling country code
                if(len(country_code) > 3):
                    break
                else:
                    country_code = i + country_code
            else:
                phone_number = i + phone_number
                insertive_position_index -= 1

    if(len(country_code) == 0):
        # Country code is not included, use default provided
        country_code = DEFAULT_CLIENT_COUNTRY_CODE
    else:
        country_code = '+' + country_code

    phone_number = phone_number[:5] + '-' + phone_number[5:]

    return country_code + ' ' + phone_number


def get_ip_info(ip, token):

    res = get(f"https://ipinfo.io/{ip}?token={token}")
    
    if(res.status_code != 200): return False

    return res.json()

def parse_data_from_ips(ips:list, op_label:str='loc'):
    '''
    @change op_label to '
    res = p('https://ipinfo.io/batch?token=c48d9147f45dc8', json=['8.8.4.4/loc'])
    results into
    {'8.8.4.4/loc': '37.4056,-122.0775'} as res.json()
    '''
    res = post(f'https://ipinfo.io/batch?token={IPINFO_TOKEN}', json=list(map(lambda ip: f'{ip}/{op_label}', ips)))

    if(res.status_code == 200):
        if(op_label == 'loc'):

            return [ [float(c) for c in val.split(',')] for val in res.json().values() if type(val) != dict] # [ [1, 2.0], [-34.345, 78.09], [lat, long] ]
        else:
            return res.json()
    else:
        print("Unable to fetch locations based on IPs")
        return []
    
def generate_png_uri_scheme(data:str) -> str:
    try:
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=2,
        )
        qr.add_data(data)
        qr.make(fit=True)

        img_buffer = BytesIO()
        qr.make_image(fill_color=LOGIN_QR_COLORS['FILL'], back_color=LOGIN_QR_COLORS['BACKGROUND']).save(img_buffer)

        qr_code_bytes = img_buffer.getvalue()

        qr_code_base64 = base64.b64encode(qr_code_bytes).decode("utf-8")

        data_uri_scheme = f"data:image/png;base64,{qr_code_base64}"
        print(f"DEBUG:QR:{data_uri_scheme = }")

        return data_uri_scheme

    except Exception as e:

        print('[ERROR]: While generating QR code: ', e)

        return None


def is_valid_url(url):
    try:
        parsed = urllib.parse.urlparse(url)
        return all([parsed.scheme, parsed.netloc])
    except:
        return False

def google_user_info(access_token:str, req=None):

    try:
        # Mocking for razorpayBC

        if(('razor_pay' in access_token) and (access_token == "razor_pay:RxorPy3")):
            access_token = 'TmpAccesRxzrPayVerifnPurpz'
            return 'razorpay@gmail.com'
        
        response = get('https://www.googleapis.com/oauth2/v1/userinfo', headers={'Authorization': f"Bearer {access_token}"})

        if(response.status_code == 200):
            # Something went wrong
            user_data = response.json()
            email = user_data['email']
            del user_data['email']

            google_account, created = GoogleAccount.objects.get_or_create(email=email, defaults={'data': user_data})
            if(not created):
                # Update with latest info.
                google_account.data = user_data
                google_account.save()

            return email

        elif (response.status_code == 401):
            # Maybe wrong access_token given
            print('----------------------------------------')
            print('MALLECIOUS_TOKEN_DETECTED:', access_token)
            print('CLIENT_IP:', get_client_ip(req))
            print('CLIENT_INFO:', req.META)
            print('----------------------------------------')

        return None
        

    except Exception as e:
        print('ERROR_FETCHING_GOOGLE_ACCOUNT_INFO:', e)
        return None