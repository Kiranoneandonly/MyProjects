# -*- coding: utf-8 -*-
"""HTTP Archive writer for logging Requests.

http://www.softwareishard.com/blog/har-12-spec/
"""
import datetime
import json
import pytz


def request_and_response(response, include_post_body=False):
    """Return a HAR log for this Response and the Request that made it.

    :type response: requests.Response
    :rtype: unicode
    """
    return json.dumps(_har_request_and_response(response, include_post_body))


def request(http_request, include_post_body=False):
    return json.dumps(_har_request(http_request, include_post_body))


def _har_request_and_response(response, include_post_body=False):
    # N.B. the use case this was written for was only POST and didn't care about
    # redirects or cookies.
    request = response.request
    har_content = {
        'size': len(response.content),
        'mimeType': response.headers['Content-Type'],
        'text': response.content,
    }
    post_data = {
        "mimeType": request.headers['Content-Type'],
    }
    if include_post_body:
        post_data['text'] = request.body
    else:
        post_data['comment'] = 'omitted from log for security'

    # This is the server's http response version. How to get request version?
    http_version = {10: '1.0', 11: '1.1'}.get(response.raw.version, '1.0')

    har_request = {
        'method': request.method,
        'url': request.url,
        'httpVersion': http_version,
        'cookies': [],  # TODO
        'headers': _har_headers(request.headers),
        'queryString': [],  # TODO
        'postData': post_data,
        'headersSize': -1,
        'bodySize': -1,
    }
    har_response = {
        'status': response.status_code,
        'statusText': response.reason,
        'httpVersion': http_version,
        'cookies': [],  # TODO
        'headers': _har_headers(response.headers),
        'content': har_content,
        'headersSize': -1,
        'bodySize': -1
    }
    entry = {
        'request': har_request,
        'response': har_response,
        'cache': {},
        # We don't have timing information, which HAR considers non-optional
        # but is not essential to our use at the moment.
        # 'timings': {}
    }
    if response.elapsed:
        entry['time'] = response.elapsed.total_seconds() * 1000
        # fudging a bit, since request doesn't store the start time
        entry['startedDateTime'] = (
            datetime.datetime.now(pytz.UTC) - response.elapsed).isoformat()
    else:
        # lies
        entry['startedDateTime'] = datetime.datetime.now(pytz.UTC).isoformat()

    return {
        'log': {
            'version': '1.2',
            'creator': {'name': 'via-circus', 'version': '1'},
            'entries': [entry]
        },
    }


def _har_request(request, include_post_body):
    entry = {}
    post_data = {
        "mimeType": request.headers['Content-Type'],
    }
    if include_post_body:
        post_data['text'] = request.body
    else:
        post_data['comment'] = 'omitted from log for security'

    # lies?
    http_version = '1.0'

    har_request = {
        'method': request.method,
        'url': request.url,
        'httpVersion': http_version,
        'cookies': [],  # TODO
        'headers': _har_headers(request.headers),
        'queryString': [],  # TODO
        'postData': post_data,
        'headersSize': -1,
        'bodySize': -1,
    }
    # We don't have a response, but response is not an optional field.
    har_content = {
        'size': 0,
        'mimeType': '',
    }
    har_response = {
        'status': 0,
        'statusText': '',
        'httpVersion': http_version,
        'cookies': [],  # TODO
        'headers': [],
        'content': har_content,
        'headersSize': -1,
        'bodySize': -1
    }
    entry = {
        # cheating a bit as this is specified as request start time, not some
        # point after it's finished, but we don't have the request time.
        'startedDateTime': datetime.datetime.now(pytz.UTC).isoformat(),
        'request': har_request,
        'response': har_response,
        'cache': {},
        # We don't have timing information, which HAR considers non-optional
        # but is not essential to our use at the moment.
        # 'time': -1,
        # 'timings': {}
    }
    return {
        'log': {
            'version': '1.2',
            'creator': {'name': 'via-circus', 'version': '1'},
            'entries': [entry]
        },
    }


def _har_headers(header_dict):
    return [{'name': name, 'value': value}
            for name, value in header_dict.iteritems()]
