from credentials_fetcher import get_social_access_token, get_social_user_data, refresh_social_access_token
import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "reach_out_backend.settings")

import django
django.setup()

from django.core.management import call_command


response = get_social_access_token('Instagram', "AQCjRf_5jOkfoVXGZ0yKIO1BMtyVsmA5bK0WpXeg5uAF3K1UAqYGAw8PVS7Xukdl3Y-F1NR-0E9nXkWZB0jlyCLFbV4TIRKyOA8HPtC5-_CfN2fz1iECJZqIGeVWVR-Hf6zipqapgwcTOIWPeUR1cmBW1tzQS-HRi26hUjODW7vt7Fg9uEdZfrFIN3YN3Jml6to7rxz3ZfQdLAresaRYOGx1_kma5GcQ6Q6zzBvEM2qshQ")

rotate_response = refresh_social_access_token('Instagram', "")

if(True):

    access_token = response.get('access_token')
    # access_token = "EAAHh4Qh1XZCUBANZA8AIZCKIwdFVOcLoCNoW4xkA397qzBdswAajxnPH2zUCTSAEhmyBCMyc8Vq2ZBMohOFBW2QSBzxuacLkMBJ9xQyBF1IrDyNCEQD7FOSGvJtCabqFZCtYKYHkZAFwNydYcMje4d0P3yyMzg4hoiOEB7ZCLooWQZDZD"
    print('AccessToken: ', access_token)
    print("Returner:", get_social_user_data("Instagram", access_token))

