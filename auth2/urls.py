from django.urls import path
from .views import SignUpView, VerificationWithLoginView, SendOTPView, SocialConnectionUrlBuilderView, UpdateAccessTokenView, WebSignInView, WebLogoutView, create_login_qr_session, listen_login_qr_session, resolve_login_qr_session, destroy_login_qr_session, generate_qr_data

urlpatterns = [
    # path('/login')
    path('signup/', SignUpView.as_view(), name='Signup a new account'),
    path('login/', VerificationWithLoginView.as_view(), name='SignIn to account (after verification)'),
    path('otp/', SendOTPView.as_view(), name='asd'),
    path('social_connection_url/', SocialConnectionUrlBuilderView.as_view(), name='returns social connection url'),
    path('update_access_token/', UpdateAccessTokenView.as_view(), name='returns updated access token'),
    path('web/login/', WebSignInView.as_view(), name='Web signIn'),
    path('web/logout/', WebLogoutView.as_view(), name='Web Logout'),

    path('login_qr_session/create/', create_login_qr_session, name='Create Login Qr Session'),
    path('login_qr_session/listen/<str:session_id>/', listen_login_qr_session, name='Listen to QR session'),
    path('login_qr_session/resolve/<str:session_id>/', resolve_login_qr_session, name='Resolve QR session'),
    path('login_qr_session/qr/<str:session_id>/', generate_qr_data, name='Generate QR data'),
    path('login_qr_session/terminate/<str:session_id>/', destroy_login_qr_session, name='Destroy Login QR session'),


    # '''post req fields=> mode(?social, code, state):, mode_identifier, mode_data'''
    # path('social/', SocialTokenBasedRedirectionView.as_view(), name='SocialLoginLinkingHandler'),
]