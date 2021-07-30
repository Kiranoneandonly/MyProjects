import datetime

import calendar
import hashlib
import os.path
import random
from django.conf import settings
from django.utils.timezone import localtime, is_naive, make_aware, get_current_timezone


def _make_aware_default(when):
    if is_naive(when):
        when = make_aware(when, get_current_timezone())
    return when


def calculate_gross_margin(revenue, cost):
    if not revenue or not cost:
        return None
    else:
        # currently price is Decimal and cost is float, only because cost hasn't
        # been converted over yet. They need to be consistent here, and GM
        # doesn't much benefit from being Decimal, so float everything for now.
        return (float(revenue) - float(cost)) / float(revenue)


def format_gross_margin(value):
    if not value:
        return u''
    return u'{0:.2f}%'.format(value*100)


def generate_sha1(string, salt=None):
    salt = salt or hashlib.sha1(str(random.random())).hexdigest()[:5]
    hash = hashlib.sha1(salt+str(string)).hexdigest()

    return salt, hash


def get_boto_session():
    from boto3.session import Session
    return Session(aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                   aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY)


def get_boto_client(session):
    return session.client('s3')


def copy_file_asset(from_key, to_key):
    session = get_boto_session()
    client = get_boto_client(session)
    bucket_name = str(settings.AWS_STORAGE_BUCKET_NAME)
    client.copy_object(ACL=settings.AWS_DEFAULT_ACL, Bucket=bucket_name, CopySource=bucket_name+'/'+from_key, Key=to_key)


def delete_file_asset(from_key):
    session = get_boto_session()
    client = get_boto_client(session)
    bucket_name = str(settings.AWS_STORAGE_BUCKET_NAME)
    client.delete_object(Bucket=bucket_name, Key=from_key)


def sibpath(path, sibling):
    """
    Return the path to a sibling of a file in the filesystem.

    This is useful in conjunction with the special C{__file__} attribute
    that Python provides for modules, so modules can load associated
    resource files.
    """
    # stolen from twisted.python.util
    return os.path.join(os.path.dirname(os.path.abspath(path)), sibling)


def clear_cache():
    """
    Clear Django Cache
    https://djangosnippets.org/snippets/1080/
    This piece of code will clear the cache, whether you are using in-memory or filesystem caching.
    At least for locmem one has to do clear also "_expire_info", otherwise there will be key errors:
        cache._expire_info.clear()
    if you're using memcached it's
        cache._cache.flush_all()
    """
    from django.core.cache import cache
    from django.core.cache.backends.dummy import DummyCache
    from django.core.cache.backends.memcached import PyLibMCCache, MemcachedCache

    try:
        if type(cache) is PyLibMCCache:
            cache.clear()
        elif type(cache) is MemcachedCache:
            cache._cache.flush_all()
        else:
            cache._expire_info.clear()
            cache._cache.clear()  # in-memory caching
    except AttributeError:
        # try filesystem caching next
        old = cache._cull_frequency
        old_max = cache._max_entries
        cache._max_entries = 0
        cache._cull_frequency = 1
        if type(cache) is not DummyCache:
            # cache._cull()
            cache.clear()
        cache._cull_frequency = old
        cache._max_entries = old_max


def get_first_day(dt, d_years=0, d_months=0):
    # d_years, d_months are "deltas" to apply to dt
    y, m = dt.year + d_years, dt.month + d_months
    a, m = divmod(m-1, 12)
    import pytz
    PST = pytz.timezone(settings.PST_TIME_ZONE)
    date_first_day = PST.localize(datetime.datetime(y+a, m+1, 1))
    return date_first_day


def get_last_day(dt):
    return get_first_day(dt, 0, 1) + datetime.timedelta(-1)


def add_months(sourcedate, months):
    month = sourcedate.month - 1 + months
    year = sourcedate.year + month / 12
    month = month % 12 + 1
    day = min(sourcedate.day, calendar.monthrange(year,month)[1])
    return datetime.date(year, month, day)


def format_datetime(when):
    """
    :type when: datetime.datetime or None
    """
    if when is None:
        return u''
    else:
        return unicode(localtime(when))


def comment_filters(comment_type=None):
    from django.db.models import Q
    # q_object = Q()
    # q_object.add(Q(user_type=comment_type), Q.OR)
    # q_object.add(Q(via_comment_user_type=comment_type), Q.OR)
    # return q_object
    return [
        Q(user_type=comment_type) | Q(via_comment_user_type=comment_type)
    ]


def remove_html_tags(raw_html):
    cleantext = None
    if raw_html:
        import re
        cleanr = re.compile('<.*?>')
        cleantext = re.sub(cleanr, ' ', raw_html).strip()
    return cleantext


def is_numeric(literal):
    """Return whether a literal can be parsed as a numeric value"""
    castings = [int, float, complex,
                lambda s: int(s, 2),   # binary
                lambda s: int(s, 8),   # octal
                lambda s: int(s, 16)]  # hex

    for cast in castings:
        try:
            cast(literal)
            return True
        except ValueError:
            pass
    return False
