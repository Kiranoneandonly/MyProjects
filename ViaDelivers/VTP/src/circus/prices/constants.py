# -*- coding: utf-8 -*-
from decimal import Decimal


# For rounding prices to the nearest cent.
TWO_PLACES = Decimal('0.00')


class MinimumJobSurcharge(object):
    """This line-item is added to make up the price of minimum jobs."""

    name = u"[minimum job surcharge]"
    orig_name = name
    prepared_name = None

    def __unicode__(self):
        return unicode(self.name)


MINIMUM_JOB_SURCHARGE = MinimumJobSurcharge()
