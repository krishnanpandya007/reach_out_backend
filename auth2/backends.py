from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from re import match as regex_match
from sys import path
from os import getcwd
path.append(getcwd())

from auth2.models import Phone
from constants import USERNAME_REGEX,EMAIL_REGEX, PHONE_REGEX

User = get_user_model()


class ProfileBackend(ModelBackend):

    def authenticate(self, request, username=None, password=None):

        '''
        @param password: Secret Code given to staff members
        '''

        try:

            user = None
            if (regex_match(USERNAME_REGEX, username)):

                user = User.objects.get(username=username)
                                

            elif (regex_match(EMAIL_REGEX, username)):

                user = User.objects.get(email=username)
                

            elif (regex_match(PHONE_REGEX, username)):
                phone = Phone.objects.get(number=username)
                user = phone.target_profile

            # # Invalid identifier not any of (username, email, phone_no)
            # return None

            
        except User.DoesNotExist:
            return None 

        else:

            if(user.is_staff):
                print("checking")
                success = user.check_password(password)
                return user if success else None
            return user


