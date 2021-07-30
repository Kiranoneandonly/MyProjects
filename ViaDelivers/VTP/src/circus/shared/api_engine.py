# coding=utf-8
from __future__ import unicode_literals
import json
import logging
from django.conf import settings
import requests
from shared import har

logger = logging.getLogger('circus.' + __name__)

API_HEADERS = {
    'content-type': 'application/json',
    'x-apikey': settings.VIA_DVX_API_KEY
}


STATUS_SUCCESS = 0
STATUS_FORCE_MANUAL_ESTIMATE = -1
STATUS_INVALID_EC2_DIRECTORY = -2
STATUS_UNKNOWN_FAILURE = -3
# Files did not make it to DVX server in time for analysis:
STATUS_DOWNLOAD_FILES_ANALYSIS_ERROR = -4


class DVXFailure(Exception):

    def __init__(self, url, response_data=None, http_archive=None,
                 exception=None):
        super(DVXFailure, self).__init__(url, response_data, http_archive,
                                         exception)
        self.url = url
        self.http_archive = http_archive
        self.response_data = response_data
        self.__cause__ = exception


    @classmethod
    def from_http_response(cls, http_response, response_data=None):
        # Instead of figuring out which bits to parse out now, save everything.
        archive = har.request_and_response(http_response,
                                           include_post_body=True)
        return cls(url=http_response.url,
                   response_data=response_data,
                   http_archive=archive)


    @classmethod
    def from_exception(cls, exception, http_request):
        archive = har.request(http_request, include_post_body=True)
        url = http_request.url
        return cls(url=url, http_archive=archive, exception=exception)


    @property
    def api_status(self):
        if self.response_data:
            return self.response_data.get('status')

    def __str__(self):
        status = self.api_status
        name = self.url.replace(settings.VIA_DVX_BASE_URL, '')
        if self.__cause__:
            cause = ' cause:%r' % (self.__cause__,)
        else:
            cause = ''
        return ('<%(cls)s %(name)s status:%(status)s%(cause)s>' % dict(
            name=name,
            cause=cause,
            cls=self.__class__.__name__,
            status=status,
        ))


def _api_request(url, payload, method='POST'):
    logger.info('URL: ' + url)
    logger.info('Payload JSON: ' + json.dumps(payload))

    if method == 'POST':
        request = requests.Request(
            method, url, headers=API_HEADERS,
            data=json.dumps(payload))
    elif method == 'GET':
        request = requests.Request(
            method, url, headers=API_HEADERS,
            params=payload)
    else:
        raise ValueError("Only expected GET or POST, not %r" % (method,))

    try:
        # We're using prepared requests and .send() instead of doing both in one
        # .get() or .put() step so we still have a request object to log when
        # things blow up.
        session = requests.Session()
        request = session.prepare_request(request)
        http_response = session.send(request, timeout=settings.VIA_API_CALL_TIMEOUT_SECONDS)
    except requests.RequestException, err:
        # Sometimes a request to the API fails with a nice error message.
        # On occasion it may fail with a status 500 error page.
        # And sometimes it may crash and close the connection without sending
        # an HTTP response *at all*, which manifests as a ConnectionError here.
        logger.error("Error retrieving response.", exc_info=True)
        raise DVXFailure.from_exception(err, err.request)

    logger.info(
        'Response Text: ' + unicode(http_response) + unicode(http_response.text))

    try:
        response_data = http_response.json()
    except ValueError:
        raise DVXFailure.from_http_response(http_response)

    # responses surrounded by "" or [] can make .json() return strings or
    # lists, so make sure we have a dict.
    if not isinstance(response_data, dict):
        raise DVXFailure.from_http_response(http_response)

    if int(response_data.get('status')) != STATUS_SUCCESS:
        raise DVXFailure.from_http_response(http_response, response_data)

    return response_data


def api_post(url, payload):
    return _api_request(url, payload, 'POST')


def api_get(url, payload):
    return _api_request(url, payload, 'GET')
