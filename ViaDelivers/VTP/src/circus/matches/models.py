from django.db import models
from django.utils.translation import ugettext_lazy as _
from shared.fields import CurrencyField


ANALYSIS_FIELD_NAMES = ['guaranteed', 'exact', 'duplicate', 'fuzzy9599', 'fuzzy8594', 'fuzzy7584', 'fuzzy5074', 'no_match']
ANALYSIS_FIELD_NAMES_LABELS = [
    ('guaranteed', 'Prfect'),
    ('exact', 'Exact'),
    ('duplicate', 'Reps'),
    ('fuzzy9599', '95-99'),
    ('fuzzy8594', '85-94'),
    ('fuzzy7584', '75-84'),
    ('fuzzy5074', '50-74'),
    ('no_match', 'NoMch')
]


class AnalysisFields(models.Model):
    guaranteed = models.IntegerField(_('Prfect'), default=0)
    exact = models.IntegerField(_('Exact'), default=0)
    duplicate = models.IntegerField(_('Reps'), default=0)
    fuzzy9599 = models.IntegerField(_('95-99'), default=0)
    fuzzy8594 = models.IntegerField(_('85-94'), default=0)
    fuzzy7584 = models.IntegerField(_('75-84'), default=0)
    fuzzy5074 = models.IntegerField(_('50-74'), default=0)
    no_match = models.IntegerField(_('NoMch'), default=0)

    class Meta:
        abstract = True


class AnalysisCategoryCurrencyFields(models.Model):
    guaranteed = CurrencyField(_('Prfect'), default=0.0)
    exact = CurrencyField(_('Exact'), default=0.5)
    duplicate = CurrencyField(_('Reps'), default=0.5)
    fuzzy9599 = CurrencyField(_('95-99'), default=1.0)
    fuzzy8594 = CurrencyField(_('85-94'), default=1.0)
    fuzzy7584 = CurrencyField(_('75-84'), default=1.0)
    fuzzy5074 = CurrencyField(_('50-74'), default=1.0)
    no_match = CurrencyField(_('NoMch'), default=1.0)

    class Meta:
        abstract = True
