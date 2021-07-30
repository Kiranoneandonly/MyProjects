# -*- coding: utf-8 -*-
"""Protected URLs require authorization.

TODO:
-----

Smarter checks:
 - check for is_active
 - check for superuser

Establish naming conventions for Protector instances. Examples so far:

`any_via_user`: there is no Model on this protector, it checks properties of
    the user only. Doesn't check any other request args.

`protected_task`: a Protector(Task); made sense when there's a single category
    of users, as "accessible to vendors who are assigned the task, not others"
    but fails to capture more complicated relationships like "accessible to
    vendors who are assigned a task and also the client."

`project_viewers`: Tells us that this is a Protector(Project) and 'viewers' is
    shorthand for whatever business logic defines that. Seems fitting but
    `project_viewers.protect_patterns()` reads like the viewers are doing the
    protecting, which is misleading.


Constraints:
------------

given r'/(?P<proj_id>)/?P<task_id>/'
    constraint['task_id'] = lambda project, task_id: Task(task_id).project == project


Potential compatibility issues:
-------------------------------

- putting more hierarchy in the URL structure (/task_id/asset_id/ instead of
just /asset_id/) means that view gets more kwargs, even though it doesn't
consider them relevant. Also more kwargs to pass to calls to reverse().

    - The disadvantages of "more kwargs to pass to reverse" are becoming
      apparent. At best, it's redundant information. At worst, it's an extra
      thing to get _wrong_. That sucks.

    - Potential paths to improvement:

      1) instead of constraints that enforce Task and TLTK to be consistent,
         provide an adapter that takes tltk_id and returns Task (or task_id).

      2) use less reverse() and more Model.get_absolute_url. That would probably
         work for these loc kit shared_urls that are for downloading assets, but
         is not really generally applicable due to multiple views of other
         objects.

      3) Make some magic hierarchy-aware reverse(). I guess it would need the
         same adapter smarts as #1 and _also_ require you to keep constraints,
         so that's lots of complexity.


- Django 1.6 uses a decorator @transaction.non_atomic_requests, and says "it
only works if it's applied to the view itself." Does our proxy break that? Are
there are things that work in a similar way we're breaking?
    - Yes! @csrf_exempt breaks! (special-case code in place for this)

- Protector.protect_patterns should take tuples that haven't been through url()
"""
import logging
from django.conf.urls import url, include
from django.core.exceptions import PermissionDenied, ImproperlyConfigured

# should each Protector have its own Logger?
logger = logging.getLogger('circus.' + __name__)

NO_CONSTRAINTS = 'NO_CONSTRAINTS'


class NotAuthorized(PermissionDenied):
    pass


class MissingConstraint(ImproperlyConfigured):

    def __init__(self, protector, pattern, unknown_args):
        self.protector = protector
        self.pattern = pattern
        self.unknown_args = unknown_args


    def __str__(self):
        unexpected_args = ', '.join(repr(a) for a in self.unknown_args)
        return ("%s: %s on %s encountered unexpected args %s. "
                "(Typo or missing constraint.)" % (self.__class__.__name__,
                                                   self.protector,
                                                   self.pattern,
                                                   unexpected_args)
                )


def example_condition(model, user):
    """Is this user authorized to do this to this model?

    :type user: django.contrib.auth.models.AbstractUser
    :type model: django.db.models.Model
    :rtype: bool
    """
    return False


class ProtectedURLConf(object):
    def __init__(self, urlpatterns):
        self.urlpatterns = urlpatterns


