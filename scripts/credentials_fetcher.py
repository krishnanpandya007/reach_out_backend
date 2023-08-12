from django.conf import settings
from django.utils import timezone
from requests import get, post, patch
from base64 import b64encode
from instaloader import Instaloader
from json import dumps
from logging import getLogger

import urllib.request
import sys,os
sys.path.append(settings.BASE_DIR)
from global_utils.decorators import rotate_and_retry_on_400
from constants import SOCIAL_INFO_FETCHER_BOT_NAME,SOCIAL_MEDIAS,PROFILE_PIC_BASE_PATH,OAUTH_CONFIGS
from auth2.models import RawSnap, Social

instaloader = Instaloader()
logger = getLogger(__name__)


'''
NOTE: We have to create `Social` model on `linking` action for social
not on `login` action
'''

# In Dicord we get user_id in user_info, while in 

# In Instagram we get user_id at access token retreival and also at user_info

platform_token_fetchers:dict
platform_info_fetchers:dict

def get_social_access_token(platform, code=None):

    try:
        assert platform in SOCIAL_MEDIAS, "Invalid/Unidentifiable Platform provided, Aborting..."

    except AssertionError as ae:
        return {
            'error': True,
            'message': "Social media not whitelisted"
            }

    data_as_json = platform_token_fetchers[platform](platform, code=code)

    access_token = data_as_json.get('access_token', None)
    refresh_token = data_as_json.get('refresh_token', None)
    expires_in = data_as_json.get('expires_in', None)

    if(access_token is not None):
        return {'error': False, 'access_token': access_token, 'refresh_token': refresh_token, 'expires_in': expires_in}
    else:
        data_as_json["error"] = True
        return data_as_json

def get_social_user_data(platform, access_token, rotate_token=None, sync_model=None, take_raw_snap=False):

    '''
    @param rotate_token is used refresh token when,
        - Initial UserData respond with status 400, we'll refresh access token if possible and retry the request

    @param sync_model => if provided or not None, it tries to edit and save that model
                       - ex.. Social.objects.get(pk=s_id)
    @param take_raw_snap => if True, tries to take up snap of registered social medias and save `RawSnap`
    '''

    try:
        assert platform in SOCIAL_MEDIAS, "Invalid/Unidentifiable Platform provided, Aborting..."

    except AssertionError as ae:
        return {
                'error': True,
                'primary': None,
                'secondary': None,
                'profile_id': None
            }

    data_as_json = platform_info_fetchers[platform](platform, access_token, take_raw_snap=take_raw_snap)

    try:
        if((data_as_json['error']==False) and (sync_model is not None)):
            print('Gotten')
            print(data_as_json)
            sync_model.handleId = data_as_json['profile_id']
            sync_model.name = data_as_json['primary']
            sync_model.profilePicUrl = data_as_json['secondary']
            if(data_as_json.get('new_access', False)):
                sync_model.access_token = data_as_json['new_access']
                sync_model.expires_at = timezone.now() + timezone.timedelta(seconds=data_as_json['expires_in'])
            if(data_as_json.get('new_refresh', False)):
                sync_model.refresh_token = data_as_json['new_refresh']
            if(data_as_json.get('relogin_required', False)):
                print('Innn')
                sync_model.relogin_required = data_as_json['relogin_required']

            sync_model.save()
        elif(data_as_json['relogin_required']==True) and (sync_model is not None):
            sync_model.relogin_required = True
            sync_model.save()
    except Exception as e:
        logger.error('Cannot sync user_data to target model', e)

    return data_as_json

