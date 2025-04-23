from django.urls import path

from access_requests.views import (
    AccessRequestView,
    AdminAccessRequestsListView,
    AdminAccessRequestView,
    AdminCreateAccessRequestView,
    CreateAccessRequestView,
    MyAccessRequestsListView,
)

urlpatterns = [
    path("access_requests/", CreateAccessRequestView.as_view(), name="create_access_request"),
    path("access_requests/my/", MyAccessRequestsListView.as_view(), name="my_access_requests"),
    path("access_requests/<int:id>/", AccessRequestView.as_view(), name="access_request_view"),
    path("admin/access_requests/", AdminCreateAccessRequestView.as_view(), name="admin_create_access_request"),
    path("admin/access_requests/my/", AdminAccessRequestsListView.as_view(), name="admin_access_requests"),
    path("admin/access_requests/<int:id>/", AdminAccessRequestView.as_view(), name="admin_access_request_view"),
]
