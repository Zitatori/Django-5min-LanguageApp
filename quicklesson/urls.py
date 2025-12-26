from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("django.contrib.auth.urls")),


    # 言語切替用
    path("i18n/", include("django.conf.urls.i18n")),

    path("", include("core.urls")),
]
