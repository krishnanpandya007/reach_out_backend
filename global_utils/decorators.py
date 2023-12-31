from .models import NotProvided
from pymemcache.client.base import Client

from django.db.models import Model
from functools import wraps
from base64 import b64encode

from typing import Callable, Any
from constants import CACHE_TYPES_LIFETIME
import sys
from django.conf import settings
sys.path.append(settings.BASE_DIR)

from constants import OAUTH_CONFIGS, SOCIAL_INFO_FETCHER_BOT_NAME
import logging

logger = logging.getLogger(__name__)

client = Client(('127.0.0.1', 11211))

class memcache:

    @staticmethod
    def set(cache_type:str) -> Any:
        def inner_parent(cache_getter_func:Callable[[str, str], Any]) -> Any:

            @wraps(cache_getter_func)
            def inner(*args, **kwargs):

                if(cache_type not in CACHE_TYPES_LIFETIME.keys()):
                    print("`cache_type` not whitelisted! maybe add into constants/CACHE_TYPES_LIFETIME")
                    return None

                cache_key = "%s:%s" % (args[0], cache_type)
                otp =  cache_getter_func(*args, **kwargs) #  Here it must return cache_value if none, itll consider as failure to generate cacheKey and won't store in memcache
                if(otp == None):
                    print("Got None as cache_value, skipping to store it in memCache")
                    return None
                try:

                    client.set(cache_key, otp, CACHE_TYPES_LIFETIME[cache_type])                

                except Exception as e:
                    print('[FAIL_CACHE_%s]: ' % cache_type.upper(), e)
                    return None
                return otp

            return inner

        return inner_parent

    @staticmethod
    def get(cache_type:str, cache_key:str) -> Any:
        if(cache_type not in CACHE_TYPES_LIFETIME.keys()):
            print("`cache_type` not whitelisted! maybe add into constants/CACHE_TYPES_LIFETIME")
            return None
        try:
            data = client.get("%s:%s" % (cache_key.replace(' ', '-'), cache_type))
        except Exception as e:
            print("[FAIL_RETRIEVE_CACHE_%s]: " % (cache_type.upper()))
            return None

        return data.decode() if data is not None else None

    @staticmethod
    def manual_set(cache_type:str, cache_identifier:str, otp:str):
        if(cache_type not in CACHE_TYPES_LIFETIME.keys()):
            print("`cache_type` not whitelisted! maybe add into constants/CACHE_TYPES_LIFETIME")
            return None

        cache_key = "%s:%s" % (cache_identifier.replace(' ', '-'), cache_type)
        # otp =  cache_getter_func(*args, **kwargs) #  Here it must return cache_value if none, itll consider as failure to generate cacheKey and won't store in memcache
        if(otp == None):
            print("Got None as cache_value, skipping to store it in memCache")
            return None
        try:

            client.set(cache_key, otp, CACHE_TYPES_LIFETIME[cache_type])                

        except Exception as e:
            print('[FAIL_CACHE_%s]: ' % cache_type.upper(), e)
            return None
        return otp

    @staticmethod
    def delete(cache_type:str, cache_key:str) -> Any:
        if(cache_type not in CACHE_TYPES_LIFETIME.keys()):
            print("`cache_type` not whitelisted! maybe add into constants/CACHE_TYPES_LIFETIME")
            return None
        try:
            
            data = client.delete("%s:%s" % (cache_key.replace(' ', '-'), cache_type), noreply=False)

        except Exception as e:
            print("[FAIL_DELETE_CACHE_%s]: " % (cache_type.upper()))
            return None

        return data

    @staticmethod
    def validate_cache_key(cache_getter_func):

        @wraps(cache_getter_func)
        def inner(*args, **kwargs):

            if(len(args) < 1):
                raise Exception('Func must be built with initial arg with cache_key')

            if(not isinstance(args[0], str)):
                raise Exception('cache_key must be type of `str`')

            print(args, kwargs)
            return cache_getter_func(*args, **kwargs)

        return inner

    @staticmethod
    def is_valid_otp(identifier, otp):
        
        result = memcache.get(cache_type='OTP', cache_key=identifier)

        if(result is None):
            return False
        return result == otp

