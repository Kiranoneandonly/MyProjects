# -*- coding: utf-8 -*-
import re
from unittest import TestCase
from django.conf.urls import url, include
from django.contrib.auth.models import AbstractBaseUser
from django.core.exceptions import ObjectDoesNotExist, ImproperlyConfigured
from django.core.urlresolvers import resolve
from django.test import RequestFactory
from django.views.decorators.csrf import csrf_exempt
from mock import Mock, patch, create_autospec, ANY
from shared.protection import Protector, NotAuthorized, ViewWrapper, \
    NO_CONSTRAINTS


class SprocketManager(object):

    def get(self, **kwargs):
        sprocket = Sprocket()
        sprocket.__dict__.update(kwargs)
        return sprocket


class Sprocket(object):
    """A mock model."""

    class DoesNotExist(ObjectDoesNotExist):
        pass

    objects = SprocketManager()


    def yes(self, user):
        return True


    def no(self, user):
        return False



class UnicornManager(object):
    """Silly, unicorns do not exist."""

    def get(self, **kwargs):
        raise Unicorn.DoesNotExist



class Unicorn(object):
    """Non-existent model."""

    class DoesNotExist(ObjectDoesNotExist):
        pass

    objects = UnicornManager()



class TestProtector(TestCase):

    def setUp(self):
        self.view_calls = []
        self.view_response = object()
        self.request = RequestFactory().get('/')
        self.request.user = Mock(AbstractBaseUser)


    def view(self, request, *a, **kw):
        self.assertIs(self.request, request)
        self.view_calls.append(((request,) + a, kw))
        return self.view_response


    def test_passthrough(self):
        protector = Protector(condition=lambda obj, user: True)

        response = protector.handle(self.view, self.request)

        self.assertIs(self.view_response, response)
        self.assertEqual(1, len(self.view_calls))
        view_args, view_kwargs = self.view_calls[0]
        # request should be passed through to view
        self.assertIs(self.request, view_args[0])


    def test_always_fail(self):
        protector = Protector(condition=lambda obj, user: False)

        with self.assertRaises(NotAuthorized):
            protector.handle(self.view, self.request)

        self.assertEqual(0, len(self.view_calls))


    def test_user_conditional(self):
        self.request.user.is_authenticated = lambda: True

        protector = Protector(condition=lambda obj, user: user.is_authenticated())

        response = protector.handle(self.view, self.request)

        self.assertIs(self.view_response, response)
        self.assertEqual(1, len(self.view_calls))


    def test_user_conditional_negative(self):
        self.request.user.is_authenticated = lambda: False

        protector = Protector(condition=lambda obj, user: user.is_authenticated())

        with self.assertRaises(NotAuthorized):
            protector.handle(self.view, self.request)

        self.assertEqual(0, len(self.view_calls))


    def test_with_object(self):
        # noinspection PyTypeChecker
        protector = Protector(Sprocket, 'sprocket_id')
        response = protector.handle(self.view, self.request, sprocket_id='123')

        self.assertIs(self.view_response, response)
        self.assertEqual(1, len(self.view_calls))
        view_args, view_kwargs = self.view_calls[0]
        self.assertIs(self.request, view_args[0])


    def test_object_not_found(self):
        # noinspection PyTypeChecker
        protector = Protector(Unicorn, 'unicorn_id')

        # When it can't find the object, we can't make any assertions about
        # whether you're authorized to know whether it exists. So this should
        # not leak information, and return the same HTTP response code as
        # requests that fail authorization checks.
        with self.assertRaises(NotAuthorized):
            protector.handle(self.view, self.request, unicorn_id='42')

        self.assertEqual(0, len(self.view_calls))


    def test_key_not_given(self):
        # noinspection PyTypeChecker
        protector = Protector(Sprocket, 'sprocket_id')

        with self.assertRaises(ImproperlyConfigured):
            protector.handle(self.view, self.request, notasprocket_id='42')

        self.assertEqual(0, len(self.view_calls))


    def test_with_object_condition(self):
        condition = lambda sprocket, user: sprocket.yes(user)
        # noinspection PyTypeChecker
        protector = Protector(Sprocket, 'sprocket_id', condition)
        response = protector.handle(self.view, self.request, sprocket_id='123')

        self.assertIs(self.view_response, response)
        self.assertEqual(1, len(self.view_calls))


    def test_with_object_condition_failure(self):
        condition = lambda sprocket, user: sprocket.no(user)
        # noinspection PyTypeChecker
        protector = Protector(Sprocket, 'sprocket_id', condition)

        with self.assertRaises(NotAuthorized):
            protector.handle(self.view, self.request, sprocket_id='345')

        self.assertEqual(0, len(self.view_calls))


    def test_checks_constraints(self):
        # noinspection PyTypeChecker
        protector = Protector(Sprocket)
        check_constraints = create_autospec(protector.check_constraints)
        check_constraints.return_value = True
        protector.check_constraints = check_constraints

        protector.handle(self.view, self.request, pk='123')

        check_constraints.assert_called_once_with(ANY, {'pk': '123'})


    def test_checks_constraints_failure(self):
        # noinspection PyTypeChecker
        protector = Protector(Sprocket)
        check_constraints = create_autospec(protector.check_constraints)
        check_constraints.return_value = False
        protector.check_constraints = check_constraints

        with self.assertRaises(NotAuthorized):
            protector.handle(self.view, self.request, pk='123')

        check_constraints.assert_called_once_with(ANY, {'pk': '123'})


