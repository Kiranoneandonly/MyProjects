# -*- coding: utf-8 -*-
"""Send reset-your-password emails to all clients.

Part of the initial OLS to VTP migration.
"""
from django.conf import settings
from django.contrib.auth.forms import PasswordResetForm
from django.core.management import BaseCommand

# noinspection PyUnresolvedReferences
from six.moves import input
from accounts.models import CircusUser


def send_reset_link(new_user, domain='translation.viadelivers.com'):
    # It is a little weird to build a Form to send an email, but the existing
    # password-reset-link generation is in PasswordResetForm.save().
    form = PasswordResetForm({'email': new_user.email})

    # is_valid has side-effects that need to run before form.save.
    if not form.is_valid():
        raise ValueError(form.errors)

    form.save(
        from_email=settings.FROM_EMAIL_ADDRESS,
        use_https=settings.LINKS_USE_HTTPS,
        domain_override=domain
    )


class Command(BaseCommand):
    help = 'Send reset-your-password emails to all clients.'

    def handle(self, *args, **kwargs):
        targets = CircusUser.objects.filter(
            user_type=settings.CLIENT_USER_TYPE, is_active=True)

        count = targets.count()
        self.stdout.write("Checking %d client accounts...\n" % (count,))
        passed = []
        failed = []
        for i, user in enumerate(targets):
            # if the User does not meet this condition, the PasswordResetForm
            # will silently fail for them.
            if not user.has_usable_password():
                self.stdout.write("User ID#%s <%s> password marked unusable" %
                                  (user.id, user.email))
                failed.append(user)
                continue

            passed.append(user)

        if failed:
            self.stdout.write("%s/%s accounts weeded out." %
                              (len(failed), count))

        count = len(passed)
        confirm = input("Really send email to %d users? (y/N)\n" % (count,))
        if not confirm.upper().startswith('Y'):
            self.stdout.write("Aborting.\n")
            return

        count = len(passed)
        for i, user in enumerate(passed):
            self.stdout.write("%3d/%d id=%-4d %s\n" % (
                i + 1, count, user.id, user.email
            ))

            send_reset_link(user)

        self.stdout.write("Done.\n")
