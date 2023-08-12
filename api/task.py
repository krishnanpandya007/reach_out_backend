import firebase_admin
from firebase_admin import credentials
from firebase_admin import messaging
from global_utils.decorators import memcache

# Initialize the Firebase Admin SDK
cred = credentials.Certificate('C:\\Users\\krishnan\\reachoutd\\daily\\reachout_firebase_creds.json')
firebase_admin.initialize_app(cred)

def handle_follower_notification(target_profile, target_uid:int=None, reacher_uid:int=None, reacher_name:str='ReachOut user'):
    '''
    Sends the notification to the end user if user has subscribed to notifications realted to 'new_follower' topic.
    TODO: Slow-Down: 1.1Minute [SLOWDOWN_FOLLOWER:(krishnan).id = (ayush).id, 2minute]
    '''    
    preference = target_profile.prefs

    # Enable slowdown

    target_is_on_slowdown = memcache.get('SLOWDOWN_FOLLOWER', target_uid)

    if(target_is_on_slowdown == str(reacher_uid)):
        return
    
    if(preference.notifications['new_follower'] == True and (preference.notifications['fcm_token'])):
        # User has subscribed to this catagory, continue to send notification
        try:
            message = messaging.Message(
                notification=messaging.Notification(
                    title=f'{reacher_name} followed you!',
                    body='Tap to view their profile.'
                ),
                token=preference.notifications['fcm_token'],
                data={'type': 'new_follower', 'follower_id': f"{reacher_uid}", 'click_action': 'FLUTTER_NOTIFICATION_CLICK'}
            )

            # Send the message
            response = messaging.send(message)

            # Only enable slowdown if notification sent successfully!
            if(response and (target_is_on_slowdown != str(reacher_uid))):
                # Send notification but trigger slowdown after
                memcache.manual_set('SLOWDOWN_FOLLOWER', target_uid, reacher_uid)

        except Exception as e:
            print('ERROR_SENDING_NOTIFICATION:FOLLOWER', e)

def handle_social_tap_notification(target_profile, target_uid:int=None, tapper_uid:int=None, social_platform:str=None, tapper_name:str='ReachOut user'):
    '''
    Sends the notification to the end user if user has subscribed to notifications realted to 'social_tap' topic.
    TODO: Slow-Down: 2H [SLOWDOWN_SOCIAL_TAP:(krishnan).id = true, 2minute]
    '''    
    preference = target_profile.prefs

    # Enable slowdown

    target_is_on_slowdown = memcache.get('SLOWDOWN_SOCIAL_TAP', str(target_uid))

    if(target_is_on_slowdown == 'true'):
        return
    
    if(preference.notifications['social_tap'] == True and (preference.notifications['fcm_token'])):
        # User has subscribed to this catagory, continue to send notification
        try:
            message = messaging.Message(
                notification=messaging.Notification(
                    title=f'{tapper_name} checked your {social_platform} handle!',
                    body='Tap to view their profile.'
                ),
                token=preference.notifications['fcm_token'],
                data={'type': 'social_tap', 'tapper_id': f"{tapper_uid}", 'click_action': 'FLUTTER_NOTIFICATION_CLICK'}
            )

            # Send the message
            response = messaging.send(message)

            # Only enable slowdown if notification sent successfully!
            if(response and (target_is_on_slowdown != 'true')):
                # Send notification but trigger slowdown after
                memcache.manual_set('SLOWDOWN_SOCIAL_TAP', str(target_uid), 'true')

        except Exception as e:
            print('ERROR_SENDING_NOTIFICATION:SOCIAL_TAP', e)