def get_meta_user_data(platform, access_token, take_raw_snap=False):

    if (platform != 'Facebook') and (platform != 'Instagram'):

        print("Error: ", "Invalid Platform, not associted with Meta. either not whitelisted at ReachOut")

        return {
            'error': True,
            'profile_id': None,
            'primary': None,
            'secondary': None,
        }

    url = OAUTH_CONFIGS[platform]['info_retrieval_endpoint']
    user_data_response = get(url % access_token)
    if(user_data_response.status_code == 400):
        return {
            'error': True,
            'profile_id': None,
            'primary': None,
            'secondary': None,
            'relogin_required': True
        }
    user_data_json = user_data_response.json() 
    print("Raw:", user_data_json)
    if(user_data_response.status_code == 200):

        if(platform == 'Facebook'):
            profile_pic_url = (f"https://graph.facebook.com/v16.0/{user_data_json['id']}/picture?type=large&access_token={access_token}" if user_data_json['picture'] else None)
            fb_avatar_url = None
            if(profile_pic_url is not None):
                # Download profile pic to folder,save it generate URL, save it
                res = urllib.request.urlopen(profile_pic_url)

                relative_avatar_url = os.path.join(PROFILE_PIC_BASE_PATH, 'Facebook', user_data_json['id'] + '.jpeg')
                fb_avatar_url=os.path.join(os.getcwd(), relative_avatar_url)
                fil = open(fb_avatar_url, 'wb')
                fil.write(res.read())
                fil.close()
                fb_avatar_url = '/' + relative_avatar_url.replace('\\', '/')
            return {
                'error': False,
                'profile_id': user_data_json['id'],
                'primary': user_data_json['name'],
                'secondary': fb_avatar_url,
            }
        # For Instagram
        return {
            'error': False,
            'profile_id': user_data_json['id'],
            'primary': user_data_json['username'],
            'secondary': instaloader.get_profile_pic_url(user_data_json['username']),
        }

    else:
        return {
            'error': True,
            'profile_id': None,
            'primary': None,
            'secondary': None,
        }
#FDL
@rotate_and_retry_on_400
def get_snapchat_user_data(platform, access_token, take_raw_snap=False):
    user_info_fetch_headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {access_token}',
        'Accept': 'application/json',
        'User-Agent': SOCIAL_INFO_FETCHER_BOT_NAME
    }
    # If we have access token fetch the information and return success code mixin

    user_data_response = post(OAUTH_CONFIGS['Snapchat']['info_retrieval_endpoint'], json={'query': "{me{displayName bitmoji{avatar} externalId profileLink}}"}, headers=user_info_fetch_headers, timeout=15)
    # print("SNAP_RESP:",user_data_response.json())
    if(user_data_response.status_code == 400):
        # Try on request to refresh acces token then if fails then returns error response
        
        return {
            'error': 400, # triggers rotate_access_token action and retry this
            'profile_id': None,
            'primary': None,
            'secondary': None
        }
    elif user_data_response.status_code == 401:
        print('returned')
        return {
            'error': True,
            'primary': None,
            'secondary': None,
            'profile_id': None,
            'relogin_required': True
        }
    try:
        
        user_data = user_data_response.json()
        # print("alele:",user_data)
        # Fetch primary & Secondary info for discord/make another function for fething out primary
        # and secondary information per app/social platform
        if(user_data_response.status_code == 200 and user_data.get('data', False)):

            return {

                'error': False,
                'primary': user_data['data']['me']['displayName'],
                'secondary': user_data['data']['me']['bitmoji'].get('avatar', None),
                'profile_id': user_data['data']['me']['externalId']

            }

    finally:

        return {
            'error': True,
            'primary': None,
            'secondary': None,
            'profile_id': None,
            'relogin_required': True
        }

