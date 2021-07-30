from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management import BaseCommand


DEFAULT_ADMIN_EMAIL = 'admin@viadelivers.com'
DEFAULT_PM_EMAIL = 'TranslationCoordinators_test@viadelivers.com'
DEFAULT_SALES_EMAIL = 'AccountExecutive_test@viadelivers.com'

DEFAULT_USERS = [
    {
        'email': DEFAULT_ADMIN_EMAIL,
        'password': 'admin',
        'first_name': 'Admin',
        'last_name': 'User',
        'is_staff': True,
        'is_admin': True,
    },
    {
        'email': DEFAULT_PM_EMAIL,
        'password': 'abcd',
        'first_name': 'Translation',
        'last_name': 'Coordinator Test',
        'is_staff': True,
        'is_admin': False,
    },
    {
        'email': DEFAULT_SALES_EMAIL,
        'password': 'abcd',
        'first_name': 'Business',
        'last_name': 'Account Test',
        'is_staff': True,
        'is_admin': False,
    }
]

def make_default_users():
    for user in DEFAULT_USERS:
        try:
            user_obj = get_user_model().objects.get(email=user['email'])
            print "found existing user {0}".format(user['email'])
        except:
            print "creating user {0}".format(user['email'])
            user_obj = get_user_model().objects.create_user(user['email'], user['password'])

        user_obj.is_active = True
        user_obj.is_staff = user['is_staff']
        user_obj.is_superuser = user['is_admin']
        user_obj.user_type = settings.VIA_USER_TYPE
        user_obj.first_name = user['first_name']
        user_obj.last_name = user['last_name']
        user_obj.set_password(user['password'])
        user_obj.save()


class Command(BaseCommand):
    args = ''
    help = 'Populate default users and roles'

    def handle(self, *args, **options):
        make_default_users()

