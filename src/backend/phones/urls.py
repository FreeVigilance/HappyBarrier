from django.urls import path

from phones.views import (
    AdminBarrierPhoneDetailView,
    AdminBarrierPhoneListView,
    AdminBarrierPhoneScheduleView,
    AdminCreateBarrierPhoneView,
    UserBarrierPhoneDetailView,
    UserBarrierPhoneListView,
    UserBarrierPhoneScheduleView,
    UserCreateBarrierPhoneView,
)

urlpatterns = [
    path("barriers/<int:id>/phones/", UserCreateBarrierPhoneView.as_view(), name="user_create_barrier_phone_view"),
    path("barriers/<int:id>/phones/my/", UserBarrierPhoneListView.as_view(), name="user_barrier_phone_list_view"),
    path("phones/<int:id>/", UserBarrierPhoneDetailView.as_view(), name="user_barrier_phone_view"),
    path("phones/<int:id>/schedule/", UserBarrierPhoneScheduleView.as_view(), name="user_barrier_phone_schedule_view"),
    path(
        "admin/barriers/<int:id>/phones/", AdminCreateBarrierPhoneView.as_view(), name="admin_create_barrier_phone_view"
    ),
    path(
        "admin/barriers/<int:id>/phones/my/", AdminBarrierPhoneListView.as_view(), name="admin_barrier_phone_list_view"
    ),
    path("admin/phones/<int:id>/", AdminBarrierPhoneDetailView.as_view(), name="admin_barrier_phone_view"),
    path(
        "admin/phones/<int:id>/schedule/",
        AdminBarrierPhoneScheduleView.as_view(),
        name="admin_barrier_phone_schedule_view",
    ),
]