@rotate_and_retry_on_400
def get_user_data_generally(platform, access_token, take_raw_snap=False):
    user_info_fetch_headers = {
        'Authorization': f'Bearer {access_token}',
        'User-Agent': SOCIAL_INFO_FETCHER_BOT_NAME
    }
    # If we have access token fetch the information and return success code mixin

    user_data_response = get(OAUTH_CONFIGS[platform]['info_retrieval_endpoint'], headers=user_info_fetch_headers, timeout=15)
    # print("user_data_core:Debug", )
    if(user_data_response.status_code == 401):
        return {
            'error': True,
            'primary': None,
            'secondary': None,
            'profile_id': None,
            'relogin_required': True
        }
    user_data = user_data_response.json()
    # Fetch primary & Secondary info for discord/make another function for fething out primary
    # and secondary information per app/social platform
    if(user_data_response.status_code == 200):

        # Take up snap if premissioned
        try:
            if(take_raw_snap):
                snap = RawSnap.objects.create(snap_type='Social:UserData:%s' % platform, snap_key=str(user_data['user']['id'] if platform == 'Discord' else (user_data['subreddit']['display_name'] if platform == 'Reddit' else user_data['id'])), snap_data=dumps(user_data))
                snap.save()
        except Exception as e:
            logger.error('Cannot take RawSnap of userData:', e)

        if(platform == 'Discord'):

            return {
                'error': False,
                'primary': user_data['user']['username'] + '#' + user_data['user']['discriminator'],
                'secondary': 'https://cdn.discordapp.com/avatars/' + user_data['user']['id'] + '/' + user_data['user']['avatar'] + '.png',
                'profile_id': user_data['user']['id']
            }
        
        elif (platform == 'Reddit'):

            return {
                'error': False,
                'primary': user_data['name'],
                'secondary': user_data['subreddit']['icon_img'],
                'profile_id': user_data['subreddit']['display_name'],
                'subreddit_url': user_data['subreddit']['url']
            }
        elif (platform == 'LinkedIn'):
            return {
                'error': False,
                'primary': user_data['firstName']['localized'][user_data['firstName']['preferredLocale']['language'] + '_' + user_data['firstName']['preferredLocale']['country']] + ' ' + user_data['lastName']['localized'][user_data['lastName']['preferredLocale']['language'] + '_' + user_data['lastName']['preferredLocale']['country']],
                'secondary': user_data['profilePicture']['displayImage~']['elements'][0]['identifiers'][0]['identifier'],
                'profile_id': user_data['id']
            }

    else:
        return {
            'error': True if platform == 'LinkedIn' else user_data_response.status_code, # Bypass retry_rotate_hook on LinkedIn platform
            'primary': None,
            'secondary': None,
            'profile_id': None,
        }

def get_token_generally(platform, code=None):
    '''
    Get the token the general way
    '''
    platform_config = OAUTH_CONFIGS[platform]



    data = {
        'client_id': platform_config['client_id'],
        'client_secret': platform_config['client_secret'],
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': platform_config['redirect_uri'],
    }

    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
        'User-Agent': SOCIAL_INFO_FETCHER_BOT_NAME

    }
    
    r = post(platform_config['access_retrieval_endpoint'], data=data, headers=headers, timeout=15)

    data_as_json =  r.json()

    return data_as_json

def get_reddit_tokens(platform='Reddit', code=None):

    platform_config = OAUTH_CONFIGS['Reddit']

    encoded_credentials = b64encode(f"{platform_config['client_id']}:{platform_config['client_secret']}".encode('ascii'))

    data = {
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': platform_config['redirect_uri'],
    }
    # print("Debug authentication: ", f"Basic {encoded_credentials.decode('ascii')}")
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
        'Authorization': f"Basic {encoded_credentials.decode('ascii')}",
        'User-Agent': SOCIAL_INFO_FETCHER_BOT_NAME
    }

    
    r = post(platform_config['access_retrieval_endpoint'], data=data, headers=headers, timeout=15)

    data_as_json =  r.json()
    return data_as_json

def get_instagram_token(platform='Instagram', code=None):

    platform_config = OAUTH_CONFIGS["Instagram"]

    data = {
        'client_id': platform_config['client_id'],
        'client_secret': platform_config['client_secret'],
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': platform_config['redirect_uri'],
    }

    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
        'User-Agent': SOCIAL_INFO_FETCHER_BOT_NAME

    }
    
    r = post(platform_config['access_retrieval_endpoint'], data=data, headers=headers, timeout=15)

    data_as_json =  r.json()
    print('InitialInstagramAccessResponse::', data_as_json)
    access_token = data_as_json.get('access_token', None)
    # access_token = data_as_json.get('access_token', None)
    if(access_token is None):

        # Some Error while retrieving access_token, try later?
        return {'error': True}

    long_lived_access_token_retrieval_url = "https://graph.instagram.com/access_token"

    data['grant_type'] = "ig_exchange_token"
    data['access_token'] = access_token
    del data['client_id']
    del data['code']
    del data['redirect_uri']

    r = get(long_lived_access_token_retrieval_url, params=data, headers=headers, timeout=15)
    data_as_json =  r.json()
    return data_as_json
    '''
    In instagram, there is a way to refresh access token
    curl -i -X GET "https://graph.instagram.com/refresh_access_token
  ?grant_type=ig_refresh_token
  &access_token={long-lived-access-token}"

  {
  "access_token":"{long-lived-user-access-token}",
  "token_type": "bearer",
  "expires_in": 5183944 // Number of seconds until token expires
}

    '''

