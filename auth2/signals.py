from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from auth2.models import Profile, ProfilePoint, AnalyticProfile, Preference
import logging

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Profile, dispatch_uid='post_save_order')
def init_sub_models_on_profile_save(sender, instance, created, **kwargs):
    '''
    1. [NEW_CREATION]?  username = username+=self.pk
    '''
    logging.debug(f'[{created = }]')

    try:

        if(created):
            instance.username = (instance.first_name + instance.last_name).lower() + str(instance.pk)
            instance.save()

    except Exception as e:
        logger.warning('Unable to update username', e)

    '''
    2. AddUp a new profilePoint
    '''
    _point:ProfilePoint = None

    try:
        if(hasattr(instance, 'raw_ip')):

            point, _ = ProfilePoint.objects.get_or_create(profile=instance, defaults={'ip': instance.raw_ip})
            point.save()

            _point = point
    except Exception as e:
        logger.warning('Unable to update IP for profile', e)
    '''
    3. Create AnalyticProfile
    '''
    
    if(created):
        try:
            a_p, a_p_created = AnalyticProfile.objects.get_or_create(profile=instance)
            if(_point):
                a_p.self_point = _point
            a_p.save()

        except Exception as e:
            logger.warning('Unable to create/update AnalyticProfile', e)


    '''
    4. Create preferences model
    '''

    if(created):
        Preference.objects.create(profile=instance)
    




