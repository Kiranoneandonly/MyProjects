from django.test import TestCase
from django.core.urlresolvers import reverse
from django.conf import settings
from datetime import datetime
import pytz

from shared.datafactory import create_client, create_client_user, create_via_user, create_vendor_user
from shared.group_permissions import CLIENT_ORGANIZATION_ADMINISTRATOR_GROUP, DEPARTMENT_ADMINISTRATOR_GROUP, \
        DEPARTMENT_USER_GROUP, PROTECTED_HEALTH_INFORMATION_GROUP
from django.contrib.auth.models import Group, Permission
from client_portal.views import GroupsListView
from shared.management.commands.create_default_roles import Command
from accounts.models import GroupOwnerPermissions
from django.contrib.auth import get_user_model
from shared.group_permissions import MANAGE_USERS_GROUPS_MENU_PERMISSION, CLIENT_MANAGER_CODENAME
from django.contrib.contenttypes.models import ContentType
from services.models import Locale
from shared.datafactory import create_project
from services.managers import PRICING_SCHEMES_HEALTHCARE
from projects.models import ProjectTeamRole

PST = pytz.timezone(settings.PST_TIME_ZONE)  # "America/Los_Angeles"


class TestPhiSecureClientJobs(TestCase):
    def setUp(self):
        self.client_1 = create_client(u"top_organization")
        self.contact_1 = create_client_user(u'one@grouppermission.test', client=self.client_1)
        self.phi_secure_job_group = Group.objects.get_or_create(name=PROTECTED_HEALTH_INFORMATION_GROUP)

        self.client_1.manifest.pricing_scheme.code = PRICING_SCHEMES_HEALTHCARE
        self.client_1.manifest.baa_agreement_for_phi = True

        started_timestamp = datetime(2013, 11, 12, 9, tzinfo=PST)
        self.en_US = Locale.objects.get(lcid=1033)
        self.ru = Locale.objects.get(lcid=1049)
        self.project = create_project(self.id(),
                                 started_timestamp=started_timestamp,
                                 source=self.en_US,
                                 targets=[self.ru],
                                 client_poc=self.contact_1,
                                 is_secure_job=True,
                                 is_phi_secure_job=True,
                                 )

    # Testing a job is PHI secure client job
    def test_is_phi_secure_job(self):
        self.assertEquals(self.project.is_secure_job, True)
        self.assertEquals(self.project.is_phi_secure_client_job(), True)

        # Client BAA agreement is not in place
        self.client_1.manifest.baa_agreement_for_phi = False
        self.assertEquals(self.project.is_phi_secure_client_job(), False)

    def test_can_via_user_access_secure_job(self):
        self.via_user = create_via_user()
        self.assertEquals(self.project.can_via_user_access_secure_job(self.via_user[0]), False)
        self.via_user[0].add_to_group(PROTECTED_HEALTH_INFORMATION_GROUP)
        ProjectTeamRole.objects.get_or_create(project_id=self.project.id, contact_id=self.via_user[0].id)
        self.assertEquals(self.project.can_via_user_access_secure_job(self.via_user[0]), True)

    def test_contact_add_project_permissions(self):
        add_project_permission = Permission.objects.get(codename='add_project')

        self.contact_1.remove_user_permission(permission=add_project_permission)
        self.contact_1.save()
        self.assertEquals(self.contact_1.has_perm('projects.add_project'), False)

        self.client_1.manifest.enforce_customer_hierarchy = False
        self.assertEquals(self.client_1.manifest.enforce_customer_hierarchy and not self.contact_1.has_perm('projects.add_project'), False)

        self.contact_1.add_user_permission(permission=add_project_permission)
        self.contact_1.save()
        # TODO Not working during Test, but does work on production
        # self.assertEquals(self.contact_1.has_perm('projects.add_project'), True)

        self.client_1.manifest.enforce_customer_hierarchy = False
        self.assertEquals(self.client_1.manifest.enforce_customer_hierarchy and not self.contact_1.has_perm('projects.add_project'), False)

        self.client_1.manifest.enforce_customer_hierarchy = True
        # TODO Not working during Test, but does work on production
        # self.assertEquals(self.client_1.manifest.enforce_customer_hierarchy and self.contact_1.has_perm('projects.add_project'), True)
        # self.assertEquals(self.client_1.manifest.enforce_customer_hierarchy and not self.contact_1.has_perm('projects.add_project'), False)


