from django.db import transaction
from django.core.exceptions import ValidationError
from django.core.signing import Signer, BadSignature
from django.conf import settings
from django.http import HttpResponse
from django.core.mail import send_mail

from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from rest_framework.decorators import permission_classes, api_view
from django.utils import timezone
from .models import Profile, Phone, Social
from twilio.rest import Client
import logging
from json import loads
# from oauth2_provider.settings import refre
from re import match as regex_match
import sys
from urllib.parse import unquote as decode_uri
if(settings.BASE_DIR not in sys.path): sys.path.append(settings.BASE_DIR)
from constants import SOCIAL_TOKEN_PROTECTOR_KEY, SOCIAL_TOKEN_PROTECTOR_SALT, EMAIL_BASIC_STRUCTURE, EMAIL_EMOJI_URL,TWILIO_ACCOUNT_SID,TWILIO_AUTH_TOKEN,TWILIO_PHONE_NO,EMAIL_REGEX,PHONE_REGEX,SOCIAL_MEDIAS,SOCIAL_OAUTH_LINKS,OAUTH_WEB_CLIENT_ID, OAUTH_WEB_CLIENT_SECRET, SOCIAL_LINKS_PREFIXES
from global_utils.functions import get_oauth2_tokens_response, generate_otp, format_phone_number, is_valid_url
from global_utils.decorators import memcache
from scripts.credentials_fetcher import get_social_access_token, get_social_user_data

logger = logging.getLogger(__name__)
social_token_signer = Signer(SOCIAL_TOKEN_PROTECTOR_KEY, salt=SOCIAL_TOKEN_PROTECTOR_SALT)
twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)


'''
TODO: login/mode=(email | phone | social)  [auth2]
      signUp/ => Initially no social Media [auth2]
      link/social => if already linked? raise snackbar with `report a problem` RedirectableAction [api]
'''

class SignUpView(APIView):

      permission_classes = (AllowAny,)

      def post(self, request, *args, **kwargs):
            try:

                  name = request.data.get('name', '').split(' ')
                  email = request.data.get('email', None)
                  phone = request.data.get('phoneNo', None)
                  
                  assert len(name) == 2, "Provide valid `name`!"
                  assert email is not None, "Email is required!"
                  assert phone is not None, "PhoneNo is required!"

                  try:
                        phone = format_phone_number(phone, '+91')
                  except Exception:
                        pass

                  print(phone)

                  f_name, l_name = name

                  try:
                        # we want to rollback the `Phone` creation if creation of profile failed
                        with transaction.atomic():

                              phone = Phone.objects.create(number=phone)

                              new_profile = Profile.objects.create(first_name=f_name, last_name=l_name, email=email, phone=phone)

                              new_profile.save()

                              phone.target_profile = new_profile

                              phone.save()


                  except ValidationError as ve:
                        print(ve)
                        
                        return Response(data={'error': True,'message': ve.messages[0]}, status=400)

                  return Response({'error': False, 'message': 'Profile created'},status=201)


                  
            except AssertionError as ae:
                  return Response({'error': True, 'message': str(ae)},status=400)


            except Exception as e:
                  logging.info(f"{self.__class__.__name__}:[OUTER_EXC]:", e)
                  return Response({'error': True, 'message': 'Something went wrong!'},status=500)

