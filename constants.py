import os 

BACKEND_ROOT_URL = "http://192.168.165.153:8000"

SOCIAL_PROFILE_LINK_PREFFIXES = {
    'Instagram': 'https://www.instagram.com/',
    # 'Twitter': 'https://www.twitter.com/',
    'Facebook': 'https://www.facebook.com/',
    'Snapchat': 'https://www.snapchat.com/add/',
    'Reddit': 'https://www.reddit.com/u/',
    'Discord': 'https://discordapp.com/users/',
    'LinkedIn': 'https://www.linkedin.com/in/'
}

SOCIAL_OAUTH_LINKS = {
    'Instagram': 'https://www.instagram.com/oauth/authorize?client_id=2138701906517396&redirect_uri=https%3A%2F%2Freachout.org.in%2Fauth%2Fredirect%2F&response_type=code&scope=user_profile&platform=instaU12',
    'Snapchat': 'https://accounts.snapchat.com/accounts/oauth2/auth?client_id=cc0ab0b7-82d4-446e-bf54-9c86603c4a79&redirect_uri=https%3A%2F%2Freachout.org.in%2Fauth%2Fredirect&response_type=code&scope=https://auth.snapchat.com/oauth2/api/user.display_name https://auth.snapchat.com/oauth2/api/user.external_id https://auth.snapchat.com/oauth2/api/user.bitmoji.avatar',
    'Facebook': 'https://www.facebook.com/dialog/oauth?app_id=529831602511861&redirect_uri=https%3A%2F%2Freachout.org.in%2Fauth%2Fredirect%2F',
    # [NOTE, TODO]: when server is up on domain, check LinkedIn URL
    'LinkedIn': 'https://www.linkedin.com/oauth/v2/authorization?response_type=code&client_id=77jn18bchr2v1y&scope=r_liteprofile&redirect_uri=https%3A%2F%2Freachout.org.in%2Fauth%2Fredirect%2F',
    'Reddit': 'https://www.reddit.com/api/v1/authorize?client_id=sSPxMYHlFoqrn5flh0MNsw&response_type=code&redirect_uri=https%3A%2F%2Freachout.org.in%2Fauth%2Fredirect%2F&scope=identity&duration=permanent',
    'Discord': 'https://discord.com/oauth2/authorize?response_type=code&client_id=1059894751773597727&scope=identify&redirect_uri=https%3A%2F%2Freachout.org.in%2Fauth%2Fredirect%2F&prompt=consent'
}

OAUTH_CONFIGS = {

    'Discord': {
        'client_id': "1059894751773597727",
        'client_secret': "kL-Cu_eb3QZdLa1RBvZcH_vDr_JMzhZz",
        'redirect_uri': "https://reachout.org.in/auth/redirect/",
        'access_retrieval_endpoint': "https://discord.com/api/oauth2/token",
        'refresh_access_token_endpoint':"https://discord.com/api/v10/oauth2/token",
        'info_retrieval_endpoint': "https://discord.com/api/oauth2/@me"
    },

    'Instagram': {
        'client_id': "2138701906517396",
        'client_secret': "d57f3c828cbb0cc64080767aec663738",
        'redirect_uri': "https://reachout.org.in/auth/redirect/",
        'access_retrieval_endpoint': "https://api.instagram.com/oauth/access_token",
        'refresh_access_token_endpoint': "https://graph.instagram.com/refresh_access_token?grant_type=ig_refresh_token&access_token=%s",
        'info_retrieval_endpoint': "https://graph.instagram.com/v15.0/me?fields=id,account_type,username&access_token=%s" #Remaining
    },

    # 'Twitter': {
        # 'client_id': "TmlCeWg3Zmp5VDdmUnhtbjJQdjc6MTpjaQ",
        # 'client_secret': "9TZ_cnlCk1uDY42_zm8-V926QzbiINtrut1fMUeUhUbPGTRBCZ",
        # 'redirect_uri': "https://reachout.org.in/auth/redirect/",
        # 'access_retrieval_endpoint': "https://api.instagram.com/oauth/access_token",
        # 'info_retrieval_endpoint': "https://graph.instagram.com/v15.0/me?fields=id,account_type,username&access_token=%s" #Remaining
    # },

    'Facebook': {
        'client_id': "529831602511861",
        'client_secret': "607b4e44150b8ac1df58aee9806cc9b5",
        'refresh_access_token_endpoint':"https://www.linkedin.com/oauth/v2/accessToken",
        'access_retrieval_endpoint': "https://graph.facebook.com/oauth/access_token",
        'info_retrieval_endpoint': "https://graph.facebook.com/me?fields=id,name,picture&access_token=%s" #Remaining
    },

    'Snapchat': {
        # 'client_id': "56055847-1477-4ac7-a17a-507c322d89d1",
        'client_id': "cc0ab0b7-82d4-446e-bf54-9c86603c4a79",
        # 'client_secret': "UAI7kDuYEnesoVpCMt_u3UbxbqKEmvhOpTLf1hIaB8Y",
        'client_secret': "edpSqP3fUWObrAy_pez7VMQaIAIoRgJkx4YdX3ls4NU",
        'access_retrieval_endpoint': "https://accounts.snapchat.com/accounts/oauth2/token",
        'refresh_access_token_endpoint':"https://accounts.snapchat.com/accounts/oauth2/token",
        'info_retrieval_endpoint': "https://kit.snapchat.com/v1/me"
    },

    'Reddit': {
        'client_id': 'sSPxMYHlFoqrn5flh0MNsw',
        'client_secret': 'Wkc7I42bpRTV3eLOHI7HnmXXtFCzMw',
        'access_retrieval_endpoint': 'https://www.reddit.com/api/v1/access_token',
        'refresh_access_token_endpoint': "https://www.reddit.com/api/v1/access_token",
        'info_retrieval_endpoint': "https://oauth.reddit.com/api/v1/me"
    },

    'LinkedIn': {
        'client_id': '77jn18bchr2v1y',
        'client_secret': 'tHvyJMFNlNzQFgWs',
        'redirect_uri': 'https://www.google.com/',
        'access_retrieval_endpoint': 'https://www.linkedin.com/oauth/v2/accessToken',
        'refresh_access_token_endpoint':"https://www.linkedin.com/oauth/v2/accessToken",
        'info_retrieval_endpoint': 'https://api.linkedin.com/v2/me?projection=(id,firstName,lastName,profilePicture(displayImage~:playableStreams))'

        # Optional URL: https://api.linkedin.com/v1/people/~:(id,email-address,first-name,last-name,formatted-name,picture-url)?format=json
    },

}

