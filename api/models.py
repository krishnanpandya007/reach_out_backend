from django.db import models, connection
from django.contrib.postgres.fields import ArrayField
from logging import getLogger

# from django.conf import settings

# import sys, os
# if(settings.BASE_DIR not in sys.path): sys.path.append(settings.BASE_DIR)
from auth2.models import Profile
from constants import FEED_PAGE_SIZE, ContactStatus

logger = getLogger(__name__)
# Create your models here.


class Recommendation(models.Model):

    target_profile = models.ForeignKey(Profile, on_delete=models.CASCADE)
    recommendation_type = models.CharField(max_length=8, null=False, blank=False) # standard|nearme
    recommendation_profiles = ArrayField(base_field=models.BigIntegerField(), default=list, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def recommendations(self):
        return Profile.objects.filter(pk__in=self.custom_fetch())

    def custom_fetch(self, page_size:int=FEED_PAGE_SIZE, update_on_fetch:bool=True) -> list:
        '''

        :page_size       - number of objects needs to be fetched from recommendation
        :update_on_fetch - either updates the array of recommendations after fething objects or not

        @returns List[Int]: array of `recommended profile ids`

        '''

        rec_profile_ids = self.recommendation_profiles 
        print("HelloPopulatingRecomendations")
        print(rec_profile_ids)
        # First need to check if we have enough ids to fulfill recommendation quantity
        if(len(self.recommendation_profiles) <= FEED_PAGE_SIZE):
            self.poppulate_recommendations()

        ids = rec_profile_ids[:page_size]

        if(update_on_fetch):
            rec_profile_ids = rec_profile_ids[page_size:]

        self.save()

        return ids

    def poppulate_recommendations(self):

        '''
        makes recommendation as given/set mode (standard|nearme)
        '''
        print('Poppulating recommendations')
        with connection.cursor() as cur:
            _recommendation_fn = 'get_u2u_global_score' if self.recommendation_type == 'standard' else 'get_u2u_local_score'
            try:
                cur.execute(f"select iter.id as profile_id ,{_recommendation_fn}({self.target_profile.pk},iter.id::int) as score from auth2_profile iter where iter.id != {self.target_profile.pk} and iter.is_staff=false order by score desc;")
                ids = [rec_res[0] for rec_res in cur.fetchall() if int(rec_res[1]) != -1]
                print(f"Fetched ids for recommendations from direct DB [Purely]", ids)
                self.recommendation_profiles = ids
            except Exception as e:
                logger.critical('Error Making recommandations', exc_info=str(e))

    def save(self, *args, **kwargs):
        if not self.pk:
            # On Creation of new object// => Make recommendation and save it!
            
            self.poppulate_recommendations()


        super(Recommendation, self).save(*args, **kwargs)

# @sync constants.py
CURRENT_STATUS_LIST = (
   ('Untouched', 'Untouched'),
   ('In-Progress', 'In-Progress'),
   ('Completed', 'Completed')
)

class Contact(models.Model):

    # TODO: name.@max_length constraint doesn't synced with frontend currently 
    # TODO:  - nor everyone.@required
    # TODO: need to add @method trace_path.validator syntax to trace_path
    # TODO: need to add @method trace_path.validator min_length 1 to trace_path

    email = models.EmailField(null=False, blank=False, unique=False)
    name = models.CharField(null=False, max_length=150, blank=False, unique=False)
    detail = models.TextField(null=False, blank=False, unique=False)
    trace_path = models.CharField(max_length=255, blank=False, null=False, unique=False)
    status = models.CharField(choices=CURRENT_STATUS_LIST, default=ContactStatus.untouched, max_length=15)

    def __str__(self):
        status = '⚪' if self.status == 'Untouched' else ( '🔴' if self.status == 'In-Progress' else '🟢')
        return status + "" + self.trace_path.split('.')[-1] + ' —' + self.name
