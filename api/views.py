from django.db.models import F, Case, When
from django.core.exceptions import ValidationError
from django.core.signing import Signer, BadSignature
from django.conf import settings
from glob import glob
from django.core.mail import send_mail
from shutil import move as shutil_move
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser, FileUploadParser
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAdminUser
from auth2.permissions import UserHaveUnlockedAnalytics
from rest_framework.decorators import permission_classes, api_view
from rest_framework.response import Response
from oauth2_provider.views import TokenView # For logging in users
from geopy.geocoders import Nominatim
# from .models import Profile, Phone, Social
from twilio.rest import Client
import logging
from hashlib import sha256
from itertools import islice
from re import match as regex_match
import sys, os
if(settings.BASE_DIR not in sys.path): sys.path.append(settings.BASE_DIR)

from .predictor import predict_standard_posts, predict_engage_posts 
from auth2.models import Profile, Phone, AnalyticProfile, Social, Preference
from api.models import Recommendation
from global_utils.models import NotProvided
from auth2.serializers import ProfilePageSerializer, ProfileSerializer, ProfilePreferencesSerializer
from constants import UPLOAD_FILE_KEYS_WHITELIST, DEFAULT_CLIENT_COUNTRY_CODE, SOCIAL_THRESHOLD_UPDATE_DURATION, PROFILE_PREFERENCES_CONFIG, SOCIAL_MEDIAS, IPINFO_TOKEN, BACKEND_ROOT_URL, ANALYTICS, SEARCH_PAGE_SIZE
from global_utils.functions import get_client_ip, format_phone_number, remove_filename_extention, get_ip_info, parse_data_from_ips
from global_utils.decorators import memcache
from scripts.credentials_fetcher import get_social_access_token, get_social_user_data
from django.db.models.functions import Now
from django.utils import timezone
from django.db import transaction
from django.contrib.postgres.search import TrigramSimilarity
from .task import handle_follower_notification, handle_social_tap_notification
from reach_out_backend.settings import executor


from yake import KeywordExtractor
language = "en"
max_ngram_size = 1
deduplication_threshold = 0.9
numOfKeywords = 5 # Will generate max 5 tags for each profile
custom_kw_extractor = KeywordExtractor(lan=language, n=max_ngram_size, dedupLim=deduplication_threshold, top=numOfKeywords, features=None)

geolocator = Nominatim(user_agent="reach_out")

class ProfileView(APIView):

    permission_classes = (IsAuthenticated,)

    def get(self, request):

        try:

            profile = request.user
            print('Getting:', profile.safe_profile_pic_url)

            info = {
                'profileId': profile.pk,
                'name': profile.get_full_name(),
                'bio': profile.bio,
                'profilePicUrl': profile.safe_profile_pic_url,
                'touch_ups': profile.touch_ups
            }

            # profile.raw_ip = get_client_ip(request)

            return Response({'error': False, 'message': 'Profile Info retrieved!', **info}, status=200)

        except Exception as e:
                logging.info(f"{self.__class__.__name__}:[OUTER_EXC]:", e)
                return Response({'error': True, 'message': 'Something went wrong!'},status=500)

    def put(self, request):

        '''
        For updating fields in profile
        ex. profilePicUrl,name,bio
        '''

        try:

            profile_pic_url = request.data.get('profilePicUrl', NotProvided)
            name = request.data.get('name', NotProvided)
            bio = request.data.get('bio', NotProvided)

            assert not (isinstance(profile_pic_url, NotProvided) and isinstance(name, NotProvided) and isinstance(bio, NotProvided)), "Provide fields to update"
            assert (name.count(' ') == 1 if isinstance(name, str) else True), "Provide valid name"

            profile:Profile = request.user
            print('aa')

            if(isinstance(profile_pic_url, str)):
                '''
                RESUME:
                '''
                profile_pic_url = profile_pic_url.replace(BACKEND_ROOT_URL, '')
                if(profile_pic_url.startswith(settings.MEDIA_URL)):
                    print('aaa')
                    # It is uploaded file
                    try:

                        new_profile_pic_url = profile_pic_url.replace('uploads', 'profile_pics').replace('profile_pic__', '').split('?')[0]
                        abs_path = os.path.join(settings.BASE_DIR.resolve().as_posix(), *(profile_pic_url.split('?')[0]).split('/'))
                        try:

                            # CleanUp files with same aliases
                            match_files = glob(os.path.join(settings.BASE_DIR.resolve().as_posix(), remove_filename_extention(new_profile_pic_url) + '.*'))
                            print('matching_files:', match_files)
                            print(settings.BASE_DIR.resolve().as_posix() / (remove_filename_extention(new_profile_pic_url) + '.*'))
                            for target_file in match_files: os.remove(target_file)
                        except Exception as e:
                            print('Flck:WasteManagement Failed:', e)
                            pass

                        shutil_move(abs_path, abs_path.replace('uploads', 'profile_pics').replace('profile_pic__', ''))
                        print('if::', new_profile_pic_url)
                        profile.profilePicUrl = new_profile_pic_url
                        # After this time to clear up profile_pics stales
                    except Exception as e:
                        print("ASD", e)
                        return Response({'error': False, 'message': 'Error while updating profilePicUrl'},status=500)
                else:
                    # TODO: Anyhow verify the domains of imgURL within whitelisted socials
                    new_profile_pic_url = profile_pic_url.replace('uploads', 'profile_pics').replace('profile_pic__', '').split('?')[0]
                    print('else:', new_profile_pic_url, profile_pic_url)
                    profile.profilePicUrl = new_profile_pic_url

            if(isinstance(name, str)):
                f_name, l_name = name.split(' ') if isinstance(name, str) else [None, None]
                profile.first_name = f_name
                profile.last_name = l_name

            if(isinstance(bio, str)):
                profile.bio = bio
                # Now we'll add predicted tags for given BIO, sync with DB
                if(isinstance(bio, str) and bio.count(' ') >= 3):
                    keywords = [tag_info[0] for tag_info in custom_kw_extractor.extract_keywords(bio)]
                    analytics_obj = profile.analytics
                    analytics_obj.predicted_tags = keywords
                    analytics_obj.save()

            # profile.raw_ip = get_client_ip(request)
            print('final:', profile.safe_profile_pic_url)
            updated_data = {
                'name': profile.get_full_name(),
                'bio': profile.bio,
                'profilePicUrl': profile.safe_profile_pic_url
            }

            profile.save()

            return Response({'error': False, 'message': 'Profile edited!', **updated_data}, status=201)

        except ValueError as ve:
            return Response(data={'error': True,'message': ve.messages[0]}, status=400)

        except AssertionError as ae:
            return Response({'error': True, 'message': str(ae)},status=400)

        except Exception as e:
                logging.info(f"{self.__class__.__name__}:[OUTER_EXC]:", e)
                return Response({'error': True, 'message': 'Something went wrong!'},status=500)

    def delete(self, request):

        '''
        WARNING: BACHHE DUR RHE
        '''

        try:

            profile:Profile = request.user

            # profile.raw_ip = get_client_ip(request)
            profile.save()

            assert False, "Currently, it's disabled to remove your profile."

            profile.delete()

            return Response({'error': False, 'message': 'Profile deleted! we\'ll miss you ;('}, status=201)

        except Exception as e:
                logging.info(f"{self.__class__.__name__}:[OUTER_EXC]:", e)
                return Response({'error': True, 'message': 'Something went wrong!'},status=500)

