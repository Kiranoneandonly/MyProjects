from django.db import models
from shared.models import CircusModel


class Holiday(CircusModel):
    holiday_name = models.CharField(max_length=100, blank=True, null=True)
    holiday_date = models.DateField(blank=True, null=True)
    description = models.TextField(blank=True, null=True)

    def __unicode__(self):
        return u'{0}: {1}'.format(self.holiday_name, self.holiday_date)
