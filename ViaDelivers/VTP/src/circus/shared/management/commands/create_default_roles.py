from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.core.management import BaseCommand
from accounts.models import GroupOwner

from shared.group_permissions import DEPARTMENT_ADMINISTRATOR_GROUP, CLIENT_MANAGER_GROUP, CLIENT_APPROVED_USER_GROUP, \
    CLIENT_PROJECT_APPROVER_GROUP, CLIENT_CONTRIBUTOR_GROUP, DEPARTMENT_USER_GROUP, CLIENT_ADMIN_PERMISSIONS, \
    CLIENT_MANAGER_PERMISSIONS, CLIENT_PROJECT_APPROVER_PERMISSIONS, APPROVED_USER_PERMISSIONS, \
    CLIENT_CONTRIBUTOR_PERMISSIONS, CLIENT_USER_PERMISSIONS, CLIENT_USER_CODENAME, APPROVE_PROJECT_CODENAME, \
    CLIENT_MANAGER_CODENAME, BILL_TO_COMPANY_CODENAME, VIEW_COLLEAGUE_DATA_CODENAME, REPORTING_DIRECT_REPORTS_CODENAME,\
    VIEW_CHILD_COMPANY_JOBS_CODENAME, APPROVE_ACCESS_REQUESTED_JOBS_CODENAME, CLIENT_ADMIN_ACCESS_CHILD_DEPT_CODENAME, \
    MGR_VIEW_TEAM_JOBS_CODENAME, CLIENT_MANAGER_TEAM_PERMISSIONS, CLIENT_DEFAULT_LEVEL_GROUP, CLIENT_ORGANIZATION_ADMINISTRATOR_GROUP, \
    CLIENT_ORGANIZATION_ADMINISTRATOR_PERMISSIONS, SECURE_JOB_PERMISSION, MANAGE_USERS_GROUPS_MENU_PERMISSION, CLIENT_NOTIFICATION_GROUP, \
    PROTECTED_HEALTH_INFORMATION_GROUP


def add_permission_to_groups(codename, app_label, model, groups):
    permission = Permission.objects.get_by_natural_key(codename, app_label, model)
    for obj in groups:
        # ok to add repeatedly
        obj.permissions.add(permission)


def clear_permissions(group):
    group.permissions.clear()