class ProfilePageView(APIView):

    permission_classes = (AllowAny,)

    def get(self, request, *args, **kwargs):

        try:

            profile_id = kwargs.get('profile_id', None)
            log_mode = request.GET.get('log', 'on') # if 'off' doesnt affect Analytics

            assert profile_id, "Provide valid profile id"

            profile = Profile.objects.get(pk=profile_id)

            if(log_mode != 'off'):
                if(request.user.is_authenticated and request.user.pk != profile.pk and (request.user.analytics.self_point is not None)):
                    # If user loads its own profile, we dont wanna count it
                    # Log to `analytics` about profile views
                    analytics = profile.analytics
                    analytics.profile_views.add(request.user.analytics.self_point)
                    if(analytics.profile_views.count() % ANALYTICS['TIME_STAMP_THRESHOLD']['PROFILE_VIEWS'] == 0):
                        for timestamp in analytics.profile_views_timestamps:
                            if(timestamp < (timezone.now() - timezone.timedelta(days=ANALYTICS['MAX_AGE']))):
                                analytics.profile_views_timestamps.remove(timestamp)
                            else:
                                break
                        # Every 10 impressions we note a TimeStamp for building graph
                        analytics.profile_views_timestamps.append(timezone.now())

                    analytics.save()

            serializer = ProfilePageSerializer(profile, many=False)
            print('aah:', serializer.data)

            return Response({'error': False, 'message': 'Profile Page retrieved!', **serializer.data}, status=200)            
            
        except Profile.DoesNotExist:
            return Response({'error': True, 'message': 'Profile not found'}, status=404)        

        except AssertionError as ae:
            return Response({'error': True, 'message': str(ae)},status=400)        

        except Exception as e:
            logging.info(f"{self.__class__.__name__}:[OUTER_EXC]:", e)
            return Response({'error': True, 'message': 'Something went wrong!'}, status=500)        

