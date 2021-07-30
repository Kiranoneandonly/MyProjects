# -*- coding: utf-8 -*-
from urlparse import urlsplit, urljoin
from django.core.urlresolvers import reverse, resolve
from django.test import TestCase as DjangoTestCase
from django.utils.http import urlencode
from pyquery import PyQuery


class ViewTestCase(DjangoTestCase):

    def assert_200(self, response):
        if hasattr(response, 'url'):
            url = ' ' + response.url
        else:
            url = ''
        self.assertEqual(200, response.status_code,
                         "Expected response status 200, got %s: %s%s" % (
                             response.status_code, response.reason_phrase,
                             url
                         ))


    def assertNoFormError(self, response):
        if response.context and 'form' in response.context:
            form = response.context['form']
            if form.errors:
                self.fail(form.errors)


    def assertRedirectsToName(self, response, url_name,
                              *view_args, **view_kwargs):
        """Assert the response is a redirect to a URL with this name.

        Slightly different API than assertRedirects, and doesn't follow the
        redirect to see if it returns 200.
        """
        self.assertEqual(302, response.status_code)
        redirect_url = urlsplit(response.url).path
        match = resolve(redirect_url)
        self.assertEqual(url_name, match.url_name)
        if view_args is not None:
            self.assertEqual(view_args, match.args)
        if view_kwargs is not None:
            self.assertEqual(view_kwargs, match.kwargs)


class PageObject(object):
    view_name = None

    def __init__(self, response, *view_args, **view_kwargs):
        self.response = response
        self.doc = PyQuery(response.content)


    # All these class methods that take a Client to get the initial page content
    # should probably be off on some other object. (i.e. a custom Client)

    @classmethod
    def credentials(cls):
        raise NotImplementedError


    @classmethod
    def url(cls, *view_args, **view_kwargs):
        assert cls.view_name is not None, "must define %s.view_name" % (
            cls.__name__,)
        url = reverse(cls.view_name, args=view_args, kwargs=view_kwargs)
        match = resolve(url)
        if match.url_name != cls.view_name:
            raise AssertionError("url %r does not resolve to %s: "
                                 "matched %s" % (url, cls.view_name, match))
        return url


    @classmethod
    def get(cls, client, *view_args, **view_kwargs):
        """GET with args for matching django URL patterns.

        :type client: django.test.Client
        """
        cls.login(client)

        url = cls.url(*view_args, **view_kwargs)

        response = client.get(url)
        self = cls(response, *view_args, **view_kwargs)
        return self


    @classmethod
    def get_query(cls, test_client, **query_args):
        """GET with query parameters in the URL.

        :type test_client: django.test.Client
        """
        cls.login(test_client)

        url = cls.url()
        query_str = urlencode(query_args)
        url = urljoin(url, '?' + query_str)

        response = test_client.get(url)
        self = cls(response)
        return self


    @classmethod
    def post(cls, client, post_data, *view_args, **view_kwargs):
        """
        :type client: django.test.Client
        """
        cls.login(client)

        url = cls.url(*view_args, **view_kwargs)

        response = client.post(url, post_data)

        if not response.content:
            raise ValueError(
                "POST response contains no body content: %s" % (response,))

        self = cls(response, *view_args, **view_kwargs)
        return self


    @classmethod
    def login(cls, client):
        credentials = cls.credentials()
        if not client.login(**credentials):
            raise ValueError("login failed")
