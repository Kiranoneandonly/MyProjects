from decimal import Decimal

from django import template
register = template.Library()


@register.simple_tag
def word_percentage(total_words, word_percentage_per_bucket):
    total_count_percentage = Decimal(total_words)/100
    if word_percentage_per_bucket == 0:
        word_percentage_of_total = 0
    else:
        word_percentage_of_total = word_percentage_per_bucket/total_count_percentage
    return int(round(word_percentage_of_total, 0))


@register.simple_tag
def mbd_percentage(mbd_price):
    if mbd_price == 0:
        mbd_percentage_per_bucket = 0
    else:
        mbd_percentage_per_bucket = Decimal(mbd_price)*100
    return int(mbd_percentage_per_bucket)



