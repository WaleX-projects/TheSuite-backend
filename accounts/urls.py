from django.urls import path
from .views import RegisterView, LoginView, ProfileView, VerifyEmailView, PasswordResetRequestView, PasswordResetView, PendoMetadataView

urlpatterns = [
    path("register/", RegisterView.as_view(), name="register"),
    path("login/", LoginView.as_view(), name="login"),
    path("profile/", ProfileView.as_view(), name="profile"),
    path("verify/<str:token>/", VerifyEmailView.as_view(), name="verify-email"),
    path("reset-password-request/", PasswordResetRequestView.as_view(), name="password-reset-request"),
    path("reset-password/<str:token>/", PasswordResetView.as_view(), name="password-reset"),
    path("pendo-metadata/", PendoMetadataView.as_view(), name="pendo-metadata"),
]