class UploadFileView(APIView):

    '''

    @AssetManager

    handles to store uploaded files by user,
    other non-file information will be discarded!

    format: http://localhost:8000/api/upload/?key=images:profile_pic&identifier=2
            - payload has to be in `multipart/form-data`
            - specifically, the target file has to be present in `upload_file` key in that formData

    @param @required `key`
    @param @required `identifier`

    [OPTIONAL]Architecture: 
        - accepts a unique `key` (has to be whitelisted) ex. `profile_pic`
        - accepts an `identifier` ex.. 2(has to be unique per `key` group/model)
        
        evaluating both => (profile_pic/2)
            ~ creates uploads/images/profile_pic

        Descr: reason behind this, if user re-uploads another profile_pic it saves to same destination as it's old one,
               so no new_file created and follows space utilization
               +
               In future, if people try to overuse this public resource, we'll create hash for `identifier` to make it less exposed as public resource
               NOTE: this is currently followed

    '''

    permission_classes = (AllowAny,)
    parser_classes = (MultiPartParser,FormParser)

    def post(self, request, *args, **kwargs):
        try:

            key = request.GET.get('key', None)
            identifier = request.GET.get('identifier', None)

            assert (key and identifier), "Provide proper `key` and `identifier` params"
            assert (len(identifier) < 255), "`identifier` too long!" # It's blueprinted to have filename < 255 chars.
            assert (key in UPLOAD_FILE_KEYS_WHITELIST), "`key` not whitelisted!"
            upload_file = request.FILES.getlist('upload_file')
            assert (len(upload_file) == 1), "One file uploadation is necessary"
            upload_file = upload_file[0]
            assert (upload_file.size < 8388608), "File size must be less than 8 MB"
            extention = upload_file.content_type.split('/')[-1]
            # assert extention
            # suzume
            identifier_hash = sha256(bytes(identifier, 'utf-8')).hexdigest()

            file_type, key = key.split(':')
            relative_path_folder = os.path.join("media", file_type, 'uploads')
            relative_path = os.path.join("media", file_type, 'uploads', key + '__' + identifier_hash + '.' + extention)
            upload_path = os.path.join(settings.BASE_DIR, relative_path)                     
            # Using Pattern matching algo. to make finding same fileNames faster
            # TODO: use {os.sep} to seperate paths
            '''
            # On changing the image URL, use this script to delete other extention
            Lets first clear same aliases files
            '''
            match_files = glob(os.path.join(settings.BASE_DIR, relative_path_folder) + f'\{key}__{identifier_hash}.*')
            for target_file in match_files: os.remove(target_file)
            fil = open(upload_path, 'wb')
            fil.write(upload_file.read())
            fil.close()
            # print('Before')

            return Response({'error': False, 'message': 'File Uploaded!', 'upload_path': '/' + relative_path.replace('\\', '/')}, status=201)

        except AssertionError as ae:
            print("reason::", ae)
            return Response({'error': True, 'message': str(ae)},status=400)

        except Exception as e:
                logging.info(f"{self.__class__.__name__}:[OUTER_EXC]:", e)
                return Response({'error': True, 'message': 'Something went wrong!'},status=500)

class FeedView(APIView):
    '''
    BRR!!! this is advanced kind of stuff. so if you scared even by assignments deadlines, Don't touch it😂
    
    Besides that: 
        - In future if we want to allow unauthenticated users to take advantage of it, make a `get` method and remove permission_classess bearer also add auth_check in `post`

    '''

    permission_classes = (IsAuthenticated,)

    def get(self, request, *args, **kwargs):
        
        try:

            # page_size = request.GET.get('page_size', None)
            feed_type = request.GET.get('feed_type', 'standard')
            log_mode = request.GET.get('log', 'on') # Log the request, if 'off' provided itll not update analytics
    
            '''
            TODO: let page_size matter in recommendations
            '''

            # assert (feed_type and page_size) and isinstance(page_size, int) and isinstance(feed_type, str), "`page_size`:Integer `feed_type`:String aren't mentioned properly in params"
            assert (feed_type in ['standard', 'nearme']), "provide valid `feed_type` param"

            user_profile = request.user

            recommender, _ = Recommendation.objects.get_or_create(target_profile=user_profile, recommendation_type=feed_type)

            recommended_profiles = recommender.recommendations

            # Time to increase these profile's impressions
            try:

                # Updating 5 queries one by one + Retrieving 5 entries joined to profile + each time network bandwidth is used!
                # is expensieve operation. instead, using atomicity approach to make 1 commit (transactional)

                if(log_mode != 'off'):


                    # Let's find associated analytics profile then update it
                    profile_analytics = [profile.analytics for profile in list(recommended_profiles)]

                    for analytics in profile_analytics:

                        analytics.impressions += 1
                        if(analytics.impressions % ANALYTICS['TIME_STAMP_THRESHOLD']['IMPRESSIONS'] == 0):
                            # Removing older Records than 30 days
                            for timestamp in analytics.impressions_timestamps:
                                if(timestamp < (timezone.now() - timezone.timedelta(days=ANALYTICS['MAX_AGE']))):
                                    analytics.impressions_timestamps.remove(timestamp)
                                else:
                                    break
                            # Every 10 impressions we note a TimeStamp for building graph
                            analytics.impressions_timestamps.append(timezone.now())


                    AnalyticProfile.objects.bulk_update(profile_analytics, ['impressions', 'impressions_timestamps'])


                '''
                TODO: Make proper updation query
                '''

                # AnalyticProfile.objects.filter(profile__pk__in=[profile.pk for profile in recommended_profiles]).update(impressions=F('impressions')+1, impressions_timestamps=Case(
                #     When(impressions=F('impressions') - (F('impressions')%10), then=[*F('impressions_timestamps'), Now()]),
                #     default=F('impressions_timestamps')
                # ))             
                
            except Exception as e:
                print("LOL", e)
                pass

            serialized_profiles = ProfileSerializer(recommended_profiles, many=True, context={'profile_id': user_profile.pk})

            return Response({'error': False, 'message': 'Feed retrieved!', 'profile_cards': serialized_profiles.data}, status=200)

        except AssertionError as ae:
            return Response({'error': True, 'message': str(ae)},status=400)

        except Exception as e:
                logging.info(f"{self.__class__.__name__}:[OUTER_EXC]:", e)
                return Response({'error': True, 'message': 'Something went wrong!'},status=500)
        