class VerificationWithLoginView(APIView):
      # TODO: Testing for email, phone login
      # 1. start memcache server, set OTP then try to login
      '''
      This view is for obtaining initial access/refresh token on login workflow
      if client uses login_with_email/login_with_phone => then first another view sends OTP then this view verifies and log in the user
      '''

      permission_classes = (AllowAny,)

      def post(self, request, *args, **kwargs):

            try:

                  mode = request.data.get('mode', False)
                  
                  assert mode in ['email', 'phone_no', 'social'], "Invalid Login mode"
                  # email="krishnanpandya06@gmail.com"

                  if(mode == 'social'):
                        # Do Social verification stuff
                        code = request.data.get('code', None)
                        state = request.data.get('state', None) # Pass on directly the SyncKey/SyncToken (encrypted)

                        try:
                              data = social_token_signer.unsign_object(state)
                              profile_id = data.get('profile_id', None) # -1
                              reason_type = data.get('flow_type', None)# Login/Linking
                              platform = data.get('platform', None) # Any
                              assert profile_id and platform, "Invalid state"
                              assert reason_type in ['Login', 'Linking'], "Invalid state Tempered/MalformedRedirection"                              

                        except (BadSignature) as bs:
                              logger.warning('Tempered state!')
                              return Response({'error': True, 'message': 'Tempered State detected'},status=400)
                        
                        else:
                              # pid, socialMedia
                              # Here we need to return app redirection url that redirects uer to app's specific page which confirms social linking of user

                              token_response = get_social_access_token(platform, code) 

                              # print(token_response['message'])

                              assert token_response['error'] == False, "Please try again later"

                              if(reason_type == 'Login'):

                                    temp_access = token_response['access_token']

                                    user_data_response = get_social_user_data(platform, temp_access)

                                    assert user_data_response['error'] == False, "Please try again later"

                                    # Check if returned profile Id exists in our DB or not
                                    target_media = Social.objects.filter(socialMedia=platform, handleId=user_data_response['profile_id'])
                                    
                                    assert target_media.exists(), "The social handle that you've just login through was not linked to any profile on this platform! ;(" # Reply with code

                                    target_media = target_media.first()

                                    mode_identifier = target_media.profile.email
                              
                              else:

                                    '''
                                    OverwriteSocialMEdiaIfExists
                                    For linking create social and attach or overwrite existing social and attach it
                                    # returned params (in url) : social_link_status: success|error
                                    # returned params (in url) : social_link_msg: STR
                                    # returned params (url) : redirect_app_path: STR: reachoutapp.org./asd?social_link_status=success&social_link_mdg=something s not working
                                    '''
                                    try:

                                          profile_link:str = None
                                          if(platform == 'LinkedIn'):
                                                profile_link = request.data.get('profile_link', False)
                                                assert profile_link, "@param `profile_link` must be provided for such socials"
                                                profile_link = decode_uri(profile_link)
                                                assert regex_match(r'^(https?://)?([a-z]{2,3}\.)?linkedin\.com/(in|pub|company)/[a-zA-Z0-9_-]+/?$',profile_link), "LinkedIn profile link already attached to another profile"
                                          elif(platform == 'Facebook'):
                                                profile_link = request.data.get('profile_link', False)
                                                assert profile_link, "@param `profile_link` must be provided for such socials"
                                                profile_link = decode_uri(profile_link)
                                                assert regex_match(r'^(https?://)?(www\.)?facebook\.com/[a-zA-Z0-9_.-]+/?$',profile_link), "Facebook profile link already attached to another profile"
                                          elif (platform == 'Snapchat'):
                                                snap_username = request.data.get('profile_link', False)
                                                assert regex_match(r'^[a-zA-Z][a-zA-Z0-9_]{2,14}$', snap_username), "Snapchat username already linked to another profile!"
                                                profile_link = f"https://www.snapchat.com/add/{snap_username}"

                                          target_profile = Profile.objects.get(pk=profile_id)
                                          target_social_media = target_profile.socials.filter(socialMedia=platform)
                                          
                                          if(target_social_media.exists()):
                                                
                                                # For overwriting delete the old one linked account
                                                target_social_media = target_social_media.first()
                                                target_social_media.delete()
                                    
                                          # Lets link non-existing social media
                                          # target_social_media.access_token = token_response['access_token']
                                          # target_social_media.refresh_token = token_response['refresh_token']
                                          # target_social_media.expires_in = timezone.now()+timezone.timedelta(seconds=token_response['expires_in'])
                                          data_response = get_social_user_data(platform, token_response['access_token'], rotate_token=token_response['refresh_token'])
                                          assert data_response['error'] == False, "Failed retrieving social data!"
                                          '''
                                          Generating profile_link for remaining socials
                                          '''
                                          if(profile_link is None):
                                                '''
                                                NOTE: in reddit maybe URL joining collide because of slash
                                                '''
                                                profile_link = SOCIAL_LINKS_PREFIXES[platform]['base_url'].format(data_response[SOCIAL_LINKS_PREFIXES[platform]['target_field']])
                                          # AccessToken, refreshToken, expires, primary,secondary(profile_link), 
                                          Social.objects.create(profile=target_profile, socialMedia=platform, handleId=data_response['profile_id'], access_token=token_response['access_token'], refresh_token=token_response['refresh_token'], expires_at=timezone.now()+timezone.timedelta(seconds=token_response['expires_in']), name=data_response['primary'], profilePicUrl=data_response['secondary'], profile_link=profile_link, last_updated=timezone.now())
                                          
                                          return Response({'error': False, 'message': 'Social Linked!', 'redirect_app_path':  f"/link/socials/?social_link_status=success&social_link_msg={platform} profile linked succefully!"}, status=200)
                                    except AssertionError as aae:
                                          print(aae)
                                          return Response({'error': False, 'message': 'unable to link social', 'redirect_app_path':  f"/link/socials/?social_link_status=error&social_link_msg=Error linking {platform} profile, Try again later."}, status=400)
                        print('Ono')
                        return Response({'error': True, 'message': 'Something went wrong'},status=400)

                  else:
                        mode_identifier = request.data.get('mode_identifier', None)# phone => +91 2334-45,email
                        otp = request.data.get('otp', None)

                        assert (mode_identifier is not None) and (otp is not None), "missing mode extra params"
                        if(mode == 'phone_no'):
                              mode_identifier = format_phone_number(mode_identifier, '+91')
                        otp_valid = memcache.is_valid_otp(mode_identifier, otp)
                        assert otp_valid, "Invalid OTP"

                        if(mode == 'email'):
                              print("Identifier:", mode_identifier)
                              profile = Profile.objects.get(email=mode_identifier)
                              profile.email_verified = True
                              profile.save()
                        else:
                              phone = Phone.objects.get(number=mode_identifier)
                              phone.number_verified = True
                              phone.save()


                  response = get_oauth2_tokens_response(request, identifier=mode_identifier)
                  print("debug response: ", response, response.content)
                  # response = modify_http_response_json_content(response, edits=Profile.getStartupInfo(mode_identifier))

                  try:
                        if(response.status_code == 200):
                              if(mode != 'social'):
                                    memcache.delete('OTP', mode_identifier)
                  except Exception as e:
                        logger.error('Unable to delete cached OTP on login flow', e)

                  return response


            except (Profile.DoesNotExist, Phone.DoesNotExist) as ne:
                  return Response({'error': True, 'message': 'Profile not found'}, status=404)        

            except AssertionError as ae:
                  print('assa', ae)
                  return Response({'error': True, 'message': str(ae)},status=400)

            except Exception as e:
                  logging.info(f"{self.__class__.__name__}:[OUTER_EXC]:", e)
                  return Response({'error': True, 'message': 'Something went wrong!'},status=500)

