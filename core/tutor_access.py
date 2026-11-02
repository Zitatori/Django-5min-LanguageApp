"""Keep tutor navigation and endpoint access aligned with the tutor badge."""
from functools import wraps
from django.http import HttpResponseForbidden


def can_access_tutor_dashboard(user):
    if not user.is_authenticated:
        return False
    role = getattr(getattr(user, 'userprofile', None), 'role', '')
    return (user.is_staff or user.is_superuser or role.lower() == 'admin'
            or hasattr(user, 'tutorprofile'))


def tutor_access_required(view):
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        if not can_access_tutor_dashboard(request.user):
            return HttpResponseForbidden('Tutor access is required.')
        return view(request, *args, **kwargs)
    return wrapped