class Protector(object):
    """A proxy for views that ensures access to the view is authorized.
    """

    def __init__(self, model_class=None, pk_url_kwarg='pk', condition=None,
                 constraints=None):
        """Check for authorization against this type of Model.

        :param model_class: The class of model to load.

        :param pk_url_kwarg: The name of the URL argument with the primary key.

        :param condition: Function to call to determine if the user is
            authorized to use views with this model.

        :type model_class: django.db.models.Model
        :type condition: function(Model, User) -> bool
        :type constraints: dict
        """
        self.model_class = model_class
        self.pk_url_kwarg = pk_url_kwarg
        self.condition = condition
        if constraints is None:
            if self.model_class:
                constraints = {}
            else:
                # Constraints are between the model and another argument, so
                # if there's no model defined, constraints likely don't make
                # sense.
                constraints = NO_CONSTRAINTS
        self.constraints = constraints

    def handle(self, view, request, *a, **kw):
        """Request handler.

        If the request passes authorization checks, it will be passed on to
        that view.
        """
        try:
            user = request.user
        except AttributeError:
            raise ImproperlyConfigured(
                "Protector depends on Authentication Middleware to "
                "provide request.user.")

        if self.model_class is not None:
            key = kw.get(self.pk_url_kwarg)
            if key is None:
                raise ImproperlyConfigured(
                    u"%s did not receive any arg named %r in %r" % (
                        self, self.pk_url_kwarg, kw))
            try:
                model = self.model_class.objects.get(pk=key)
            except self.model_class.DoesNotExist:
                logger.info(
                    "Protector for view %r "
                    "failed to find %s(pk=%s)",
                    view, self.model_class, key)
                raise NotAuthorized()
        else:
            model = None

        if self.condition is not None:
            if not self.condition(model, user):
                logger.info(
                    "Protector for view %(view)r "
                    "failed user %(user)r "
                    "for condition %(condition)r",
                    {'view': view,
                     'user': user,
                     'condition': self.condition})
                raise NotAuthorized()

        if not self.check_constraints(model, kw):
            raise NotAuthorized()

        # logger.debug("Protector passing user %r to %r", user, view)
        return view(request, *a, **kw)

    def check_constraints(self, model, kwargs):
        if self.constraints == NO_CONSTRAINTS:
            return True

        for key, value in kwargs.iteritems():
            if key == self.pk_url_kwarg:
                continue

            if key in self.constraints:
                checker = self.constraints[key]
                passed = checker(model, value)
                if not passed:
                    # higher logging level because if constraints are failing,
                    # we're either generating bad links or someone is messing
                    # with URLs.
                    logger.warning(
                        "Protector failed constraint "
                        "%r(%r, %r)",
                        checker, model, value
                    )
                    return False
            else:
                raise ImproperlyConfigured(
                    "%s defines no constraint for %r" % (self, key))

        return True

    def protect_url(self, pattern):
        """Return a protected version of this URL pattern.

        :type pattern: django.core.urlresolvers.RegexURLPattern or RegexURLResolver
        :rtype: django.core.urlresolvers.RegexURLPattern
        """
        unknown_args = self._unknown_args(pattern.regex)
        if unknown_args:
            raise MissingConstraint(self, pattern, unknown_args)

        if pattern.callback:
            protected_view = ViewWrapper(self, pattern.callback)
            return url(pattern.regex.pattern, protected_view, pattern.default_args, pattern.name)

        elif hasattr(pattern, 'url_patterns'):
            # No direct callback, this is an include?
            # url() turns include() into a RegexURLResolver
            resolver = pattern
            regex = resolver.regex.pattern
            included_patterns = resolver.url_patterns
            protected_patterns = self.protect_patterns(*included_patterns)
            return url(regex, include(protected_patterns))

        else:
            raise TypeError("Not sure how to protect this: %r" % (pattern,))

    def protect_patterns(self, *url_patterns):
        """Protect a number of URL patterns.

        This interface is intended to be a match for
        django.conf.urls.patterns

        :return: list of URL patterns
        """
        protected = [self.protect_url(p) for p in url_patterns]
        return protected

    def _unknown_args(self, regex):
        if self.constraints == NO_CONSTRAINTS:
            return set()

        groups = set(regex.groupindex.keys())
        expected_groups = set([self.pk_url_kwarg] + self.constraints.keys())
        return groups - expected_groups

    def __repr__(self):
        model = ''
        condition = ''
        # is twisted.python.fullyQualifiedName in the stdlib yet?
        if self.model_class:
            model = ' m:%r' % (self.model_class,)
        if self.condition:
            condition = ' c:%r' % (self.condition,)
        return '<%s.%s%s%s>' % (
            self.__class__.__module__, self.__class__.__name__,
            model, condition
        )


# The view wrapper clouds New Relic's ability to report on which view is being
# executed, so we need to help it out here.
try:
    # noinspection PyUnresolvedReferences
    import newrelic.agent, newrelic.common.object_names

    def set_transaction_name_for_object(obj):
        # noinspection PyUnresolvedReferences
        return newrelic.agent.set_transaction_name(
            newrelic.common.object_names.callable_name(obj), priority=10)
except ImportError:
    def set_transaction_name_for_object(obj):
        pass


class ViewWrapper(object):
    def __init__(self, protector, view):
        self.protector = protector
        self.view = view
        # Some django decorators have attributes they expect to be visible
        # to the middleware. @csrf_exempt is one such thing, there may be
        # others.
        if hasattr(view, 'csrf_exempt'):
            self.csrf_exempt = view.csrf_exempt

    def __call__(self, *args, **kwargs):
        set_transaction_name_for_object(self.view)
        return self.protector.handle(self.view, *args, **kwargs)

    def __repr__(self):
        return '<%s proxy to %r>' % (self.protector, self.view)