SOCIAL_LINKS_PREFIXES = {

    'Discord': {
        'base_url': 'https://discordapp.com/users/%d',
        'target_field': 'profile_id'
    },
    'Instagram': {
        'base_url': 'https://instagram.com/%s',
        'target_field': 'primary'
    },
    'Reddit': {
        'base_url': 'https://www.reddit.com%s',
        'target_field': 'subreddit_url'
    },
}

SOCIAL_MEDIAS = SOCIAL_PROFILE_LINK_PREFFIXES.keys()

SOCIAL_INFO_FETCHER_BOT_NAME = "ReachOut InfoFetcher 1.0"

PROFILE_PIC_BASE_PATH = os.path.join('media', 'images', 'profile_pics')

CACHE_TYPES_LIFETIME = {
    'OTP': 60*5, # identifier: OTP:email/phone
    'WEB_SIGNIN_CODE': 60*2, # identifier: WEB_SIGNIN_CODE:profile_id
} 

OAUTH_CORE_CLIENT_ID = os.getenv('OAUTH_CORE_CLIENT_ID', 'wLePfApqei6CzBbvBqgHiuyYOmj6JpjSEWrVTuSt')
OAUTH_CORE_CLIENT_SECRET = os.getenv('OAUTH_CORE_CLIENT_SECRET', 'L6SofWPmNBvmXWiV2Baa39Nhj57raQo6BIe3wenETd1PZvtRRFUtE5njA1yiQwXtwGlUTJ1p4b7Ocx6zHX2TqG9IWcs1SvYjwZDfdnr5sKUtdfPZ7zZmy8a8Drji4oLB')

OAUTH_WEB_CLIENT_ID = os.getenv('OAUTH_WEB_CLIENT_ID', '8ox8Sy1lEjiHIARgvcUWXzHyQnEyIY1Pmu0h4B0Y')
OAUTH_WEB_CLIENT_SECRET = os.getenv('OAUTH_WEB_CLIENT_SECRET', '1lAaF2SBEin07zxtN1tQt9zReGSD6j1tDcc2ZUpXtWRs7iJHzwUAowGPk5o3Px35RM6jfkDvy4hxY4zBqsqwbdIqf9t7iAhhyY9df9lmAUPQJdkNLHlphO88v6nP8Uta')

SOCIAL_TOKEN_PROTECTOR_KEY = os.getenv('SOCIAL_TOKEN_PROTECTOR_KEY', 'mysecretprotectorKey')
SOCIAL_TOKEN_PROTECTOR_SALT = os.getenv('SOCIAL_TOKEN_PROTECTOR_SALT', 'mysecretprotectordSalt')

USERNAME_REGEX = r"^[a-zA-Z0-9]+$" #Alphanumeric Only
EMAIL_REGEX = r"^[a-zA-Z0-9.!#$%&'*+/=?^_`{|}~-]+@[a-zA-Z0-9-]+(?:\.[a-zA-Z0-9-]+)*$"
PHONE_REGEX = r"^\+\d{2,3}\s\d{5}\-\d{5}$"

TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID","AC8810f9ddb5fe0b0a61da868d38a441ca")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN","42d17df77301872f18ca7c8b33cefb8e")
TWILIO_PHONE_NO = os.getenv("TWILIO_PHONE_NO","+15095120906")

PAYPAL_CONFIG = {
    'CLIENT_ID': "ASlAoLEU-UqcfUceKTXaJoSN7RNr3uQEEXbUl-EveheEAsfsZvuS9cYZw969PzgM9jgT1U9G9SxRyFns",
    'SECRET_KEY': 'EGRFIICOA9cmV8F2yzIVsXtCLMVLGUPZlGi1uPgQqMTPewWfdcLHlIWi-WVAuWfeCaSph60Xu4BLG6yD',
    'BASE_URL': {
        'SANDBOX': 'https://api-m.sandbox.paypal.com',
        'PRODUCTION': 'https://api-m.paypal.com'
    }
}


ANALYTICS = {
    'MAX_AGE': 30,
    'TIME_STAMP_THRESHOLD': {
        'IMPRESSIONS': 10, # Every increase of 10 impressions it logs a timestamp
        'PROFILE_VIEWS': 5, # Every increase of 5 profile_views it logs a timestamp
        'REPORTS': 3, # Every increase of 3 reports it logs a timestamp
    }
}

IPINFO_TOKEN = os.getenv("IPINFO_TOKEN", "c48d9147f45dc8")

UPLOAD_FILE_KEYS_WHITELIST = ['images:profile_pic'] # In future, Contact-Us form's key can be added
# type:key_name
# +21 12345-67890

FEED_PAGE_SIZE = 5

# Below constraint contains the price as key in (INR)[Major]
# Currently only 2 offers
'''
LAST USD UPDATED: 21-May-2023
'''
# ANALYTICS_PLANS = [
#     {
#         'duration_in_days': 28,
#         'amount_in_inr': 19.00,
#         'amount_in_usd': 0.35, # []Convertion rate: 82USD + FOERIGN_ADDON(10Rs)
#         'tag': None
#     },
#     {
#         'duration_in_days': 84,
#         'amount_in_inr': 49.00,
#         'amount_in_usd': 0.75,
#         'tag': 'Suggested'
#     },
#     {
#         'duration_in_days': 180,
#         'amount_in_inr': 99.00,
#         'amount_in_usd': 1.29,
#         'tag': None
#     },
# ]

EMAIL_EMOJI_URL = {
    'hello': "https://i.pinimg.com/originals/4a/c9/0c/4ac90cad81d288bd43ce60edee0cda8a.png",
    'secret': "https://i.pinimg.com/originals/f7/48/65/f7486544efba0ff199aab69e9199fb3f.png",
    'success': "https://i.pinimg.com/originals/e7/99/23/e799236620478af54dc106cd89589cf8.png",
    'confuse': "https://i.pinimg.com/originals/bf/81/5b/bf815beabe03f8d5f22a681e7b5f9dae.png",
    'idea': "https://i.pinimg.com/originals/fa/6c/1a/fa6c1a1481a7187552d460e1099c83ec.png"
}

EMAIL_BASIC_STRUCTURE = ('''
		
		<div style="padding: 10px 15px 15px 15px;transform: rotateZ(45deg);position: relative;color: white;background-color: #59CE8F">
			<div>
				<img style="position: absolute;top: -65px" height="100" width="100" src="%s" />
			</div>
			<div style="padding: 6px 10px;color: #59CE8F;background-color: white;border-radius: 5px;display: inline-block;font-weight: 900;display: flex;align-items: center;gap: 1.5rem;font-size: 1.3rem">
                <img style="border-radius: 8px" src="https://i.pinimg.com/originals/ee/18/c6/ee18c626711eb9c3f816b1ba3300b9b4.png" width="38" height="38" />
                &nbsp;&nbsp;
                <div>
                    <span>Heya there,</span>
                    <br/>
                    <b style="font-size: 0.85rem;font-weight: 500">Mate</b>
                </div>
			</div>
			<br/>
            %s
			<b><pre style="text-align: right">~ Team Reachout</pre></b>
            <br/>
			<a href="https://reachout.org.in/docs/terms_and_conditions" style="font-size: 0.8rem;color: black">Terms</a>
			<b>&#183;</b>&nbsp;<a href="https://reachout.org.in/docs/policy" style="font-size: 0.8rem;color: black">Policy</a>
			<b>&#183;</b>&nbsp;<a href="https://reachout.org.in/contact" style="font-size: 0.8rem;color: black">Contact/Support</a>
		</div>
''')