def get_facebook_token(platform='Facebook', code=None):

    platform_config = OAUTH_CONFIGS["Facebook"]

    data = {
        'client_id': platform_config['client_id'],
        'client_secret': platform_config['client_secret'],
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': platform_config['redirect_uri'],
    }

    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
        'User-Agent': SOCIAL_INFO_FETCHER_BOT_NAME

    }

    # facebook_api_version = 'v15.0' | v4.0
    
    r = post(platform_config['access_retrieval_endpoint'], data=data, headers=headers, timeout=15)

    data_as_json =  r.json()
    access_token = data_as_json.get('access_token', "IGQVJYYWR6VzlJZAC03N0NrZAGYzdXFyNXU5ZAklZAMlkwSG5ZAMkRWRndGSUtpSzdpakVzaXR4WDY1alRheTh0em1wcDdmUlZACR3d6bkJnajVhTGNMdk00dWl4Y0dpZAHdHa0tZAYkNjRjJ6Mm52cTFtNFFzTDB5emRJSGpFbFRj")
    # access_token = data_as_json.get('access_token', None)
    if(access_token is None):
        print("Falling")
        # Some Error while retrieving access_token, try later?
        return False

    long_lived_access_token_retrieval_url = "https://graph.facebook.com/v15.0/oauth/access_token"

    data['grant_type'] = "fb_exchange_token"
    data['fb_exchange_token'] = access_token
    # del data['code']
    # del data['redirect_uri']

    r = get(long_lived_access_token_retrieval_url, params=data, headers=headers, timeout=15)

    data_as_json =  r.json()

    print("DebugFacebookLongLivedAccessToken: ", data_as_json)
    return data_as_json