@api_view(['POST'])
@permission_classes([IsAuthenticated,])
def subscribe_notifications(request):
    try:

        fcm_token = request.data.get('fcm_token', None)

        assert isinstance(fcm_token, str), "Fcm token has to be `str` instance"

        preference = request.user.prefs

        preference.notifications['fcm_token'] = fcm_token

        preference.save()

        return Response({'error': False, 'message': 'Subscribe from this device'},status=200)
    
    except AssertionError as ae:
        return Response({'error': True, 'message': str(ae)},status=400)

    except Exception:
        return Response({'error': True, 'message': 'Something went wrong 😔'},status=500) 

@api_view(['GET'])
@permission_classes([IsAuthenticated,])
def report_profile(request, *args, **kwargs):

    try:

        target_profile_id = kwargs.get('target_profile_id', -1)
        log_mode = request.GET.get('log', 'on') # if 'off' doesn't affect Analytics

        assert target_profile_id > 0, "profile Id must be positive valid integer"

        target_profile = Profile.objects.get(pk=target_profile_id)

        profile = request.user

        if(log_mode != 'off'):
            if(request.user.is_authenticated and request.user.pk != profile.pk and (request.user.analytics.self_point is not None)):
                # If user loads its own profile, we dont wanna count it
                # Log to `analytics` about profile views
                analytics = profile.analytics
                analytics.reports.add(request.user.analytics.self_point)
                if(analytics.reports.count() % ANALYTICS['TIME_STAMP_THRESHOLD']['REPORTS'] == 0):
                    for timestamp in analytics.reports_timestamps:
                        if(timestamp < (timezone.now() - timezone.timedelta(days=ANALYTICS['MAX_AGE']))):
                            analytics.reports_timestamps.remove(timestamp)
                        else:
                            break
                    # Every 10 impressions we note a TimeStamp for building graph
                    analytics.reports_timestamps.append(timezone.now())

                analytics.save()

        target_profile_analytics = target_profile.analytics
        target_profile_analytics.reports.add(profile.analytics.self_point)
        target_profile_analytics.save()

        return Response({'error': False, 'message': 'Profile Reported 👍🏻'}, status=201)        

    except Profile.DoesNotExist:
        return Response({'error': True, 'message': 'Profile not found'}, status=404)        

    except AssertionError as ae:
        return Response({'error': True, 'message': str(ae)},status=400)

    except Exception:
        return Response({'error': True, 'message': 'Something went wrong 😔'},status=500)

@api_view(['GET'])
@permission_classes([IsAuthenticated,])
def bookmark_profile(request, *args, **kwargs):

    '''
    @multi_success_response 201(added) | 200(removed)
    This is toggle behaved view.
    if profile is already bookmarked, then it removes otherwise it
    '''

    try:

        target_profile_id = kwargs.get('target_profile_id', -1)
        assert_action = request.GET.get('assert_action', None) # mark/un-mark

        assert target_profile_id > 0, "profile Id must be positive valid integer"
        assert assert_action in ['mark', 'un-mark', None], 'Invalid `assert_acton` param' 

        target_profile = Profile.objects.get(pk=target_profile_id)

        profile:Profile = request.user

        if(profile.marks.contains(target_profile)):
            if(assert_action == 'mark'): return Response({'error': False, 'message': 'Bookmark added'}, status=201)        
       
            profile.marks.remove(target_profile)
            return Response({'error': False, 'message': 'Bookmark removed'}, status=200)        

        else:
            if(assert_action == 'un-mark'): return Response({'error': False, 'message': 'Bookmark removed'}, status=200)
            profile.marks.add(target_profile)
            return Response({'error': False, 'message': 'Bookmark added'}, status=201)        


    except Profile.DoesNotExist:
        return Response({'error': True, 'message': 'Profile not found'}, status=404)        

    except AssertionError as ae:
        return Response({'error': True, 'message': str(ae)},status=400)

    except Exception:
        return Response({'error': True, 'message': 'Something went wrong!'},status=500)

