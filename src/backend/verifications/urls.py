from django.urls import path

from verifications.views import SendVerificationCodeView, VerifyCodeView

urlpatterns = [
    path("auth/codes/", SendVerificationCodeView.as_view(), name="send_code"),
    path("auth/codes/verify/", VerifyCodeView.as_view(), name="verify_code"),
]
