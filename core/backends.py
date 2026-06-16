from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.models import User


class EmailOrUsernameBackend(ModelBackend):
    """ユーザー名またはメールアドレスでログインできるバックエンド。"""

    def authenticate(self, request, username=None, password=None, **kwargs):
        # メールアドレスで検索
        try:
            user = User.objects.get(email=username)
        except User.DoesNotExist:
            # ユーザー名で検索
            try:
                user = User.objects.get(username=username)
            except User.DoesNotExist:
                return None

        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None
