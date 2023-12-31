from django.utils import timezone 
from django.conf import settings
import sys
if(settings.BASE_DIR not in sys.path): sys.path.append(settings.BASE_DIR)
from global_utils.functions import get_client_ip
from constants import TRACE_URL_PREFIXES

class UserStatsUpdationMiddleware:

    '''
    1. Updates Client_IP
    2. Updates Last Seen of user/client
    '''

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):

        response = self.get_response(request)

        if(len(request.path.split('/')) > 0 or request.path.split('/')[0] not in TRACE_URL_PREFIXES):
            # Only tracing whitelisted paths
            return response
        try:
            current_user = request.user
            if request.user.is_authenticated:
                now = timezone.now()
                current_user.raw_ip = get_client_ip(request)
                current_user.last_seen = now
                current_user.save()
        except Exception as e:
            # Maybe we ran out of limit, or xyz reasons raise error
            print('Unable to log: api/middleware.py/UserStatsUpdationMiddleware: ', e)
            pass

        return response
