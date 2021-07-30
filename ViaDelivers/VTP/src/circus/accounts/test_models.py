# -*- coding: utf-8 -*-
from django.conf import settings
from django.test import TestCase
from accounts.models import CircusUser


class TestCircusUserManager(TestCase):
    def test_get_by_natural_key_is_case_insensitive(self):
        email = "Some.User@example.com"
        user = CircusUser.objects.create(
            user_type=settings.CLIENT_USER_TYPE,
            email=email,
            is_active=True,
            profile_complete=True,
            registration_complete=True,
            account=None
        )
        self.assertEqual(user, CircusUser.objects.get_by_natural_key(
            "SOME.user@example.com"))