def refresh_social_access_token(platform, rotate_token):

    '''
    (define these methods in Model `Social`)
    (LOGIN WORKFLOW)READ ONLY[
        decodeState => {type: 'Login', pid: -1, Media: 'Instagram'}
        after that Instagram sends UNIQUE:profile_id for `Social` model
            -failure => return False, Something went wrong(probabily wrong code | Temperring)
        Social.objects.filter(socialMedia='Instagram', profile_id=recieved_pid)
            - if not found return false, 400(No such linked social media handle to any existing user)
        we filter that and find parent `Profile` model for `Social` return true, 200p
        we return `Profile's email (for login), Name (for Greeting user on App)
    ]
    (LINKING WORKFLOW)READ/WRITE[after this we must assert in `state` that pid is linked with mentioned Media or not => return pid ]
    - linking social media procedure
    social_login_handler() => bool,
        - input:code => error,access_refresh
            if error return False (failed to retrieve access/refreshToken)

        - getUserData(access_token) => synced_response, error
            - if error
                - refresh_access_token o GOTO getUserData once => failed to get new_access_token
                    - return False:TokenMaybeExpired | relogin_needed


    '''

    '''
    TODO: Testing is remaining
    testing procedure:
        1. Obtain access token for all social media
        2. get refresh_token/rotate_token along with
        3. use it to refresh access token using this view
        4. try with valid and invalid rotate token/observe response code
        1. Instagram - must signin after 2 months
            -no refresh_token (but long_lived...)
            - splitter: #
            - no refresh
            - valid from 2 months user sign in using it ()
            - no rawSnap needed

            @on_invalid_rotate_token: 400 : 200

        2. Facebook - must re login after 2 months
            - no refresh_token support
            - splitter: #
            - access token valid for 2 months
            - noRawSnapNeeded

        3. Snapchat - IDK on 400 relogin_required
            - no rawSnap needed
            - profile_id CAESIKD/****
            - splitter: none
            - has refresh
            - has access (2 hours*)

            @on_invalid_rotate_token 400 : 200

        4. Reddit ~ Forever flow
            - splitter: #
            - has access token (1 day)
            - has refresh token (lifetime bitch 😎)
            - ✅ raw snap needed (on user_data)

            @on_invalid_rotate_token 400 : 200

        5. LinkedIn - must signin after 2 months
            - no refresh_token support
            - access token (2 months)
            - ✅ raw snap needed (on user_data)
            @does not support `refresh_acccess_token`
            @on_invalid_rotate_token 403:200

        6. Discord ~ Forever Flow
            - access token (7 days)
            - refresh token (untill user unauthorizes this apk)
            - ✅ raw snap needed (on user_data)


    '''

    try:

        assert platform in SOCIAL_MEDIAS, "Invalid platform!"

        match(platform):

            case 'Instagram':
                res = get(OAUTH_CONFIGS[platform]['refresh_access_token_endpoint'] % rotate_token)
                print("RotateDebug: res", res)
                if(res.status_code != 200):
                    return {
                        'error': True,
                        'access_token': None,
                        'expires_in': None,
                        'refresh_token': None
                    }
                json_data = res.json()
                return {
                    'error': False,
                    'access_token': json_data.get('access_token', None),
                    'expires_in': json_data.get('expires_in', None),
                    'refresh_token': None
                }

            case 'Facebook' | 'LinkedIn':
                return {
                    'error': True,
                    'access_token': None,
                    'expires_in': None,
                    'refresh_token': None,
                    'requires_relogin': True
                }
            
            case 'Snapchat' | 'Reddit':
                encoded_credentials = b64encode(f"{OAUTH_CONFIGS[platform]['client_id']}:{OAUTH_CONFIGS[platform]['client_secret']}".encode('ascii'))

                headers = {
                    'Authorization': f"Basic {encoded_credentials.decode('ascii')}",
                    'User-Agent': SOCIAL_INFO_FETCHER_BOT_NAME
                }

                if(platform == 'Snapchat'):
                    headers['Content-Type'] = 'application/x-www-form-urlencoded'

                res = post(OAUTH_CONFIGS[platform]['refresh_access_token_endpoint'], headers=headers, data={'grant_type': 'refresh_token', 'refresh_token': rotate_token})
                json_data = res.json()
                print("RotateDebug: res", res)

                if(res.status_code != 200):
                    return {
                        'error': True,
                        'access_token': None,
                        'expires_in': None,
                        'refresh_token': None,
                    }
                
                return {
                        'error': False,
                        'access_token': json_data.get('access_token', None),
                        'expires_in': json_data.get('expires_in', None),
                        'refresh_token': json_data.get('refresh_token', None),
                    }

            case 'Discord':

                headers = {
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'User-Agent': SOCIAL_INFO_FETCHER_BOT_NAME
                }

                res = post(OAUTH_CONFIGS[platform]['refresh_access_token_endpoint'], headers=headers, data={'grant_type': 'refresh_token', 'refresh_token': rotate_token, 'client_id': OAUTH_CONFIGS[platform]['client_id'], 'client_secret': OAUTH_CONFIGS[platform]['client_secret']})
                json_data = res.json()
                print("RotateDebug: res", res)

                if(res.status_code != 200):
                    return {
                        'error': True,
                        'access_token': None,
                        'expires_in': None,
                        'refresh_token': None,
                    }
                
                return {
                        'error': False,
                        'access_token': json_data.get('access_token', None),
                        'expires_in': json_data.get('expires_in', None),
                        'refresh_token': json_data.get('refresh_token', None),
                    }
            

    except AssertionError as ae:
        return {
            'error': True,
            'access_token': None,
            'expires_in': None,
            'refresh_token': None
        }


platform_token_fetchers = {

    'Reddit': get_reddit_tokens,
    'Instagram': get_instagram_token,
    'LinkedIn': get_token_generally,
    'Facebook': get_facebook_token,
    'Snapchat': get_token_generally,
    'Discord': get_token_generally

}

platform_info_fetchers = {

    'Reddit': get_user_data_generally,
    'Instagram': get_meta_user_data,
    'LinkedIn': get_user_data_generally,
    'Facebook': get_meta_user_data,
    'Snapchat': get_snapchat_user_data,
    'Discord': get_user_data_generally

}