class SendOTPView(APIView):

      '''
      First we try to safely_delete the value stored already with mentioned identifier
      then we generate OTP of 4 chars
      then we try to send OTP to identifier
      '''

      permission_classes = (AllowAny,)

      def post(self, request, *args, **kwargs):

            try:

                  mode = request.GET.get('mode', None)

                  assert mode in ['email', 'phone_no'], "param `mode` can be either `email` or `phone`"

                  identifier = request.data.get('identifier', None)

                  assert identifier is not None, "Provide `identifier` property in payload"

                  if(mode == 'phone_no'):

                        # Checking if that phone no. exists in DB

                        identifier = format_phone_number(identifier, '+91')

                  '''
                  We try to delete old OTP associated to given `identifier`
                  '''
                  memcache.delete('OTP', identifier)

                  otp = generate_otp()

                  if(mode == 'email'):

                        assert Profile.objects.filter(email=identifier).exists(), "No such email linked to any profile!"

                        assert regex_match(EMAIL_REGEX, identifier) and isinstance(identifier, str), "Invalid email!"

                        res = send_mail("Verify OTP - ReachOut Login", message=f"Please DragN'Drop this otp to continue login. OTP-{otp} ", from_email='server.reachout@gmail.com', html_message=(EMAIL_BASIC_STRUCTURE % (EMAIL_EMOJI_URL['hello'], (f'''
                        <p style="line-height: 2.5ch;padding-bottom: 1rem;margin-bottom: 1rem;font-size: 1rem;border-bottom: 1px dashed white;color: white;">We've recieved this email for verification workflow in order to login, here the OTP is attached enter it to continue login.</p><pre>OTP</pre><b style="font-size: 1.3rem;padding-bottom: 1rem;letter-spacing:1px;">{otp}</b><p style="border-bottom: 1px dashed white"/><br><i>If this message is not for you kindly ignore it.</i>
                        '''))), recipient_list=[identifier])

                  else:
                        assert Phone.objects.filter(number=identifier).exists(), "No such phoneNo linked to any profile!"

                        assert regex_match(PHONE_REGEX, identifier) and isinstance(identifier, str), "Invalid PhoneNo!"

                        res = twilio_client.messages.create(to=identifier.replace(' ', '').replace('-', ''), from_=TWILIO_PHONE_NO, body="Your ReachOut login's verification code is: %s. only valid for 5 minutes." % otp)

                        print("Debug:res::", res)

                  assert bool(res), "Try again later!"

                  memcache.manual_set('OTP', identifier, otp)

                  return Response({'error': False, 'message': 'Verification code sent!'}, status=200)

            except AssertionError as ae:
                  return Response({'error': True, 'message': str(ae)},status=400)

            except Exception as e:
                  logging.info(f"{self.__class__.__name__}:[OUTER_EXC]:", e)
                  return Response({'error': True, 'message': 'Something went wrong!'},status=500)

