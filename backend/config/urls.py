from django.contrib import admin
from django.urls import include, path
from clubs.views import csrf_token

urlpatterns = [path("django-admin/", admin.site.urls), path("api/csrf/", csrf_token), path("api/", include("clubs.urls"))]
