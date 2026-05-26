from django.contrib import admin
from django.urls import path, include
from django.views.generic import TemplateView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("django.contrib.auth.urls")),

    # 言語切替用
    path("i18n/", include("django.conf.urls.i18n")),

    # Service Worker はルートで配信する必要がある
    path("sw.js", TemplateView.as_view(
        template_name="sw.js",
        content_type="application/javascript",
    ), name="sw_js"),

    path("", include("core.urls")),
]
