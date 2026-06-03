from django.contrib import admin
from django.urls import path, include
from django.views.generic import TemplateView
from django.http import JsonResponse

def assetlinks(request):
    return JsonResponse([{
        "relation": ["delegate_permission/common.handle_all_urls"],
        "target": {
            "namespace": "android_app",
            "package_name": "com.onrender.django_5min_languageapp.twa",
            "sha256_cert_fingerprints": [
                "DA:19:AF:D3:5C:0F:FA:3D:91:65:D3:21:F0:4A:E0:7E:34:5A:4E:09:C4:39:73:2A:DF:EC:A0:51:89:DF:30:B4"
            ]
        }
    }], safe=False)

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

    # TWA Digital Asset Links
    path(".well-known/assetlinks.json", assetlinks, name="assetlinks"),

    path("", include("core.urls")),
]
