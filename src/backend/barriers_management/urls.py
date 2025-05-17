from django.urls import path

from barriers_management.views import (
    AdminBarrierLimitUpdateView,
    AdminBarrierSettingsView,
    AdminBarrierUsersListView,
    AdminBarrierView,
    AdminRemoveUserFromBarrierView,
    AdminSendBalanceCheckView,
    CreateBarrierView,
    MyAdminBarrierListView,
)

urlpatterns = [
    path("admin/barriers/", CreateBarrierView.as_view(), name="create_barrier"),
    path("admin/barriers/my/", MyAdminBarrierListView.as_view(), name="admin_my_barriers"),
    path("admin/barriers/<int:id>/", AdminBarrierView.as_view(), name="admin_barrier_view"),
    path("admin/barriers/<int:id>/limits/", AdminBarrierLimitUpdateView.as_view(), name="update_barrier_limit"),
    path("admin/barriers/<int:id>/users/", AdminBarrierUsersListView.as_view(), name="barrier_users_list"),
    path(
        "admin/barriers/<int:barrier_id>/users/<int:user_id>/",
        AdminRemoveUserFromBarrierView.as_view(),
        name="barrier_remove_user",
    ),
    path("admin/barriers/<int:id>/settings/", AdminBarrierSettingsView.as_view(), name="admin_barrier_settings"),
    path("admin/balance/", AdminSendBalanceCheckView.as_view(), name="admin_send_balance_check"),
]