@api_view(['GET'])
@permission_classes([IsAuthenticated,])
def reach_profile(request, *args, **kwargs):

    '''
    @multi_success_response 201(reach) | 200(un-reach)
    This is toggle behaved view.
    if profile is already reached, then it removes otherwise it'll add
    '''

    try:

        target_profile_id = kwargs.get('target_profile_id', -1)
        assert_action = request.GET.get('assert_action', None) # reach/un-reach

        assert target_profile_id > 0, "profile Id must be positive valid integer"
        assert assert_action in ['reach', 'un-reach'] if assert_action else True, 'Invalid `assert_acton` param' 

        profile:Profile = request.user
        assert target_profile_id != profile.pk, "SELF_REACH_NOT_ALLOWED" # specific code tells frontend to diplay app. msg

        target_profile = Profile.objects.get(pk=target_profile_id)


        if(target_profile.reachers.contains(profile)):
            if(assert_action == 'reach'): return Response({'error': False, 'message': 'Reached!'}, status=201)        
            target_profile.reachers.remove(profile)
            return Response({'error': False, 'message': 'Removed Reach!'}, status=200)        

        else:
            if(assert_action == 'un-reach'): return Response({'error': False, 'message': 'removed Reach!'}, status=200)
            target_profile.reachers.add(profile)
            
            try:

                executor.submit(handle_follower_notification, target_profile, target_uid=target_profile_id, reacher_uid=profile.pk, reacher_name=profile.get_full_name())

            except Exception as e:

                logging.error(f"{self.__class__.__name__}:[OUTER_EXC][HANDLING_NOTIFICATION]:", e)
                pass

            return Response({'error': False, 'message': 'Profile Reached!'}, status=201)        


    except Profile.DoesNotExist:
        return Response({'error': True, 'message': 'Profile not found'}, status=404)        

    except AssertionError as ae:
        print("ASDASD:", ae)
        return Response({'error': True, 'message': str(ae)},status=400)

    except Exception:
        return Response({'error': True, 'message': 'Something went wrong!'},status=500)

@api_view(['GET'])
@permission_classes([IsAuthenticated,])
def social_profile_pics(request, *args, **kwargs):

    try:

        profile = request.user

        '''
        Update the stale profilePicUrl(s) which may stopped working
        '''
        print('Aha::')

        target_social_medias = list(profile.socials.all())
        # for social in target_social_medias:

        #     if(social.last_updated == None or social.last_updated < timezone.now() - timezone.timedelta(**SOCIAL_THRESHOLD_UPDATE_DURATION)):

        #         if(social in ['Facebook', 'Instagram']):
        #             '''
        #             Meta companies uses rotative profile_pic_url(s)
        #             which refreshes every n interval, at the result its impossible to store that img
        #             '''
        #             res = get_social_user_data(social.socialMedia, social.access_token, rotate_token=social.rotate_token, sync_model=social)
        #             if(res['error'] == False):
        #                 # Update last_updated
        #                 social.last_updated = timezone.now()
        #                 social.save()
        #             else:
        #                 # Something error occured while syncing data
        #                 social.relogin_required = True
        #                 target_social_medias.remove(social)
        #                 social.save()
                    
        #                 print(social.rotate_token, social.access_token)
        #                 # Something went wrong so we can't send half updated, half stale data
        #                 # So deprecating both and handling as an error occured
        #                 return Response({'error': True, 'message': 'Something went wrong!'},status=500)

        media_to_avatars = dict()

        for social in list(target_social_medias):

            media_to_avatars[social.socialMedia] = social.safe_avatar

        return Response({'error': False, 'message': 'linked social avatars retrieved', 'profilePics': media_to_avatars}, status=200)

    except Exception as e:
        print(e)
        return Response({'error': True, 'message': 'Something went wrong!'},status=500)

class ContactsView(APIView):

    '''
    On-[GET]: if (contacts_synced) ? shows un-followed profiles to the user from contacts.
    On-[POST]: sync(s) contacts of that user.
    '''

    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):

        try:

            profiles:list = []

            profile = request.user

            # First check if contacts are synced or not
            assert profile.synced_contacts, "First sync the contacts!"

            # Filter contacts which is not reached by user
            contacts_profiles = Profile.objects.filter(analytics__contacts__target_profile__isnull=False)
            reached_profiles = [p.pk for p in list(profile.reached_profiles.all())]

            for contact_profile in list(contacts_profiles):
                if not (contact_profile.pk in reached_profiles):
                    profiles.append({'profile_id': contact_profile.pk, 'profile_name': contact_profile.get_full_name(), 'profile_pic_url': contact_profile.safe_profile_pic_url, 'phone_no': contact_profile.phone.number})

            return Response({'error': False, 'message': 'Contact\'s profiles are retrieved successfully!', 'contact_profiles': profiles}, status=200)

        except AssertionError as ae:
            print('ae')
            print(ae)

            return Response({'error': True, 'message': str(ae)},status=400)

        except Exception as e:
            print('ae')
            print(e)
            return Response({'error': True, 'message': 'Something went wrong!'},status=500)


            

    def put(self, request, *args, **kwargs):

        try:
            contacts:dict = request.data

            batch_size = 100
            contact_entries = list()
            
            for contact_raw_name, contact_number in contacts.items():
                formatted_number = format_phone_number(contact_number)
                if(not Phone.objects.filter(number=formatted_number).exists() and ()):
                    contact_entries.append(Phone(number=formatted_number, raw_name=contact_raw_name))

            # Sorting phones
            contact_entries.sort(key=lambda number_obj: number_obj.number)

            # Removing duplicates
            for contact_entry_idx in range(len(contact_entries)):
                if(contact_entry_idx > 0):
                    # check for prev. elemnt; if same ignore
                    if(contact_entries[contact_entry_idx] == contact_entries[contact_entry_idx - 1]):
                        # remove it
                        contact_entries.remove(contact_entries[contact_entry_idx])

            print('Now Entries: ', contact_entries)

            profile = request.user
            analytics = profile.analytics
            while True:

                batch = list(islice(contact_entries, batch_size))

                if not batch:
                    break

                objs = Phone.objects.bulk_create(batch, batch_size)
                analytics.contacts.add(*objs)

            profile.synced_contacts = True
            profile.save()

            analytics.save()

            return Response({'error': False, 'message': "Contacts synced!"}, status=201)

        except AssertionError as ae:
            return Response({'error': True, 'message': str(ae)},status=400)

        except Exception as e:
            print("EDDD")
            print(e)
            return Response({'error': True, 'message': 'Something went wrong!'},status=500)

