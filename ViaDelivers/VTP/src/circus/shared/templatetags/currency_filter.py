from decimal import Decimal
from django import template
import locale
from django.conf import settings
from django.template.defaultfilters import floatformat
import re

locale.setlocale(locale.LC_ALL, settings.CURRENCY_LOCALE)
register = template.Library()


@register.filter()
def currency(value):
    if not value:
        return "" # value = 0.0
    if re.search(r'^\(.*\)$', locale.currency(value)):
        return '-' + (re.sub('[(){}<>]', '', locale.currency(value)))
    else:
        return locale.currency(value, grouping=True)


@register.filter()
def percent(value):
    if value is None:
        return ""
    if isinstance(value, Decimal) and not value.is_finite():
        return ""
    value *= 100
    s = floatformat(value) + '%'
    return s
