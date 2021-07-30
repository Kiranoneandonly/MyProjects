from django.conf import settings
from django.http import HttpResponseRedirect
from django.utils.encoding import smart_str
from django.utils.http import urlquote
from shared.utils import get_boto_client, get_boto_session


def serve_file(request, file, **kwargs):
    """Serves files by redirecting to S3 url"""
    session = get_boto_session()
    client = get_boto_client(session)
    file_url = client.generate_presigned_url(
                                            ClientMethod="get_object",
                                            ExpiresIn=3600,
                                            Params={
                                                    "Bucket": settings.AWS_STORAGE_BUCKET_NAME,
                                                    "Key": u'media/{0}'.format(file.name),
                                                    "ResponseContentDisposition": 'attachment; filename="%s"' % urlquote(file.name.split('/')[-1]),
                                                    }
                                            )
    return HttpResponseRedirect(smart_str(file_url))


def public_download_url(file, **kwargs):
    """Directs downloads to file.url (useful for normal file system storage)"""
    return file.url
