from posixpath import basename

from django.conf import settings
from django.core.exceptions import SuspiciousOperation
from django.views.generic.base import ContextMixin
from django.utils.translation import ugettext as _


class DefaultContextMixin(ContextMixin):
    def get_context_data(self, **kwargs):
        context = super(DefaultContextMixin, self).get_context_data(**kwargs)
        context['TIMEZONE_BLURB_TEXT'] = _("Time Zone: %s ") % self.request.user.user_timezone
        context['hide_search'] = False
        context['search_query'] = u''

        if self.request.user.is_impersonate:
            from accounts.views import user_country
            self.request.user.country = user_country(self.request)

        return context


def set_filefield_from_s3_redirect(request, instance, file_attribute_name):
    # TODO: Instead of relying on the success redirect from S3,
    #     use fine-uploader's notification and add CSRF protection.
    media_dir = settings.MEDIA_URL[1:]
    s3_key = request.GET['key']
    bucket = request.GET['bucket']
    filename = basename(s3_key)

    if bucket != settings.AWS_STORAGE_BUCKET_NAME:
        raise SuspiciousOperation("Unexpected bucket name: %r != %r" %
                                  (bucket, settings.AWS_STORAGE_BUCKET_NAME))

    file_field = getattr(instance, file_attribute_name)

    expected_key = (
        media_dir +
        file_field.field.generate_filename(instance, filename))

    import re
    if re.search(r"\\+", expected_key):
        expected_key = re.sub(r"\\+", '/', expected_key)

    if expected_key != s3_key:
        expected_key_change = "".join([expected_key[0:(expected_key.rfind("/")+1)], filename])
        if expected_key_change != s3_key:
            raise SuspiciousOperation(
                "Unexpected reference file key: %r != %r" %
                (s3_key, expected_key))

    s3_key = s3_key[len(media_dir):]  # chop off leading media/ directory

    setattr(instance, file_attribute_name, s3_key)

    return s3_key, filename

