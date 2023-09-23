from django.urls import path
from .views import ProfileView, UploadFileView, ProfilePageView, FeedView, SocialView, PreferencesView, ContactsView, subscribe_notifications, contact_and_support, list_profiles, search_profile, validate_permissions, report_profile, validate, bookmark_profile, reach_profile, social_profile_pics, social_hit_log, analytics

urlpatterns = [
    # path('/login')
    path('profile/<int:profile_id>/', ProfilePageView.as_view(), name='profile_page_info'),
    path('profile/report/<int:target_profile_id>/', report_profile, name='report a profile'),
    path('profile/mark/<int:target_profile_id>', bookmark_profile, name='markup a profile'),
    path('profile/reach/<int:target_profile_id>/', reach_profile, name='reach_profile'), ## Default behaves as toggleView
    path('profile/contacts/', ContactsView.as_view(), name='sync_contacts'),
    path('profile/search/', search_profile, name='search profile'), # delete, post(update), get(basic_info)
    path('profile/preferences/', PreferencesView.as_view(), name='Preferences Handler'), # delete, post(update), get(basic_info)
    path('profile/list/<str:mode>/<int:unqid>/', list_profiles, name='List profiles'), # delete, post(update), get(basic_info)
    path('profile/', ProfileView.as_view(), name='profile_specific_operations'), # delete, post(update), get(basic_info)

    path('subscribe/notifications/', subscribe_notifications, name='subscribe notifications'), # delete, post(update), get(basic_info)

    path('upload/', UploadFileView.as_view(), name='upload_file_view'),

    path('feed/', FeedView.as_view(), name='poppulates feed for user'),

    path('social/profile_pics/', social_profile_pics, name='profile_social_avatars'),
    path('social/hitlog/', social_hit_log, name='Count(Hits)'),
    path('social/', SocialView.as_view(), name='socials'),

    path('analytics/<str:mode>/', analytics, name='analytics'),
    path('contact_and_support/', contact_and_support, name='contact'),

    path('validate/', validate, name='validate'),
    path('user_check_perm/', validate_permissions, name='checks if user has specific permissions'),
    # @DEPRECATED path('analytics_plans/', analytics_plans, name='Get Current Plans'),

    # path('unlock_analytics/', UnlockAnalytics.as_view(), name='UnlockAnalytics'),


    # path('login/', VerificationWithLoginView.as_view(), name='SignIn to account (after verification)'),
    # path('otp/', SendOTPView.as_view(), name='asd'),
    # '''post req fields=> mode(?social, code, state):, mode_identifier, mode_data'''
    # path('social/', SocialTokenBasedRedirectionView.as_view(), name='SocialLoginLinkingHandler'),
]