class SocialConnectionUrlBuilderView(APIView):

      '''
      @returns: socialRedirectUrl
      profile_id = data.get('profile_id', None) # -1
      reason_type = data.get('type', None)# Login/Linking
      platform = data.get('platform', None) # Any
      '''

      permission_classes = (AllowAny,)

      def get(self, request):

            try:

                  platform = request.GET.get('platform', None)
                  reason_type = request.GET.get('flow_type', None)

                  assert platform in SOCIAL_MEDIAS, "Platform not whitelisted"
                  assert reason_type in ['Login','Linking'], "Invalid flow_type"

                  if(not request.user.is_authenticated):
                        if(reason_type == 'Linking'):
                              return Response({'error': True, 'message': "You must be authorized to access `Linking` action"}, status=401)
                  else: 
                        assert reason_type != 'Login', "You must be unauthorized to login, xD"

                  data = {
                        'profile_id': request.user.pk if request.user.is_authenticated else -1,
                        'flow_type': reason_type,
                        'platform': platform
                  }
                  signed_state = social_token_signer.sign_object(data)
                  # NOTE: Below sperator is also sensitive to frontend portion
                  signed_state = platform + '@@' + signed_state

                  redirection_url = SOCIAL_OAUTH_LINKS[platform] + '&state=' + signed_state

                  return Response({'error': False, "message": 'Social connection URL builded!', 'socialRedirectUrl': redirection_url}, status=200) 

            except AssertionError as ae:
                  return Response({'error': True, 'message': str(ae)},status=400)

            except Exception as e:
                  logging.info(f"{self.__class__.__name__}:[OUTER_EXC]:", e)
                  return Response({'error': True, 'message': 'Something went wrong!'},status=500)
                     
class UpdateAccessTokenView(APIView):

      permission_classes = (AllowAny,)

      def post(self, request, *args, **kwargs):

            try:

                  grant_type = request.data.get('grant_type', None)
                  refresh_token = request.data.get('refresh_token', None)

                  assert grant_type == 'refresh_token', "invalid `grant_type`"                  
                  assert isinstance(refresh_token, str) , "invalid `refresh_token`"                  
                  if(request.META.get('HTTP_RAW_PLATFORM', None) == 'Web'):
                        # For web we've recieved encrypted token
                        # Let's decrypt it

                        obj = social_token_signer.unsign_object(refresh_token)
                        refresh_token = obj['ref']
                        response = get_oauth2_tokens_response(request, refresh_token=refresh_token, c_id=OAUTH_WEB_CLIENT_ID, c_secret=OAUTH_WEB_CLIENT_SECRET)

                        assert response.status_code == 200, "Invalid Refresh Code" # unable to fetch access,refreshTokten

                        data = loads(response.content)
                        response.set_cookie('access_token', data['access_token'], max_age=data['expires_in'], secure=True, httponly=True, samesite='Strict')
                        response.set_cookie('refresh_token', data['refresh_token'], max_age=getattr(settings, 'OAUTH2_PROVIDER', {})['REFRESH_TOKEN_EXPIRE_SECONDS'], secure=True, httponly=True, samesite='Strict')
                        response.set_cookie('stale_authenticated', 'true', max_age=getattr(settings, 'OAUTH2_PROVIDER', {})['REFRESH_TOKEN_EXPIRE_SECONDS'], secure=True, httponly=False, samesite='Lax')

                        response.content = b''
                        return response



                  response = get_oauth2_tokens_response(request, refresh_token=refresh_token)

                  return response

            except AssertionError as ae:
                  return Response({'error': True, 'message': str(ae)},status=400)

            except Exception as e:
                  print("TempErr:", e)
                  return Response({'error': True, 'message': 'Something went wrong!'}, status=500)