@api_view(['POST'])
@permission_classes([IsAuthenticated,])
def social_hit_log(request):

    try:

        target_profile_id = request.data.get('tp_id')
        target_socialMedia = request.data.get('ts_label')
        silent = request.data.get('silent', False)

        assert target_socialMedia in SOCIAL_MEDIAS, "invalid Media"
        assert isinstance(target_profile_id, int), "Invalid tp_id"

        target_profile = Profile.objects.get(pk=target_profile_id)

        social = target_profile.get_social(target_socialMedia)

        user_point = request.user.analytics.self_point if (request.user.analytics) and (request.user.analytics.self_point is not None) else False 

        if(user_point):
            social.hits.add(user_point)
            social.save()

        if(silent != 'true'):

            try:

                executor.submit(handle_social_tap_notification, target_profile, target_uid=target_profile_id, tapper_uid=request.user.pk, tapper_name=request.user.get_full_name(), social_platform=target_socialMedia)

            except Exception as e:

                logging.error(f"[OUTER_EXC][HANDLING_NOTIFICATION]:", e)
                pass

        return Response({'error': False, 'message': 'Logged'}, status=201)

    except (Profile.DoesNotExist):
        return Response({'error': True, 'message': 'Profile not found'}, status=404)        

    except AssertionError as ae:
        return Response({'error': True, 'message': str(ae)},status=400)

    except Exception:
        return Response({'error': True, 'message': 'Something went wrong!'},status=500)

class SocialView(APIView):

    permission_classes = (IsAuthenticated,)

    def get(self, request):

        try:

            profile = request.user

            socials = profile.socials.all()
            not_linked_socials = list(filter(lambda social: social not in [s.socialMedia for s in list(socials)],SOCIAL_MEDIAS))

            socials_data = [{'social': social.socialMedia, 'relogin_required': social.relogin_required, 'handle_id': social.name, 'linked': True} for social in list(socials)]
            socials_data += [{'social': socialMedia, 'linked': False} for socialMedia in not_linked_socials]

            print(socials_data)
            return Response({'error': False, 'message': 'Retrieved social status!', 'socials': socials_data}, status=200)

        except AssertionError as ae:
            return Response({'error': True, 'message': str(ae)},status=400)

        except Exception:
            return Response({'error': True, 'message': 'Something went wrong!'},status=500)

    def put(self, request):

        try:

            platform = request.GET.get('platform', None)
            print(request.user.pk)
            assert platform in SOCIAL_MEDIAS, "Invalid social media"
            target_social_media = request.user.socials.filter(socialMedia=platform)
            assert target_social_media.exists(), f"{platform} social handle not linked to your profile"
            target_social_media = target_social_media.first()
            res = get_social_user_data(platform, target_social_media.access_token, rotate_token=target_social_media.rotate_token, sync_model=target_social_media)

            if(res['error']):
                  print('Ono')
                  # Come/Goes direct to APK
                  return Response({'error': True, 'message': 'Something went wrong!', 'relogin_required': res.get('relogin_required', False)}, status=500)
                  
            return Response({'error': False, 'message': 'Social Updated!'}, status=201)


        except AssertionError as ae:
            return Response({'error': True, 'message': str(ae)},status=400)

        except Exception as e:
            print("Aram se ono", e)
            return Response({'error': True, 'message': 'Something went wrong!'},status=500)

class PreferencesView(APIView):

    permission_classes = (IsAuthenticated,)

    def get(self, request):

        try:

            profile = request.user

            pref = Preference.objects.get(profile=profile)

            pref_serializer = ProfilePreferencesSerializer(pref)

            return Response({'error': False, 'message': 'Retrieved social status!', 'prefs': pref_serializer.data}, status=200)

        except AssertionError as ae:
            print('ahaha', ae)
            return Response({'error': True, 'message': str(ae)},status=400)

        except Exception as e:
            print('Something Error:', e)
            return Response({'error': True, 'message': 'Something went wrong!'},status=500)

    def put(self, request):

        try:

            preference_name = request.data.get('preference_name', None)

            assert preference_name.upper() in PROFILE_PREFERENCES_CONFIG.keys(), "Invalid preference"

            new_preferences = request.data.get('prefs')

            assert isinstance(new_preferences, dict), "Invalid prefs."

            profile_pref = Preference.objects.get(profile = request.user)

            setattr(profile_pref, preference_name.lower(), new_preferences)

            profile_pref.save()

            return Response({
                'error': False,
                'message': 'Preferences updated!'
            }, status=201)
        
        except Exception as e:
            print("PREF_UPDATION_FAIL", e)
            return Response({'error': True, 'message': 'Something went wrong!'},status=500)

