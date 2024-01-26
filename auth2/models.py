from django.db import models
from os import getcwd, getenv
from sys import path
from django.contrib.auth.models import AbstractUser,BaseUserManager
from django.contrib.postgres.fields import ArrayField
from django.contrib.auth import authenticate
from django.core.validators import RegexValidator
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django.utils.timezone import timedelta, now, datetime, make_aware, get_default_timezone
from django.conf import settings
# from django.contrib.auth import get_user_model
from re import match
path.append(getcwd())

from constants import PROFILE_PREFERENCES_CONFIG, USERNAME_REGEX,EMAIL_REGEX, PHONE_REGEX, BACKEND_ROOT_URL


class Social(models.Model):

    # Yes, we are retrieving the access token from providerSocialMedia but just to differenciate the accounts and fetch profile_Links
    # We can have further informations in future if needed

    '''
    TODO: [SOCIAL_TASK] => implement refresh_access_token method (generally) ✅
    After back to current link, verification of login for social Platform(views.py)
    TODO: While linking check for double-linking same social media to 1 profile ❎

    2. On save check if duplicate handleId on provided SocialMedia
    '''
    profile = models.ForeignKey('Profile', on_delete=models.PROTECT, related_name='socials', null=True, blank=True, editable=True)
    socialMedia = models.CharField(max_length=15, unique=False)
    handleId = models.CharField(max_length=50)
    highlighted = models.BooleanField(default=False)

    access_token = models.TextField(max_length=500, null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    refresh_token = models.TextField(max_length=500, null=True, blank=True) # expires after around 2 months
    # tokens_updated_at = models.DateField(null=True, blank=True)
    relogin_required = models.BooleanField(default=False) # If we've detected code 400 on socialInteraction views
    hits = models.ManyToManyField('ProfilePoint', blank=True)
    profile_link = models.URLField(max_length=150, null=True, blank=True)
    profilePicUrl = models.CharField(max_length=500,null=True, blank=True) # Secondary
    name = models.CharField(max_length=100) # Primary
    last_updated = models.DateTimeField(auto_now_add=True, null=True, blank=True)

    @property
    def safe_avatar(self):
        return self.profilePicUrl if self.profilePicUrl.startswith('http') else (BACKEND_ROOT_URL + self.profilePicUrl)

    @property
    def rotate_token(self):
        if(self.socialMedia in ['Facebook', 'Instagram']):
            '''
            For these platform we need access_token (long_lived) in order to refresh token 
            '''
            return self.access_token
        return self.refresh_token



'''
Forms.py
from django.core.exceptions import ValidationError

class YourForm(UserCreationForm):

    def clean(self):
       email = self.cleaned_data.get('email')
       if User.objects.filter(email=email).exists():
            raise ValidationError("Email exists")
       return self.cleaned_data
'''


class Profile(AbstractUser):

    # @point returns predected `ProfilePoint` instance  
    # @phone returns `Phone` instance 
    # @analytics returns `AnalyticProfile` instance 
    # @socials returns `Social`s
    # @prefs returns `Preference`
    # NOTE: by setting, raw_ip property, it'll update position on ProfilePoint 

    '''
    on creation, AnalyticProfile instance in `create()` method
               , ProfilePoint instance at it 

    '''

    username = models.CharField(_('username'), max_length=30, unique=False,
        help_text=_('Required. 30 characters or fewer. Letters, digits and '
                    '@/./+/-/_ only.'),
        validators=[
            RegexValidator(USERNAME_REGEX,
                                      _('Enter a valid username. '
                                        'This value may contain only letters, numbers '
                                        ), 'invalid'),
        ],
        error_messages={
            'unique': _("Pick another username."),
        })
    first_name = models.CharField(_("first name"), max_length=150, null=False, blank=False)
    last_name = models.CharField(_("last name"), max_length=150, null=False,blank=False)
    email = models.EmailField(unique=True, validators = [RegexValidator(
                        regex = EMAIL_REGEX,
                        message = 'Email must has to be valid.',
                        code='invalid_email'
                    )],
        error_messages={
            'unique': _("Email taken."),
            'invalid': _("Provide valid email."), 
        }) 
    email_verified = models.BooleanField(default=False)
    bio = models.CharField(max_length=100, unique=False, null=True, blank=True)
    profilePicUrl = models.CharField(max_length=150,unique=False, null=True, blank=True) #null means AnonymousProfilePic
    synced_contacts = models.BooleanField(default=False)
    reachers = models.ManyToManyField('Profile', blank=True, related_name='reached_profiles')
    marks = models.ManyToManyField('Profile', blank=True, related_name='marked_by')
    analysis_unlocked_at = models.DateTimeField(blank=True, null=True) # SubscriptionBoughtAt
    analysis_unlock_duration = models.PositiveSmallIntegerField(blank=True, default=21) # NumberInDays

    last_seen = models.DateTimeField(null=True, blank=True)


    @property
    def has_analysis_unlocked(self) -> None:
        # Also have to invalidate the expired properties
        '''
        NOTE: In development-mode we letting it unlimited access
        '''
        if(settings.DEBUG):
            return True
        else:
            if(self.analysis_unlocked_at == None):
                return False

            if((self.analysis_unlocked_at + timedelta(days=self.analysis_unlock_duration)) <= now()):
                return True
            else:
                # Time to clear expired property value
                self.analysis_unlocked_at = None
                self.analysis_unlock_duration = 21
                self.save()
                return False

    def full_clean(self, *args, **kwargs) -> None:
            
        super().full_clean(*args, **kwargs)

        try:

            if(self.phone):
                # phone `reversedField` exists for current instance
                pass
            
        except Exception as e:
            # phone argument not provided, raise validation error
            raise ValidationError(_('Please provide `phone` field'), code='required')

        # Cleaned now try to create phoneNo by cleaning it also
        # Here if above raised exception, we dont create Phone Model otherwise we are creating

    @property
    def safe_profile_pic_url(self):
        return ((BACKEND_ROOT_URL + self.profilePicUrl) if not self.profilePicUrl.startswith('http') else self.profilePicUrl) if self.profilePicUrl is not None else (BACKEND_ROOT_URL + '/media/images/profile_pics/anonymous.png')

    @property
    def touch_ups(self):
        '''
        Blueprinted tokens which are recognizable by frontend/app
            - `link_social` (If user hasn't linked any socials)
            - `add_avatar` (If user's profile_pic is eql to anonymous one)
            - `add_bio` (If user's bio is empty or null)
        '''

        touch_ups_stack = []

        # Checking for `link_social`
        if(len(self.socials.all()) == 0):
            touch_ups_stack.append('link_social')

        # Checking for `add_avatar`
        if((self.profilePicUrl == None) or (self.profilePicUrl == (BACKEND_ROOT_URL + '/media/images/profile_pics/anonymous.png'))):
            touch_ups_stack.append('add_avatar')

        # Checking for `add_bio`
        if((self.bio == None) or not (self.bio)):
            touch_ups_stack.append('add_bio')

        return touch_ups_stack        

    def get_social(self, social_media=None):
        if(social_media == None):
            return Social.objects.filter(profile=self.pk)
        else:
            return Social.objects.get(profile=self.pk, socialMedia=social_media)

    def save(self, *args, **kwargs):
        self.set_unusable_password()
        
        # self.
        if not self.pk:
            # First time, generate username and then check for validation
            if(not self.is_staff):
                self.username = self.first_name.lower() + self.last_name.lower()
                self.full_clean()

            else:
                self.username = 'staff_' + self.first_name.lower() + self.last_name.lower()
        
        super(Profile, self).save(*args, **kwargs)
        '''
        [SIGNAL_ACTIVED]
        ex.. 1. [IF_CREATED] Edit username to username+id
             2. [IF ATTR raw_ip] Create profilePoint
             3. [IF CREATED] create AnalyticProfile
        '''

    def check_password(self, given_password:str) -> bool:

        if(not self.is_staff):
            return True
        from hashlib import sha512
        m = sha512()
        m.update(bytes(self.username,'utf-8'))
        m.update(bytes(getenv('STAFF_PASSWORD_TRANSACTION_KEY', 'vn36DIW!N*Zn2&$nh!rZ3A&k3CykzLE2PpC5QfNBjyq^%2WYF9'),'utf-8'))
        return m.hexdigest() == given_password


class ProfilePoint(models.Model):

    # @analytics returns parent `AnalyticProfile` 
    # @viewed returns QuerySet of Analyticprofile(s) which .profile has viewed
    profile = models.OneToOneField(Profile, on_delete=models.PROTECT, related_name='point')
    ip = models.GenericIPAddressField()
    city = models.CharField(max_length=100, null=True, blank=True)
    updated_at = models.DateField(auto_now=True)

    # make a property, activeness: range from 1 to 5


class AnalyticProfile(models.Model):

    profile = models.OneToOneField(Profile, on_delete=models.CASCADE, related_name='analytics')
    impressions = models.PositiveBigIntegerField(default=0) # ProfileCardViews
    impressions_timestamps = ArrayField(models.DateTimeField(), default=list, null=True, blank=True)
    self_point = models.OneToOneField(ProfilePoint, on_delete=models.PROTECT, related_name="analytics", null=True, blank=True) # its added_at shows last_updated date
    predicted_tags = ArrayField(models.CharField(max_length=20), default=list, null=True, blank=True)
       
    profile_views = models.ManyToManyField(ProfilePoint, related_name='viewed')
    profile_views_timestamps = ArrayField(models.DateTimeField(), default=list, null=True, blank=True)

    contacts = models.ManyToManyField('Phone', related_name='contact_in')
    reports = models.ManyToManyField(ProfilePoint)
    reports_timestamps = ArrayField(models.DateTimeField(), default=list, null=True, blank=True)

    
def validate_notifications(val:dict):
    if(type(val) != 'dict'):
        raise ValidationError(
            _("%(value)s isn't a dict instance."),
            params={"value": val},
        )
    for key in PROFILE_PREFERENCES_CONFIG['NOTIFICATIONS']['REQUIRED_KEYS']:
        if(key not in val.keys()):
            raise ValidationError(
                _("%(value)s, a required key isn't mentioned/included."),
                params={"value": key},
            )    

class Preference(models.Model):

    profile = models.OneToOneField(Profile, on_delete=models.CASCADE, related_name='prefs')
    notifications = models.JSONField(default=PROFILE_PREFERENCES_CONFIG['NOTIFICATIONS']['DEFAULT'],validators=[validate_notifications])
    
    # In future, its easy to add other pref(s) here in this model
    # Ex.. email-pref(s)

class Phone(models.Model):

    # @contact_in returns which AnalyticProfile has added this instance to it!
    # if target_profile points to null value, means this number is of unIdentified user (AnonymousUser)
    target_profile = models.OneToOneField(Profile, on_delete=models.PROTECT, related_name='phone', null=True, blank=True, editable=True)
    raw_name = models.CharField(max_length=50, null=True, blank=True)
    number = models.CharField(max_length=16, validators=[RegexValidator(
                        regex = PHONE_REGEX,
                        message = 'Phone number must be valid.',
                        code='invalid_phone'
                    )],
        error_messages={
            'unique': _("Phone number registered already!"),
            'invalid_phone': _("Provide proper phone number format!"),
        }, null=False, blank=False, unique=True)
    number_verified = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        
        self.full_clean()
        super(Phone, self).save(*args, **kwargs)

'''
class AnonymousPhoneNo(models.Model):

--If this(anonymous) user signups in future let backlink profile notify about him/her

    @optional backlinks = models.ManyToManyField(Profile,Profile,...)
    phoneNo = models.TextField(max_length=15,null=True, blank=True)

'''

# @sync global_utils/functions.py detect_platform_from_user_agent()
AVAILABLE_LOGIN_PLATFORMS = (
   ('Web', 'web'),
   ('Android', 'android'),
   ('Ios', 'ios'),
   ('Unknown', 'unknown')
)

class LoginHistory(models.Model):
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='login_history')
    client_ip = models.GenericIPAddressField(null=False, blank=False)
    agent = models.CharField(max_length=200, null=False, blank=False)
    detected_platform = models.CharField(choices=AVAILABLE_LOGIN_PLATFORMS, null=False, blank=False, max_length=10)
    logged_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-logged_at']

    @property
    def get_catagorized_stats(self):
        print('------------')
        stats =  dict()

        general_counts = 0
        general_logged_at = make_aware(datetime(year=2003, month=9, day=19), get_default_timezone()) # Any Date before publishing

        for platform in AVAILABLE_LOGIN_PLATFORMS:

            platform_name = platform[1]

            platform_logins = LoginHistory.objects.filter(profile=self.profile, detected_platform=platform_name)
            
            counts = platform_logins.count()

            general_counts += counts

            general_logged_at = max(general_logged_at, platform_logins.first().logged_at if platform_logins.exists() else general_logged_at)

            stats[platform[0]] = {
                "count": counts,
                "logged_at": platform_logins.first().logged_at if platform_logins.exists() else '—'
            } 

        stats["general/total"] = {
            "count": general_counts,
            "logged_at": general_logged_at
        }
        print("DEBUG::", stats)
        return stats


    def __str__(self):
        return self.profile.get_full_name() + f" ({self.detected_platform}) : " + str(self.client_ip)


class RawSnap(models.Model):

    snap_type = models.CharField(max_length=45, unique=False) # Ex.. RedditAuthResponse
    snap_key = models.CharField(max_length=20, unique=False) # Ex user_id:23 | SocialAccountId:34 | InstagramUsername:krishnanpandya
    snap_data = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

# def social_login(code, state):
#     [_, social, __] = decode_state(state)
#     access = await fetch_access(platform=social,code)
#     user_state = await fetch_user_info(access)
#     # we check that if we have user_state.id in records if it is then we login the associated user and get access and refresh token and send back to user along with BasicUserInfo
#     User(puid)[social] = user_state.id