# a 'urlconf' is a module with a "urlpatterns" attribute, but this
# should be close enough.
class URLConf(object):
    def __init__(self, urlpatterns):
        self.urlpatterns = urlpatterns


class TestProtectorURLs(TestCase):
    def setUp(self):
        self.protector = Protector()


    def test_protect_single_pattern(self):
        view = lambda *a, **kw: None
        regex = r'^task/(?P<pk>\d+)/'
        kwargs = {'foo': 'bar'}
        view_name = 'view_one'
        orig_url = url(regex, view, kwargs, name=view_name)

        # method under test
        wrapped_url = self.protector.protect_url(orig_url)

        self.assertEqual(regex, wrapped_url.regex.pattern)
        self.assertEqual(view_name, wrapped_url.name)
        self.assertEqual(kwargs, wrapped_url.default_args)

        callback = wrapped_url.callback
        self.assertEqual(self.protector, callback.protector)
        self.assertEqual(view, callback.view)


    def test_protect_url_rejects_unknown_args(self):
        # noinspection PyTypeChecker
        protector = Protector(Sprocket)
        view = lambda *a, **kw: None
        regex = r'^task/(?P<pk>\d+)/(?P<quux>\w+)'
        kwargs = {'foo': 'bar', 'quux': 'fruitcake'}
        view_name = 'view_one'
        orig_url = url(regex, view, kwargs, name=view_name)

        # method under test
        with self.assertRaises(ImproperlyConfigured):
            protector.protect_url(orig_url)


    def test_protect_url_with_constrained_args(self):
        constraints = {'quux': lambda x, y: True}
        # noinspection PyTypeChecker
        protector = Protector(Sprocket, constraints=constraints)
        view = lambda *a, **kw: None
        regex = r'^task/(?P<pk>\d+)/(?P<quux>\w+)'
        kwargs = {'foo': 'bar', 'quux': 'fruitcake'}
        view_name = 'view_one'
        orig_url = url(regex, view, kwargs, name=view_name)

        # method under test
        protected_url = protector.protect_url(orig_url)
        # pass if no exception raised


    def test_check_regex_for_unknown_args(self):
        constraints = {'quux': lambda x, y: True}
        # noinspection PyTypeChecker
        protector = Protector(Sprocket, constraints=constraints)
        regex = r'^task/(?P<pk>\d+)/(?P<quux>\w+)(?P<bang>!)?'
        unknown_args = protector._unknown_args(re.compile(regex))
        self.assertEqual({'bang'}, unknown_args)


    def test_no_constraint_check_when_no_model(self):
        protector = Protector()
        regex = r'^task/(?P<pk>\d+)/(?P<quux>\w+)(?P<bang>!)?'
        # noinspection PyProtectedMember
        unknown_args = protector._unknown_args(re.compile(regex))
        self.assertFalse(unknown_args)


    def test_protect_patterns(self):
        view_1 = lambda *a, **kw: None
        view_2 = lambda *a, **kw: None

        url_1 = url(r'^task/(?P<pk>\d+)/', view_1, name='view_one')
        url_2 = url(r'^task/(?P<pk>\d+)/edit', view_2, name='view_two')

        # self.protector.protect_url = lambda p: ('Protected', p)
        expected_urls = [url_1, url_2]

        prefix = ''
        result = self.protector.protect_patterns(url_1, url_2)
        # TODO Fix Test
        # self.assertEqual(expected_urls, result)


    # def test_protect_patterns_prefixed(self):
    #     self.fail()
    #
    #

    def test_protect_include(self):
        view = lambda *a, **kw: None
        child_regex = r'^task/(?P<task_id>\d+)/'
        kwargs = {'foo': 'bar'}
        view_name = 'view_one'
        child_url = url(child_regex, view, kwargs, name=view_name)

        include_target = [child_url]

        parent_regex = '^project/(?P<proj_id>\d+)/'
        parent_url = url(parent_regex, include(include_target))

        protected_urls = self.protector.protect_patterns(parent_url)

        parent_urlconf = URLConf(protected_urls)

        # this is getting more integration-test-like, but I am not sure how
        # to break it down yet.
        # Make sure resolution works on the combined path.
        match = resolve('/project/123/task/456/', parent_urlconf)

        # Assert that the view resolved to is protected.
        self.assertEqual(self.protector, match.func.protector)
        self.assertEqual(view, match.func.view)


