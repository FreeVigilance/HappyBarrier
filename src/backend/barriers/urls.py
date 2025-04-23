from django.urls import path

from barriers.views import (
    BarrierAccessCheckView,
    BarrierLimitView,
    BarrierView,
    LeaveBarrierView,
    ListBarriersView,
    MyBarriersListView,
)

urlpatterns = [
    path("barriers/", ListBarriersView.as_view(), name="list_barriers"),
    path("barriers/my/", MyBarriersListView.as_view(), name="my_barriers"),
    path("barriers/<int:id>/", BarrierView.as_view(), name="get_barrier"),
    path("barriers/<int:id>/limits/", BarrierLimitView.as_view(), name="get_barrier_limits"),
    path("barriers/<int:id>/leave/", LeaveBarrierView.as_view(), name="leave_barrier"),
    path("barriers/<int:id>/check_access/", BarrierAccessCheckView.as_view(), name="barrier_has_access"),
]
