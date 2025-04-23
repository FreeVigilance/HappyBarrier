from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from users.account_views import ChangePasswordView, ChangePhoneView, UserAccountView
from users.admin_views import AdminBlockUserView, AdminSearchUserView, AdminUnblockUserView, AdminUserAccountView
from users.auth_views import AdminPasswordVerificationView, CheckAdminView, LoginView, ResetPasswordView

urlpatterns = [
    path("auth/login/", LoginView.as_view(), name="login"),
    path("auth/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path(
        "auth/admin/password_verification/", AdminPasswordVerificationView.as_view(), name="admin_password_verification"
    ),
    path("users/check_admin/", CheckAdminView.as_view(), name="check_admin"),
    path("users/me/", UserAccountView.as_view(), name="user_account"),
    path("users/me/phone/", ChangePhoneView.as_view(), name="change_phone"),
    path("users/me/password/", ChangePasswordView.as_view(), name="admin_change_password"),
    path("users/me/password/reset/", ResetPasswordView.as_view(), name="admin_reset_password"),
    path("admin/users/<int:id>/", AdminUserAccountView.as_view(), name="admin_get_user"),
    path("admin/users/<int:id>/block/", AdminBlockUserView.as_view(), name="admin_block_user"),
    path("admin/users/<int:id>/unblock/", AdminUnblockUserView.as_view(), name="admin_unblock_user"),
    path("admin/users/search/", AdminSearchUserView.as_view(), name="admin_search_user"),
]