# print(exchange_code("AQDQSFdtHCLFbA5_CL0e91yulNuvlY46hXlCMazskp0LYO2PDfSpcbqRd-AnDZb3sZdr9xgvZ-mbIy-cIr5Wq_2-8U5rGy5fA7vVmL5-RAH3eboEn0drN8x7lUNqUwd3N4i7AWIhOnOvHo-CJyMeByH6dGU0zO-9BNZSy4dUtS0ikuzBJ8ysGBRtKR70qrg8DZSLWTBNtN6vIKgDBOuzzZk0KtOmo5Rk7-IexspCaaLhoA", platform='Instagram'))
# print(exchange_code("AQBwhmrAiv2CRCOBRjfEr9tuQH33sBH_iY-gtd3dokA6MhJqxbkNoZ4fPBhznfpOG8MH_KIZ-ESveuBpmKcNLMSMUptVQxzLK3Sis8qoPzrTaOyWSQgWfEaZb79LWCsEIZvOw0GIo2PmQDAN-AvgtMWg8B0jvF8rbuhjAYSZnszh68CGfn1a_2J8UGoPWn5E5u_UjOSMQgEy4waGTHecLxy_ANyJFJEsZh0b0lM9vu-VnWEWDkNiC3C8Z3ayxp8SNofvJesDTX5BX8HtTzRJtaP3q42I9rnSzyP7bgYbjY4lAKbW4tbTePa5d4zG8ynApbHde2OiZQSTmXw4ZHNeeNU72_VRxCl_HAB1_Qdn8VYBsJssck1bLJMksLkzY9FYHLtQKUsBDhYak7ycRO4uWx-3Wl9FF0CCa0PpDskTp0nmpQ", platform='Facebook'))
# get_instagram_token("asd")
# print(exchange_code("AQDyLcgd2sTmA5dDis5S5Gii5Olm9cQJ2wunqcW89j9vFDxZdIphuajhmXyvBUg79RQpK2BvkkufEXVMH6bUQLViFJdOgaUdv9Oii1SbKRrio7lSW__aFIGRvgLWsjsRmJK6sUiZxP-obssSUc1fHYtonl5HfERI5wPN5hgrNYEYJ8psRvEZJ3364ZeGK80dhfQYI7V5HYSj8y5LVHq052VPkpkrZxB-qn-zBqYXsHSOzw", platform='Instagram'))
# print(exchange_code("L5bPfQMPHX03u4EB0gPgI8QyfM8lCN8K_htC6jy_YAQ", platform='Snapchat'))
'''
SnapAccess
eyJpc3MiOiJodHRwczpcL1wvYWNjb3VudHMuc25hcGNoYXQuY29tXC9hY2NvdW50c1wvb2F1dGgyXC90b2tlbiIsInR5cCI6IkpXVCIsImVuYyI6IkExMjhDQkMtSFMyNTYiLCJhbGciOiJkaXIiLCJraWQiOiJhY2Nlc3MtdG9rZW4tYTEyOGNiYy1oczI1Ni4wIn0.._6-9hFmUquv_qCHwAjhxaw.MfOseflXD6xLDxS0CoOR-dzmS8hA2gYlrEy2bMNPGT3SzSTUY2jG7j0o5QvoGmzx-E7sXljH-7ePlHiCg4v4XDRncHz-00szSAcmMINTnl_dgU6z6HY7uct_XjkslTpx2I3t3BRZmAj9x1JS8iBhXtIV8CS9EewRoBlNeN2QPwQ2LHQJs4VFZEgURSFDuvEIbTImuPsNE9W4knNsJnDT8nP3PU_oVooiDmZBXIt3nnvMxvV5Dl_UEB43lZ412z1aT4jR3RVedHXp2EDHnYRqxcF2sBKrxRlMUnTyLEaASDLylFmsu0RmftzoaWjfo_xfOQDpGqZwu0Vwdzdm2wJ06Cm324xHbnAHiF6eCYl1n4RrSvZ6cfAvpoi_QtGLiZn15wRQky5eW0V15GTowd3gTEghXK8nEwIeWmRjcqCnGVVdOeqeU2_xQvtSXijD1n_41egRo6l3bxBQw61K9qyJW2jxlyO4VsTzX3gnnBB33AqP39wUYji2wC71v7rYGOxYwypEs8Vb5UPdf-e0RtTU3sjcgH5cLEhtlEv3rHfoiPDW5yteKNDT2SjMOeoCg-gkpittPKtsF9HCK8DoyeFS3GdpvcmUwApUQvxveN-r4y_aTHF7lwVsxo1SAeE2GPjBFIPT7kfB9pzTfvzqEW1wCplYlBW54udrj3WzWjA7QjElEdaWsUbRAgPQ-F1fSj9WH-0XTsuuzp3BLOJKu7BHuo_Y_klICrcobpBIeV0JkaXUmATlhIGTFeVTxikR30E1s8uxCYPqOmadA3F-G44jhMk-gp1ke4uZP2HNO5064nU.vCAGJl0EthyuQjPXS0yBnA

SnapRefresh
eyJraWQiOiJyZWZyZXNoLXRva2VuLWExMjhnY20uMCIsInR5cCI6IkpXVCIsImVuYyI6IkExMjhHQ00iLCJhbGciOiJkaXIifQ..K5Ek52_vyFjwvPgK.Mxvpa5AZPx1bqMB2nPeB03QzSR2BDOcBYo5DMPsJQJ8l874D6rqeBeXM0I4IRK0bcNhn_F11OU8Na86DB592CdLcP6I_YEXNAYVraaYwwUt0NdDV0gXY7mrti8Dpo0KkCF-aynvLsE0IWEH2rd76wwxJaUT0kpmkdfpFFmRGYLl1JNVkh2Hr2nyhWPGJGZFSwHC-gCzHPwCZHbTZ416gtZi14MpjLBbDab5ZHwbivH-0H6xKuSAKL6HgRzENl_W37Aisem-XbXBve3mNSobQ_mICrlEXEisGIYLbE-1ghn4tytlBmdvnfYc6MxsT3eMl.vBhLW2aXibo19W38ewfa3A

RedditCode: kBviuWRddUsUdPLf9pTuYKl-QqdduA
RedditAccess: 1133901000900-H5DhQYLBUUNBM6gDegnEq86TNzmfuA

LinkedIn Accesstoken: 
AQVHpwUWb54uvf_1OuprMqNhC20YjGS3Z1B3Gt1R_ntgRQtTgcveZ2FGnW1-SbGX9FiC1b0lTeHG4jG5TdIQnGp63lAoJJPFSLsL6KkOTLAfz23_oLGEE_PYXzMKy8Qk7qKh7XWFoYrlA5P2CyN-QE8OfngXHU1LlwXHQYZdxoLaVRpRGTbuhJj-3fhslGQ72KD5yK-8VP-h2XOePFgUMLkHvwW4zQXKmU5464FJ_qD9L2W46TopvoMpc37L4DeO1yMjEdWrH-u-wHVw2MF2SpwMYLCVXB8CNRy0yUX31vWyxk3vpKeUHkYpDCbpgYUmB3KFXbJ5iLhXTnQD6mWky0kk5Fj5uQ
@for 60 days


FacebookCode: AQB7eKvdru7o-QGET2-9XKauPO78skTjJhkTmsGEVoPj3l1NbNuITHgaS0938fXy8eRtx6q1omZdtwe7DfubN1rAajMCDa96iKX2MfK-eaZJ8ywK8fBK5q4HX3pYh1_S1isM-_q2N9k185w0tqEocQU-1crLxMQA-dxCaix4_n7zmIoLnb7jSMbVpVAEwhBa5Htdz1Lu5FOzvPQ1_361ImCgaTRnenVDlbJXuXSN5cOaWGdk4rUnfSTHBHBa125ZT2b5RVWHRdJVq7RN3fHdS6FmY6TC4ZKJLpv4MLP-bTneVVzZ8argvwCAVIPmhrZKLxsazfnGWiKdIaePl3iaYypFjrphW_4M5oNKzEsYZgm17TSbNBeeO3lsvfOMqP3PpDMrajv3nmB3UJKUR_72KPye_m83K24RX5CIqzNUL-izlg

'''

# get_reddit_tokens('zAr4xmRazllobRrwt0vxN8HIfLm2SA')