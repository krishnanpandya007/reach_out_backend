from django.http import HttpResponse
from json import dumps
from django.conf import settings
from constants import SOCIAL_TOKEN_PROTECTOR_KEY, SOCIAL_TOKEN_PROTECTOR_SALT
from django.core.signing import Signer
import sys
if(settings.BASE_DIR not in sys.path): sys.path.append(settings.BASE_DIR)


refresh_token_signer = Signer(SOCIAL_TOKEN_PROTECTOR_KEY, salt=SOCIAL_TOKEN_PROTECTOR_SALT)

class WebAuthMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        is_web_client = request.META.get('HTTP_RAW_PLATFORM', None) == 'Web'

        if(not is_web_client):
            return self.get_response(request)
        access_token = request.COOKIES.get('access_token')
        if(access_token):
            request.META['HTTP_AUTHORIZATION'] = f"Bearer {access_token}"

        response = self.get_response(request)

        '''
        Alright, if also after excecuting the response, we got 401 that means AccessToken is invalid so handling that also
        By invalidating all tokens and setting code to REQUIRED_RELOGIN
        '''

        if(response.status_code == 401):
            refresh_token = request.COOKIES.get('refresh_token')
            if(refresh_token):
                return HttpResponse(dumps({'error': True, 'message': 'Unauthorized', 'refresh': refresh_token_signer.sign_object({'ref': refresh_token}), 'code': 'ROTATE_ACCESS'}), status=401)

            cres = HttpResponse(dumps({'error': True, 'message': 'Unauthorized', 'code': 'REQUIRED_RELOGIN'}), status=401)       
            cres.set_cookie('access_token', None, max_age=0, secure=True, httponly=True, samesite='Lax')
            cres.set_cookie('refresh_token', None, max_age=0, secure=True, httponly=True, samesite='Lax')
            cres.set_cookie('stale_authenticated', None, max_age=0, secure=True, httponly=False, samesite='Lax')
            return cres


        return response