@api_view(['POST'])
@permission_classes([IsAuthenticated,])
def update_social(request, *args, **kwargs):
    '''
      *Build class => get-> linkedSocials/reloginRequired
                      put-> updateSocial
    3 purposes:
      * Update: /social/update?action=update&social=Instagram

    Links specific social to user's profile
    @data_params: `code`, `state`, `profile_link?` (required on LinkedIn/Snapchat)
    '''

    try:

            platform = request.GET.get('media', None)
            
            assert platform in SOCIAL_MEDIAS, "Invalid social media"
            target_social_media = request.user.socials.filter(socialMedia=platform)
            assert target_social_media.exists(), f"{platform} social not linked to your profile"

            res = get_social_user_data(platform, target_social_media.access_token, rotate_token=target_social_media.rotate_token, sync_model=target_social_media)

            if(res['error']):
                  # Come/Goes direct to APK
                  return Response({'error': True, 'message': 'Something went wrong!', 'relogin_required': res.get('relogin_required', False)}, status=500)
                  
            return Response({'error': False, 'message': 'Social Updated!'}, status=201)
            '''
            let new_access/new_refresh matters here/other updations can be also reviewed/handled below part
                  - relogin_required (need to be handled here...)

            * UpdateSocial view to update info like firstname,ProfilePic

            2purpose click,
                  * Link new social media (handleId doesnt Exist)
                  * when ReloginRequired caused (handleId exists)(expired access/refresh)
                        * handleId already exists, just refresh accesstoken, refreshtoken using provided code
            if(handleId.exists()):
                  if(relogin_required):
                        get @param `code`
                        # Fetch new tokens and setUpdatedTokens

                  updateSocialData(update primary,secondary,profileLink)
            else:
                  # New social to link to profile

            '''
            




    except AssertionError as ae:
        return Response({'error': True, 'message': str(ae)},status=400)

    except Exception:
        return Response({'error': True, 'message': 'Something went wrong!'},status=500)


