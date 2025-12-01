from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path("admin/", admin.site.urls),

    # 🔹 Django標準の認証URL（login, logout など）を有効化
    path("accounts/", include("django.contrib.auth.urls")),

    # 🔹 自分のアプリ(core)のURL
    path("", include("core.urls")),
]
