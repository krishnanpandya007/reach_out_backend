from django.db import models
# Create your models here.

WHITELISTED_CONSTRAINTS_FAMILIES = [
    ('active_users', 'Active Users'),
    ('recently_active_users', 'Recently Active Users'),
    ('active_qr_sessions', "Active QR sessions")
]

class Constraint(models.Model):
    '''
    This model specifically stands for storing single values (ex.. average user time)
    family: average_user_time,
    handle: {
        'value': 12.0,
        ...extras?
        'value_in'?: 'minutes'
    }
    added_at: Date 

    +------------------+
    |  bla bla bla(s)  |
    +------------------+
    * This model specifically used to store results for any analytics job.

    * The reason behind putting entire JSON field cover just for 'value' key is that we dont know the datatype it supposed to be hold.
      Ex there is average_time: Date, poppular_user: number, poppular_label: string etc... + if we want to hold relevant sub-contraints, we can
    '''
    family = models.CharField(max_length=50, unique=False, choices=WHITELISTED_CONSTRAINTS_FAMILIES) # Name of constraint
    handle = models.JSONField(default=dict)
    added_at = models.DateTimeField(auto_now_add=True)

    def get_family_members(self, addon_filters:dict) -> models.QuerySet:
        '''
        @returns:  previous values with same name along with time_stamps
        addon_filter? = {'added_at__gte': '12-03-2023'}
        '''
        similar_constraints = Constraint.objects.filter(family=self.family, **addon_filters)
        return similar_constraints
    
    class Meta:
        ordering = ['-added_at']
    