class TestViewWrapper(TestCase):
    def test_wrap_unannotated_view(self):
        def normal_view(request):
            pass

        protector = object()
        wrapped = ViewWrapper(protector, normal_view)
        self.assertFalse(hasattr(wrapped, 'csrf_exempt'))


    def test_wrap_csrf_exempt_view(self):
        @csrf_exempt
        def exempt_view(request):
            pass

        protector = object()
        wrapped = ViewWrapper(protector, exempt_view)
        self.assertTrue(wrapped.csrf_exempt)



class TestProtectorConstraints(TestCase):
    def setUp(self):
        self.model = object()
        constraints = {
            'asset_id': self.is_odd
        }
        self.protector = Protector(constraints=constraints)
        self.is_odd_calls = []


    def is_odd(self, model, asset_id):
        self.is_odd_calls.append((model, asset_id))
        return int(asset_id) % 2


    def test_constraints_pass(self):
        asset_id = '5'
        kwargs = {'pk': '10', 'asset_id': asset_id}
        passed = self.protector.check_constraints(self.model, kwargs)
        self.assertTrue(passed)
        self.assertEqual([(self.model, asset_id)], self.is_odd_calls)


    def test_constraints_fail(self):
        asset_id = '6'
        kwargs = {'pk': '10', 'asset_id': asset_id}
        passed = self.protector.check_constraints(self.model, kwargs)
        self.assertFalse(passed)
        self.assertEqual([(self.model, asset_id)], self.is_odd_calls)


    def test_catch_unconstrained_key(self):
        # This constraint will always pas,
        self.protector.constraints['asset_id'] = lambda model, asset_id: True

        # but there is another kwarg in here with no constraint defined.
        kwargs = {'pk': '10', 'asset_id': '7', 'quux_id': '987'}

        with self.assertRaises(ImproperlyConfigured):
            self.protector.check_constraints(self.model, kwargs)


    def test_no_constraints(self):
        # With the NO_CONSTRAINTS flag, check_constraints should pass even if
        # there are unrecognized kwargs.
        protector = Protector(constraints=NO_CONSTRAINTS)
        kwargs = {'pk': '10', 'asset_id': '7', 'quux_id': '987'}
        self.assertTrue(protector.check_constraints(self.model, kwargs))
