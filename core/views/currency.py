from django.http import HttpResponseBadRequest
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST
from core.services.pricing import CURRENCIES


@require_POST
def set_display_currency(request):
    currency = request.POST.get('currency')
    if currency not in CURRENCIES:
        return HttpResponseBadRequest('Unsupported currency')
    target = request.POST.get('next', '')
    if not url_has_allowed_host_and_scheme(target, allowed_hosts={request.get_host()}, require_https=request.is_secure()):
        target = reverse('profile')
    response = redirect(target)
    response.set_cookie('display_currency', currency, max_age=31536000, httponly=True, secure=request.is_secure(), samesite='Lax')
    return response
