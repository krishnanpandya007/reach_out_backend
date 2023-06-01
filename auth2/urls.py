from django.urls import path
from .views import SignUpView, VerificationWithLoginView, SendOTPView, SocialConnectionUrlBuilderView, UpdateAccessTokenView, WebSignInView, WebLogoutView

urlpatterns = [
    # path('/login')
    path('signup/', SignUpView.as_view(), name='Signup a new account'),
    path('login/', VerificationWithLoginView.as_view(), name='SignIn to account (after verification)'),
    path('otp/', SendOTPView.as_view(), name='asd'),
    path('social_connection_url/', SocialConnectionUrlBuilderView.as_view(), name='returns social connection url'),
    path('update_access_token/', UpdateAccessTokenView.as_view(), name='returns updated access token'),
    path('web/login/', WebSignInView.as_view(), name='Web signIn'),
    path('web/logout/', WebLogoutView.as_view(), name='Web Logout'),

    # '''post req fields=> mode(?social, code, state):, mode_identifier, mode_data'''
    # path('social/', SocialTokenBasedRedirectionView.as_view(), name='SocialLoginLinkingHandler'),
]