@api_view(['GET'])
@permission_classes([IsAuthenticated,UserHaveUnlockedAnalytics])
def analytics(request, *args, **kwargs):
# '''

# TODO:FRONTEND-snackbar user if he is not authenticated(Redirect LoginBars) -> not has_unlocked_analytics(Redirect Plans)

# '''
    try:

        analytics_mode = kwargs.get('mode', None)

        if not (analytics_mode in ['stats', 'graph', 'geo']):
            return Response(status=404)
        
        profile = request.user
        analytics = profile.analytics
        print(analytics)

        assert bool(analytics), "Looks like analytics aren't subscribed yet!" 

        if(analytics_mode == 'stats'):

            stats_data = {
                'impressions': {'total': analytics.impressions, 'this_month': len(analytics.impressions_timestamps)*10},
                'profile_views': {'total': analytics.profile_views.count(), 'this_month': len(analytics.profile_views_timestamps)*10},
                'reports': {'total': analytics.reports.count(), 'this_month': len(analytics.reports_timestamps)*10},
                'bookmarkers': profile.marked_by.count(),
                'social_stats': {social.socialMedia: social.hits.count() for social in list(profile.socials.all())},
                'extracted_tags': analytics.predicted_tags,

                # Below are other properties, show em and show a way to fixem (nextTime Login with these to verify associated field)
                'email_verified': profile.email_verified,
                'phone_verified': profile.phone.number_verified if hasattr(profile, 'phone') else None,
            }
            return Response(stats_data, status=200)

        elif (analytics_mode == 'graph'):
            
            

            '''
            Build current timstamp with current number of impressions and plot with `current_week` mode as default from frontend
            as backend we just send data for a month
            '''

            # TODO: First calculate the needed params then the way to get it

            graph_type = request.GET.get('type', 'impressions')

            assert graph_type in ['impressions', 'profile_views', 'reports'], "Invalid `graph_type`"

            # Show full details of this month
            initial_data = [{'name': f"Day {i+1}"} for i in range(7*4)] 
            raw_scores = {} #[[day, score]]
            timestamps = getattr(analytics, f"{graph_type}_timestamps")

            if(len(timestamps) < 2):
                return Response({'error': True, 'message': f'Atleast {ANALYTICS["TIME_STAMP_THRESHOLD"][graph_type.upper()]*2} {graph_type} required to track it\'s graphical analysis'}, status=400)

            unit = float('inf')
            max_diff = -1

            for i in range(1, len(timestamps)):
                diff_in_hours = (timestamps[i] - timestamps[i-1]).total_seconds()/3600
                day = (28 - (timezone.now() - timestamps[i]).days) # gets day of that week_1
                if(raw_scores.get(day, False)):
                    raw_scores[day] += diff_in_hours
                else:
                    raw_scores[day] = diff_in_hours
                unit = min(unit, diff_in_hours)
                max_diff = max(max_diff, diff_in_hours)

            max_diff += 1 #  
            for day, raw_score in raw_scores.items():
                initial_data[day-1]['all_time'] = (max_diff/unit) - (raw_score/unit) # setting the score

            return Response(initial_data, status=200)                
        
        else:
            '''
            LIGHT DOCS:
            res = p('https://ipinfo.io/batch?token=c48d9147f45dc8', json=['8.8.4.4/loc'])
            results into
            {'8.8.4.4/loc': '37.4056,-122.0775'} as res.json()

            view_permission=p.objects.get(codename='view_analyticprofile')
            profile.objects.last().user_permissions.add(view_permission)
            r.objects.last().has_perm('auth2.view_analyticprofile')
            '''
            graph_type = request.GET.get('type', 'profile_views') # profile_views, reports, socials

            assert graph_type in ['profile_views', 'reports', 'social_taps'], "Invalid `graph_type`"

            data = {}

            if(graph_type == 'social_taps'):
                data = {}
                socials = request.user.socials.all()

                for social in socials:
                    data[social.socialMedia] = list(social.hits.values_list('ip', flat=True))

                # Now convert ips into lat longs
                # TODO: Build optimized arch. for retrieving and presenting to frontend
                for media_name, ips in data.items():
                    data[media_name] = {}
                    data[media_name]['cor'] = parse_data_from_ips(ips) # [ [lat_ip1, long_ip1], [lat_ip2, long_ip2], ... ]
                # {Instagram: {cor: [[1, 2], [3, 4]], area: }}
                    # Disabling the area-labeling feature

                    # data[media_name]['area'] = [', '.join([(j,l) for j,l in geolocator.reverse(','.join(g)).raw.items() if j in ['country', 'city', 'state']]) for g in data[media_name]['cor']]
            else:
                query_set = getattr(request.user.analytics, graph_type)
                ips = list(query_set.values_list('ip', flat=True))

                # convert ips into lat,long (s)


                data['cor'] = parse_data_from_ips(ips)
                # NOTE: Adding location Area labeling is expensieve+time consuming relative to server, hence disabled for now. 
                # But, can be on-turned by activating below lines

                # data['area'] = []
                # for lat_lon in data['cor']:
                #     print("Before")
                #     # print("asdasddsaadsadsdsaadsadsads:", ', '.join(lat_lon))
                #     print("After")

                #     d = geolocator.reverse(', '.join(str(h) for h in lat_lon))

                #     print("D:", d)
                #     d = d.raw
                #     print("D:", d)

                #     data['area'].append(', '.join([d['address'].get('city', 'village'), d['address']['state'], d['address']['country']]))

            return Response(data, status=200)
    
    except AssertionError as ae:
        print("Something dont wrong")
        return Response({'error': True, 'message': str(ae)},status=400)

    except Exception as e:
        print("asdasd", e)
        return Response({'error': True, 'message': 'Something went wrong!'},status=500)