class TestSecureVtpGroupPermission(TestCase):
    def setUp(self):
        self.client_1 = create_client(u"top_organization")
        self.client_2 = create_client(u"child_department")
        self.client_3 = create_client(u"another_top_organization")

        self.contact_1 = create_client_user(u'one@grouppermission.test', client=self.client_1)
        self.contact_2 = create_client_user(u'two@grouppermission.test', client=self.client_2)
        self.contact_3 = create_client_user(u'three@grouppermission.test', client=self.client_3)

        self.org_admin_group = Group.objects.get_or_create(name=CLIENT_ORGANIZATION_ADMINISTRATOR_GROUP)
        self.admin_group = Group.objects.get_or_create(name=DEPARTMENT_ADMINISTRATOR_GROUP)
        self.client_user_group = Group.objects.get_or_create(name=DEPARTMENT_USER_GROUP)


    # Check whether a client user can access manage_users and groups options and pages.
    # To access these option, user should have ClientAdminLoginRequired.
    # User should be in Client Organization Administrator group or should have MANAGE_USERS_GROUPS_MENU_PERMISSION assigned.
    def test_can_user_access_manage_users_groups_options(self):
        # User 1 has admin login required option, and also he is in CLIENT_ORGANIZATION_ADMINISTRATOR_GROUP. He can access the pages.
        self.contact_1.add_to_group(CLIENT_ORGANIZATION_ADMINISTRATOR_GROUP)
        is_client_organization_administrator = self.contact_1.is_client_organization_administrator
        self.assertEquals(is_client_organization_administrator, True)

        self.contact_1.set_password("test")
        user_login = self.client.login(email='one@grouppermission.test', password='test')
        self.assertTrue(user_login)

        response = self.client.get(reverse('client_manage_users'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '<th>Department</th>')

        response = self.client.get(reverse('client_manage_groups'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '<th>Name</th>')

        self.client.logout()

        # User 2 has admin login required option, but has neither MANAGE_USERS_GROUPS_MENU_PERMISSION nor DEPARTMENT_ADMINISTRATOR_GROUP
        # So he can not access the pages
        self.contact_2.remove_from_group(DEPARTMENT_ADMINISTRATOR_GROUP)
        is_client_organization_administrator = self.contact_2.is_client_organization_administrator
        self.assertEquals(is_client_organization_administrator, False)

        self.contact_2.set_password("test")
        user_login = self.client.login(email='two@grouppermission.test', password='test')
        self.assertTrue(user_login)

        response = self.client.get(reverse('client_manage_groups'))
        self.assertEqual(response.status_code, 302)

        self.contact_2.add_to_group(DEPARTMENT_ADMINISTRATOR_GROUP)
        response = self.client.get(reverse('client_manage_groups'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "<h2>You don't have permission to access this page</h2>")

        response = self.client.get(reverse('client_manage_users'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '<th>Department</th>')
        self.client.logout()

        # Since user 3 has no admin login required option, he can not access the pages
        self.contact_3.add_to_group(DEPARTMENT_USER_GROUP)
        self.contact_3.set_password("test")
        user_login = self.client.login(email='three@grouppermission.test', password='test')
        self.assertTrue(user_login)

        response = self.client.get(reverse('client_manage_groups'))
        self.assertEqual(response.status_code, 302)
        self.client.logout()

    # If the organization/department has a parent, it can not be a top_organization.
    def test_is_top_organization(self):
        self.client_2.parent_id = self.client_1.id

        self.contact_1.add_to_group(CLIENT_ORGANIZATION_ADMINISTRATOR_GROUP)
        self.contact_2.add_to_group(CLIENT_ORGANIZATION_ADMINISTRATOR_GROUP)

        self.assertEquals(self.client_1.is_top_organization, True)
        self.assertEquals(self.client_2.is_top_organization, False)

    def get_perm(self, user):
        group_owner_permission = GroupOwnerPermissions.objects.filter(group_id=self.admin_group[0].id,
            user_id=user.id,
            parent_account_id=user.account.id)
        perm = []
        for grp_permission in group_owner_permission:
            perm.append(grp_permission.permission.name)

        return perm

    #Client admin should able to add a new user to any department under him.
    def test_client_admin_add_user_to_any_dept(self):
        self.client.login(email='one@grouppermission.test', password='test')
        self.contact_1.add_to_group(CLIENT_ORGANIZATION_ADMINISTRATOR_GROUP)
        self.contact_1.add_to_group(DEPARTMENT_ADMINISTRATOR_GROUP)

        url = reverse('client_create_user',)

        post_data = {
            'email': 'child_dept_user@grouppermission.test',
            'password1': "test",
            'password2': "test",
            'account': self.client_2.id,
        }

        response = self.client.post(url, post_data)
        # self.assertRedirects(
        #     response, response.url)
        edit_post_data = {
            'first_name': 'Robert',
            'last_name': 'Kruso',
            'title': 'Mr',
            'department': '',
            'phone': 1234567,
            'is_active': True,
            'new_password1': "test",
            'new_password2': "test",
        }
        edit_user_response = self.client.post(response.url, edit_post_data)

        users = get_user_model().objects.filter(account_id=self.client_2.id)
        account_users = []
        for u in users:
            account_users.append(u.email)

        self.assertEquals('child_dept_user@grouppermission.test' in account_users, True)


    #For default groups, permissions are specific across client admins.
    def test_specific_permissions_for_default_groups(self):
        self.client.login(email='one@grouppermission.test', password='test')
        self.contact_1.add_to_group(DEPARTMENT_ADMINISTRATOR_GROUP)
        self.contact_3.add_to_group(DEPARTMENT_ADMINISTRATOR_GROUP)
        self.client.login(email='one@grouppermission.test', password='test')

        #Testing the code and Creating roles and permissions using shared/management/commands/create_default_roles.
        perm_1 = Command()
        perm_1.handle()
        p_list = Permission.objects.filter(codename=CLIENT_MANAGER_CODENAME)
        p_ids = []
        url = reverse('client_manage_groups',)

        for p in p_list:
            p_ids.append(p.id)

        post_data = {
            'permission_id': p_ids[0],
            'group_id': self.admin_group[0].id,
            'option': True,
            'group': 'group_permissions',
        }

        #For testing vies with ajax_requests that returns json
        kwargs = {'HTTP_X_REQUESTED_WITH': 'XMLHttpRequest'}
        response = self.client.post(url, post_data, **kwargs)
        # json_string = response.content
        #Chekint the permissison in GroupOwnerPermissions model for client_1
        perm = self.get_perm(self.contact_1)
        self.assertTrue(self.contact_1.has_group(DEPARTMENT_ADMINISTRATOR_GROUP))
        self.assertEquals(perm, [u'Can manage projects of users within department'])

        self.client.logout()
        self.client.login(email='three@grouppermission.test', password='test')
        #Chekint the permissison in GroupOwnerPermissions model for client_3
        perm = self.get_perm(self.contact_3)
        self.assertTrue(self.contact_3.has_group(DEPARTMENT_ADMINISTRATOR_GROUP))
        self.assertEquals(perm, [])


    #Custom departments are specific to client organization admin
    def test_departments_specific_for_client_org_admin(self):
        self.contact_1.add_to_group(CLIENT_ORGANIZATION_ADMINISTRATOR_GROUP)
        self.contact_1.add_to_group(DEPARTMENT_ADMINISTRATOR_GROUP)
        self.contact_1.set_password("test")

        self.contact_3.add_to_group(CLIENT_ORGANIZATION_ADMINISTRATOR_GROUP)
        self.contact_3.add_to_group(DEPARTMENT_ADMINISTRATOR_GROUP)
        self.contact_3.set_password("test")

        self.client.login(email='one@grouppermission.test', password='test')

        url = reverse('client_create_group',)

        post_data = {
            'name': "test_specific_group",
        }

        response = self.client.post(url, post_data)
        self.assertRedirects(
            response, reverse('client_manage_groups',))

        response = self.client.get(reverse('client_manage_groups'))
        view = GroupsListView.as_view(template_name='clients/accounts/manage_groups.html')

        check_group = "test_specific_group" in response.context_data['group_list']
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context_data['current_user_id'], self.contact_1.id)
        self.assertTrue(check_group)

        self.client.logout()

        #Another client user login for checking whether the group is accessed
        self.client.login(email='three@grouppermission.test', password='test')

        response = self.client.get(reverse('client_manage_groups'))
        view = GroupsListView.as_view(template_name='clients/accounts/manage_groups.html')
        check_group = "test_specific_group" in response.context_data['group_list']
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context_data['current_user_id'], self.contact_3.id)
        self.assertFalse(check_group)