'''

Example Usage,

@memcache.set_new(cache_type='OTP')
@memcache.validate_cache_key
def generate_otp(username:str) -> Union[int, None]:
    code to generate OTP, return None to reflect error to decorators/wrappers
    return 3124
'''

def sync_with_model(model:Model, identifier:str, updation_fields:list):

    '''
    @param model which model needs to be updated laterwards
    @param identifier: field which can identify model uniquerly ex.. `pk`
    @param fields which fields are updated
    '''

    if(not isinstance(model, Model)):
        raise TypeError('`model` argument must be type of django.db.models.Model')

    def parent_wrapper(func):
        def wrapper(*args, **kwargs):
            res = func(*args, **kwargs)

            if(not isinstance(res, dict)):
                logging.warning('Returned value should be type of `dict`')
                return res

            if(res['error'] == True):
                return res

            model_identity = {identifier: res['identifier']}

            target_model = model.objects.get(**model_identity)
            for field in updation_fields:
                field_val = res.get(field, NotProvided)
                if(not isinstance(field_val, NotProvided)):
                    setattr(target_model, field, field_val)

            target_model.save()

            del res['identifier']

            return res

        return wrapper

    return parent_wrapper

from requests import post

def rotate_and_retry_on_400(func):
    def wrapper(*args, **kwargs):
        res = func(*args, **kwargs)
        if(res['error'] == 400):
            # retry the access token using given rotate_token
            rotate_token = kwargs.get('rotate_token', None)
            if(rotate_token is None):
                # Lol, rotate_token not provided, cant refresh token
                res['error'] = True
            platform = args[0]
            if(platform == 'Snapchat'):
                res = post(OAUTH_CONFIGS[platform]['refresh_access_token_endpoint'], params={'client_id': OAUTH_CONFIGS[platform]['client_id'], 'client_secret': OAUTH_CONFIGS[platform]['client_secret'], 'grant_type': 'refresh_token', 'refresh_token': rotate_token})
            elif (platform == 'Reddit'):
                encoded_credentials = b64encode(f"{OAUTH_CONFIGS[platform]['client_id']}:{OAUTH_CONFIGS[platform]['client_secret']}".encode('ascii'))
                res = post(OAUTH_CONFIGS[platform]['refresh_access_token_endpoint'], headers={'Authorization': f"Basic {encoded_credentials.decode('ascii')}", 'User-Agent': SOCIAL_INFO_FETCHER_BOT_NAME}, data={'grant_type': 'refresh_token', 'refresh_token': rotate_token})
            elif (platform == 'Discord'):
                res = post(OAUTH_CONFIGS[platform]['refresh_access_token_endpoint'], headers={'Content-Type': "application/x-www-form-urlencoded", 'User-Agent': SOCIAL_INFO_FETCHER_BOT_NAME}, data={'client_id': OAUTH_CONFIGS[platform]['client_id'], 'client_secret': OAUTH_CONFIGS[platform]['client_secret'],'grant_type': 'refresh_token', 'refresh_token': rotate_token})
            else:
                res['error'] = True
                res['relogin_required'] = True # for platforms like insta, Facebook, LinkedIn
            if(res != 200):
                # Unable to refresh access token, maybe invalid expired refresh token
                res['error'] = True
                res['relogin_required'] = True
            else:
                data = res.json()
                # Retrying the main ViewCall
                res = func(*args, **kwargs)
                # NOTE: Only set/update new_access, new_refresh if 'error' == False
                res['new_access'] = data['access_token']
                res['expires_in'] = data['expires_in']
                if(data.get('refresh_token', False)):
                    res['new_refresh'] = data['refresh_token']

        return res
    
    return wrapper

            