@api_view(['POST'])
@permission_classes([AllowAny,])
def validate(request):
    try:

        platform = request.data.get('platform')
        profile_link = request.data.get('key') # will get the username

        assert platform in ['LinkedIn', 'Snapchat', 'Facebook'], "Invalid platform"

        if(platform == 'Snapchat'):
            profile_link = f'https://snapchat.com/add/{profile_link}'

        profile_link_exists = Social.objects.filter(socialMedia=platform, profile_link=profile_link).exists()

        assert not profile_link_exists, 'Profile link exists already!'

        return Response({'error': False, 'message': 'Profile link doesn\'t exists'}, status=200)

    except AssertionError as ae:
        print("Something dont wrong")
        return Response({'error': True, 'message': str(ae)},status=400)

    except Exception as e:
        print("asdasd", e)
        return Response({'error': True, 'message': 'Something went wrong!'},status=500)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def validate_permissions(request):

    '''
    :Explicit view

    First user needs to be authenticated in order to verify given permissions.

    So if you only need to check if user is authenticated or not, try excluding `perms` param from URL.
    
    This view, specifically check either user have certain permissions or not.
        - However return response can't be customizable from request.
        - Returns either 200 / 403 / (basic_error_status_codes)
    '''

    try:

        perms = request.GET.get('perms', '') # comma seperated permissions 
        
        # This permissions also needs to include pre-defined permission check + explicit checks
        # Pre-defined permissions Ex. user.has_perm('app_name.perm_label') Identified by having '.' in-between
        # Explicit checks needs to be handled by custom if-else blocks
        perms = perms.split(',')
        

        for permission_label in perms:

            #checking for pre-defined permissions
            if ('.' in permission_label):
                if(not request.user.has_perm(permission_label)):
                    return Response({'error': True, 'message': 'Lack of permission!', 'code': f'access_denied {permission_label}'}, status=403)
            
            # explicit permissions handling
            if(permission_label == 'has_unlocked_analytics'):
                if(not request.user.has_analysis_unlocked):
                    return Response({'error': True, 'message': 'Authenticated but not authorized!', 'code': f'access_denied {permission_label}'}, status=403)

        return Response({'error': False, 'message': 'Permission holds.'}, status=200)

    except AssertionError as ae:
        print("Something dont wrong")
        return Response({'error': True, 'message': str(ae)},status=400)

    except Exception as e:
        print("asdasd", e)
        return Response({'error': True, 'message': 'Something went wrong!'},status=500)
    
@api_view(['GET'])
@permission_classes([IsAuthenticated,])
def search_profile(request):

    try:

        query = request.GET.get('query', None)

        sorted_profiles = Profile.objects.all()

        filtered_profiles = [profile for profile in sorted_profiles.annotate(similarity=TrigramSimilarity('username', query)).order_by('-similarity')][:100]   

        serialized_profiles = ProfileSerializer(filtered_profiles, many=True, context={'profile_id': request.user.pk})

        return Response({
            'error': False,
            'message': 'Plans retrieved!',
            'profile_cards': serialized_profiles.data
        }, status=200)

    except Exception as e:
        print("PlanRetrievingFailed", e)
        return Response({'error': True, 'message': 'Something went wrong!'},status=500)

@api_view(['GET'])
@permission_classes([AllowAny,])
def list_profiles(request, *args, **kwargs):

    try:
        list_mode = kwargs.get('mode', False)
        unique_id = kwargs.get('unqid', False)

        '''
        Reason behind replication of whitelisted labels and not giving direct orm properties access instead is 
        this view is public and some of it can be private (un-shared)
        '''
        assert list_mode in ['followers'], "Invalid `mode`"

        target_profile = Profile.objects.get(pk=unique_id)

        data = None

        match(list_mode):

            case 'followers':
                 
                 followers = [{'profile_id': ac.pk, 'name': ac.get_full_name(), 'profile_pic_url': ac.safe_profile_pic_url} for ac in target_profile.reachers.all()]

                 data = followers

        return Response({'error': False, 'message': 'Successfully retrieved list of profiles', list_mode: data}, status=200)

    except (Profile.DoesNotExist):
        return Response({'error': True, 'message': 'Profile not found'}, status=404)        

    except AssertionError as ae:
        return Response({'error': True, 'message': str(ae)},status=400)

    except Exception:
        return Response({'error': True, 'message': 'Something went wrong!'},status=500)