class Command(BaseCommand):
    args = ''
    help = 'Populate default permission groups'

    def handle(self, *args, **options):
        try:
            print "starting creating or fetching groups"
            ca, created = Group.objects.get_or_create(name=DEPARTMENT_ADMINISTRATOR_GROUP)
            cm, created = Group.objects.get_or_create(name=CLIENT_MANAGER_GROUP)
            au, created = Group.objects.get_or_create(name=CLIENT_APPROVED_USER_GROUP)
            cpa, created = Group.objects.get_or_create(name=CLIENT_PROJECT_APPROVER_GROUP)
            cc, created = Group.objects.get_or_create(name=CLIENT_CONTRIBUTOR_GROUP)
            cu, created = Group.objects.get_or_create(name=DEPARTMENT_USER_GROUP)
            cd, created = Group.objects.get_or_create(name=CLIENT_DEFAULT_LEVEL_GROUP)
            co, created = Group.objects.get_or_create(name=CLIENT_ORGANIZATION_ADMINISTRATOR_GROUP)
            cn, created = Group.objects.get_or_create(name=CLIENT_NOTIFICATION_GROUP)
            phi, created = Group.objects.get_or_create(name=PROTECTED_HEALTH_INFORMATION_GROUP)

            # Need to create the same groups in accounts_groupowner table
            current_user_groups = Group.objects.all()
            for group in current_user_groups:
                group_owner, created = GroupOwner.objects.get_or_create(
                    group_id=group.id,
                )

        except:
            print "error creating or fetching groups"
            return

        print "starting creating or fetching Permission"

        # permission to control whether a user just sees their own projects and data,
        # or whether they can see other user data in the same client
        ct = ContentType.objects.get(model='client', app_label='clients')
        Permission.objects.get_or_create(content_type=ct, codename=VIEW_COLLEAGUE_DATA_CODENAME, defaults=dict(name=u'Can view information belonging to colleagues'))
        # permission to control whether user can only pay with credit card, or whether they can be invoiced
        Permission.objects.get_or_create(content_type=ct, codename=BILL_TO_COMPANY_CODENAME, defaults=dict(name=u'Can use company account to pay for projects'))
        Permission.objects.get_or_create(content_type=ct, codename=CLIENT_MANAGER_CODENAME, defaults=dict(name=u'Can manage projects of users within department'))
        Permission.objects.get_or_create(content_type=ct, codename=APPROVE_ACCESS_REQUESTED_JOBS_CODENAME, defaults=dict(name=u'Can approve the request to access jobs'))
        Permission.objects.get_or_create(content_type=ct, codename=CLIENT_ADMIN_ACCESS_CHILD_DEPT_CODENAME, defaults=dict(name=u'Can client admin access child departments'))
        Permission.objects.get_or_create(content_type=ct, codename=MANAGE_USERS_GROUPS_MENU_PERMISSION, defaults=dict(name=u'Can manage as Client Adminstrator'))

        pt = ContentType.objects.get(model='project', app_label='projects')
        Permission.objects.get_or_create(content_type=pt, codename=APPROVE_PROJECT_CODENAME, defaults=dict(name=u'Can approve projects inside organization'))
        Permission.objects.get_or_create(content_type=pt, codename=CLIENT_USER_CODENAME, defaults=dict(name=u'Can view projects inside organization'))
        Permission.objects.get_or_create(content_type=pt, codename=VIEW_CHILD_COMPANY_JOBS_CODENAME, defaults=dict(name=u'Can Parent company view child company jobs'))
        Permission.objects.get_or_create(content_type=pt, codename=MGR_VIEW_TEAM_JOBS_CODENAME, defaults=dict(name=u'Can manager view their team members jobs'))
        Permission.objects.get_or_create(content_type=pt, codename=SECURE_JOB_PERMISSION, defaults=dict(name=u'Can secure job team members access the secure job'))

        dt = ContentType.objects.get(model='clientmanager', app_label='dwh_reports')
        Permission.objects.get_or_create(content_type=dt, codename=REPORTING_DIRECT_REPORTS_CODENAME, defaults=dict(name=u'Can manager access reports of their direct reports'))

        for group in [ca, cu, cpa, cm]:
            clear_permissions(group)

        for perm in CLIENT_USER_PERMISSIONS:
            add_permission_to_groups(perm['codename'], perm['app_label'], perm['model'], [ca, cc, au, cu, cm, cpa])

        for perm in CLIENT_CONTRIBUTOR_PERMISSIONS:
            add_permission_to_groups(perm['codename'], perm['app_label'], perm['model'], [ca, cc, au, cm, cpa])

        for perm in APPROVED_USER_PERMISSIONS:
            add_permission_to_groups(perm['codename'], perm['app_label'], perm['model'], [ca, au, cu, cm, cpa])

        for perm in CLIENT_PROJECT_APPROVER_PERMISSIONS:
            add_permission_to_groups(perm['codename'], perm['app_label'], perm['model'], [ca, cpa])

        for perm in CLIENT_MANAGER_PERMISSIONS:
            add_permission_to_groups(perm['codename'], perm['app_label'], perm['model'], [ca, cm])

        for perm in CLIENT_ADMIN_PERMISSIONS:
            add_permission_to_groups(perm['codename'], perm['app_label'], perm['model'], [ca])

        for perm in CLIENT_MANAGER_TEAM_PERMISSIONS:
            add_permission_to_groups(perm['codename'], perm['app_label'], perm['model'], [cm])

        for perm in CLIENT_ORGANIZATION_ADMINISTRATOR_PERMISSIONS:
            add_permission_to_groups(perm['codename'], perm['app_label'], perm['model'], [co])
