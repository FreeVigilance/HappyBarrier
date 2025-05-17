"""
URL configuration for backend project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path

from users.admin_views import admin_block_password_change_view

admin.site.site_url = "/admin_panel/"
admin.site.site_header = "Admin Panel"


def health_check(request):
    return JsonResponse({"status": "ok"})


urlpatterns = [
    path("admin_panel/password_change/", admin_block_password_change_view),
    path("admin_panel/", admin.site.urls),
    path("api/", include("access_requests.urls")),
    path("api/", include("action_history.urls")),
    path("api/", include("barriers.urls")),
    path("api/", include("barriers_management.urls")),
    path("api/", include("message_management.urls")),
    path("api/", include("phones.urls")),
    path("api/", include("users.urls")),
    path("api/", include("verifications.urls")),
    path("health/", health_check),
]
