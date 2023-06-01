'''
TODO: CONTANT SQL QUERIES
'''
from django.http import QueryDict
from django.conf import settings
import os, sys
if(settings.BASE_DIR not in sys.path): sys.path.append(settings.BASE_DIR)
from auth2.models import Profile

'''
TODO: VIEWS TO RETRIEVE FROM QUERIES

2 types
    - standard (for you)
    - engage (enlarge network) (TEMP)

'''

def predict_standard_posts(counter:int=0, chunk_size:int=5) -> QueryDict | None:

    try:
        # See this snippet: Person.objects.raw('SELECT id, first_name, last_name, birth_date FROM myapp_person')
        # Currently returning gibbrish| Will implement this mech. later!!
        return Profile.objects.all()[counter*chunk_size:chunk_size*(counter+1)]

    except Exception:

        return None

# As off now blueprint is provided in above snippet
predict_engage_posts = predict_standard_posts
