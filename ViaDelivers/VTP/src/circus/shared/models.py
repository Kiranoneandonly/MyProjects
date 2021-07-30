from django.db import models


class CircusModel(models.Model):
    is_deleted = models.BooleanField(default=False)

    created = models.DateTimeField(auto_now_add=True, blank=True, null=True)
    modified = models.DateTimeField(auto_now=True, blank=True, null=True)

    def attrs(self):
        for field in self._meta.fields:
            yield field.name, getattr(self, field.name)

    def dump(self):
        for field, value in self.attrs():
            print u"{0}: {1}".format(field, value)

    class Meta:
        abstract = True

    def __eq__(self, other):
        # Model subclasses really oughta compare as equal to their parent
        # And this is in fact the default behaviour in Django 1.7:
        #     https://code.djangoproject.com/ticket/16458
        # from which this implementation is backported.
        return (isinstance(other, models.Model) and
                self._meta.concrete_model == other._meta.concrete_model and
                self._get_pk_val() == other._get_pk_val())

    def __repr__(self):
        # Overridden to include object ID in repr.
        # Note python 2.x repr must be str, not unicode, so encode to utf-8.
        return ((u'<%s#%s: %s>' %
                 (self.__class__.__name__, self.id, unicode(self))).encode('utf-8', errors='replace'))


class CircusLookup(CircusModel):
    code = models.CharField(max_length=40, unique=True, db_index=True)
    description = models.CharField(max_length=40)

    class Meta:
        abstract = True

    def __unicode__(self):
        return unicode(self.description)