class WebSignInView(APIView):
      '''
      Use to let ReachOut webVersion login to your account.
      View used to generate signIn code as well as verify that signIn code

      @get => generates signIn code (5 random chars (aA1&#%@)) stores in memcache for 2 mins. (then its expires!)
      @post => verifies the signIn code returns oauth credentials based on `ReachOut Web client` (expire code if success)

      '''

      permission_classes = (AllowAny,)

      def get(self, request, *args, **kwargs):
            try:

                  if(not request.user.is_authenticated):
                        return Response({'error': True, 'message': 'You must be authenticated!'}, status=401)

                  profile = request.user

                  generated_code:str = generate_otp(complex=True)

                  memcache.manual_set('WEB_SIGNIN_CODE', str(profile.pk), generated_code)

                  return Response({'error': False, 'message': 'Web SignIn Code generated!', 'web_signin_code': generated_code}, status=201)

            except Exception as e:
                  return Response({'error': True, 'message': 'Something went wrong!'}, status=500)

      def post(self, request, *args, **kwargs):

            try:

                  mode = request.data.get('mode', None)
                  mode_value = request.data.get('mode_value', None)
                  signin_code = request.data.get('signin_code', None)

                  assert (mode and mode_value and signin_code), "Provide valid `mode` `mode_value` `signin_code`"

                  if(mode == 'email'):
                        try:
                              profile = Profile.objects.get(email=mode_value)
                        except (Profile.DoesNotExist) as ne:
                              return Response({'error': True, 'message': 'No Profile found with provided email'}, status=404)   
                  elif (mode == 'phone_no'):
                        mode_value = format_phone_number(mode_value, '+91')
                        try:
                              target_phone = Phone.objects.get(number=mode_value)
                              profile = Profile.objects.get(phone=target_phone)
                        except (Profile.DoesNotExist, Phone.DoesNotExist) as ne:
                              return Response({'error': True, 'message': 'No Profile found with provided Phone No.'}, status=404)   
                              
                  else:
                        return Response({'error': True, 'message': 'Invalid Mode'},status=400)

                  # correct_code = memcache.get('WEB_SIGNIN_CODE',str(profile.pk)) 

                  # assert correct_code is not None, "Please generate signIn code first!"
                  # assert signin_code == correct_code, "Invalid signIn code"

                  response = get_oauth2_tokens_response(request, mode_value, c_id=OAUTH_WEB_CLIENT_ID, c_secret=OAUTH_WEB_CLIENT_SECRET)

                  assert response.status_code == 200, "Try again later" # unable to fetch access,refreshTokten

                  data = loads(response.content)
                  response.set_cookie('access_token', data['access_token'], max_age=data['expires_in'], secure=False, httponly=True, samesite='Strict')
                  response.set_cookie('refresh_token', data['refresh_token'], max_age=getattr(settings, 'OAUTH2_PROVIDER', {})['REFRESH_TOKEN_EXPIRE_SECONDS'], secure=False, httponly=True, samesite='Strict')
                  response.set_cookie('stale_authenticated', 'true', max_age=getattr(settings, 'OAUTH2_PROVIDER', {})['REFRESH_TOKEN_EXPIRE_SECONDS'], secure=False, httponly=False, samesite='Lax')

                  response.content = b''
                  return response

            except AssertionError as ae:
                  return Response({'error': True, 'message': str(ae)},status=400)

            except Exception as e:
                  print(e)
                  return Response({'error': True, 'message': 'Something went wrong!'}, status=500)                  

class WebLogoutView(APIView):
      '''
      Unset the credentials `cookies` and make them invalid
      '''

      permission_classes = (IsAuthenticated,)

      def get(self, request):
            cres = HttpResponse(status=200)       
            cres.set_cookie('access_token', None, max_age=0, secure=True, httponly=True, samesite='Strict')
            cres.set_cookie('refresh_token', None, max_age=0, secure=True, httponly=True, samesite='Strict')
            cres.set_cookie('stale_authenticated', None, max_age=0, secure=True, httponly=False, samesite='Lax')
            return cres

            

# class SocialTokenBasedRedirectionView(APIView):

#       def post(self, request, *args, **kwargs):
#             '''
#             Request should contain proper oauth2 code redirections params
#             :code
#             :state[SocialMedia-token => decrypt(token)->profile_id,socialMedia,type]
#                   :type -> ("Login": UnsafeLoginView | "Linking")
            

#             at end it'll append a query param
#                   - response['Location'] += '?nome=' +request.GET['nome']
#             '''
#             try:
                  
#                   code = request.data.get('code', None)
#                   state = request.data.get('state', None)

#                   assert (code is not None) and (state is not None), "Invalid params!"

#                   try:

#                         data = social_token_signer.unsign_object(state)
#                         assert len(data.keys()) == 3, "Tempred params"

#                   except (BadSignature, AssertionError) as bs:
#                         logger.warning('Temepered with social token,', e)
#                         return Response({'error': True, 'message': 'state seems temprered!'},status=400)
                  
#                   else:
#                         state_type = data.get('flow_type')

#                         if(state_type == 'Login'):
#                               view = VerificationWithLoginView.as_view()
#                         elif(state_type == 'Linking'):
#                               # Will implement later
#                               view = VerificationWithLoginView.as_view()
#                         else:
#                               return Response({'error': True, 'message': 'Invalid state'},status=400)
#                         return view(request._request, *args, **kwargs)

#             except AssertionError as ae:
#                   return Response({'error': True, 'message': str(ae)},status=400)

#             except Exception as e:
#                   logger.warning('Unable to redirect social auth request')
#                   print(e)
#                   return Response({'error': True, 'message': 'Something went wrong!'},status=500)
