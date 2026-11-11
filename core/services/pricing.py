"""Display-only CHF conversion. Never use estimates to settle payments."""
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from django.conf import settings
from django.utils.formats import number_format
from django.utils.translation import gettext as _

CURRENCIES = ('JPY', 'CHF', 'USD', 'EUR')
# Fixed display rates explicitly chosen by the product owner.
DEFAULT_RATES = {'CHF':'1', 'JPY':'190', 'USD':'1.2', 'EUR':'1.1'}


def display_currency(request):
    selected = request.COOKIES.get('display_currency')
    if selected in CURRENCIES:
        return selected
    return 'JPY' if getattr(request, 'LANGUAGE_CODE', 'en').startswith('ja') else 'CHF'


def rate_for(currency):
    if currency == 'CHF':
        return Decimal('1')
    try:
        value = Decimal(str(getattr(settings, 'DISPLAY_CURRENCY_RATES', {}).get(currency, DEFAULT_RATES[currency])))
        if value.is_finite() and value > 0:
            return value
    except (InvalidOperation, ValueError, TypeError):
        pass
    return Decimal(DEFAULT_RATES[currency])


def price_label(amount_chf, currency):
    if currency not in CURRENCIES:
        currency = 'CHF'
    places = 0 if currency == 'JPY' else 2
    amount = (Decimal(str(amount_chf))*rate_for(currency)).quantize(Decimal('1') if places == 0 else Decimal('.01'), rounding=ROUND_HALF_UP)
    return currency + ' ' + number_format(amount, decimal_pos=places, use_l10n=True, force_grouping=True)


def pricing_context(request):
    currency = display_currency(request)
    labels = (_('Japanese yen'), _('Swiss franc'), _('US dollar'), _('Euro'))
    return {
        'display_currency': currency,
        'display_currency_choices': list(zip(CURRENCIES, labels)),
        'converted_price': currency != 'CHF',
        'gold_display_price': price_label(getattr(settings, 'GOLD_MONTHLY_PRICE_CHF', '100'), currency),
        'display_rate_label': price_label(1, currency),
    }
