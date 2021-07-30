# -*- coding: utf-8 -*-
from django.test import TestCase
from accounts.models import CircusUser
from localization_kits.authorization import may_edit_project_loc_kit, \
    may_view_project_loc_kit
from projects.models import Project
from projects.states import TASK_ACTIVE_STATUS
from shared.datafactory import create_project, create_via_user, \
    create_vendor_user, TaskFactory, create_client, create_client_user
from vendors.models import Vendor


class TestMayEditLocKit(TestCase):
    def setUp(self):
        self.project = create_project(self.id())


    def test_staff_may_edit(self):
        via_user = create_via_user()[0]
        self.assertTrue(may_edit_project_loc_kit(self.project, via_user))


    def test_client_poc_may_edit(self):
        # Reload this user to get an authentic representation of Client and
        # Account attributes.
        project = Project.objects.select_related().get(id=self.project.id)
        client_user = CircusUser.objects.get(id=self.project.client_poc.id)
        self.assertTrue(may_edit_project_loc_kit(project, client_user))


    def test_client_coworker_may_edit(self):
        # a new user, but within the same client as the project
        coworker_user = create_client_user(u"waseem@example.com",
                                           self.project.client)
        self.assertTrue(may_edit_project_loc_kit(self.project, coworker_user))


    def test_client_other_may_not_edit(self):
        another_client = create_client(u"Sunshine Brigade")
        other_client_user = create_client_user(u"other-client@example.com",
                                               another_client)
        self.assertFalse(may_edit_project_loc_kit(self.project,
                                                  other_client_user))


    def test_vendor_may_not_edit(self):
        vendor_user = create_vendor_user()[0]
        self.assertFalse(may_edit_project_loc_kit(self.project, vendor_user))
        # TODO: test with a vendor user which would pass may_view



class TestMayViewLocKit(TestCase):

    def setUp(self):
        # The viewers of a loc kit include any vendors assigned to any task
        # on the loc kit's project.
        self.project = create_project(self.id())
        task_factory = TaskFactory(self.project)
        self.tep_task = task_factory.create_tep_task(TASK_ACTIVE_STATUS)
        self.fa_task = task_factory.create_fa_task(TASK_ACTIVE_STATUS,
                                                   predecessor=self.tep_task)
        self.via_user = create_via_user()[0]
        self.fa_task.assigned_to = self.via_user

        # for perversity, ensure via_user.id == other_vendor.id
        # (to test to make sure we're not conflating things due to false
        # Task.assignee_object_id equivalences.)
        # This test scenario is currently the only thing covering
        # TaskManager.get_user_tasks; if you simplify here, make sure to give
        # that its own test cases.
        self.other_vendor_user = create_vendor_user()[0]
        other_vendor = self.other_vendor_user.account

        # self.assertEqual(self.via_user.id, other_vendor.id)

        vendor = Vendor.objects.create(
            name="Tim's Translation Team",
            account_type=other_vendor.account_type,
        )
        self.vendor_user = create_vendor_user('howard@example.com', vendor)[0]
        self.tep_task.assigned_to = vendor

        self.tep_task.save()
        self.fa_task.save()

        # make another project and task for other-vendor
        other_project = Project.objects.create(
            name="sabotage",
            status=self.project.status,
            client=self.project.client,
            client_poc=self.project.client_poc,
            source_locale=self.project.source_locale,
            current_user=self.project.client_poc_id
        )
        other_project.target_locales.add(*self.project.target_locales.all())
        other_task_factory = TaskFactory(other_project)
        other_task_factory.create_tep_task(TASK_ACTIVE_STATUS,
                                           assigned_to=other_vendor)


    def test_vendor_may_view(self):
        self.assertTrue(may_view_project_loc_kit(self.project, self.vendor_user))


    def test_other_vendor_may_not_view(self):
        self.assertFalse(may_view_project_loc_kit(self.project, self.other_vendor_user))


    def test_staff_may_view(self):
        self.assertTrue(may_view_project_loc_kit(self.project, self.via_user))


    def test_client_poc_may_view(self):
        # Reload this user to get an authentic representation of Client and
        # Account attributes.
        project = Project.objects.select_related().get(id=self.project.id)
        client_user = CircusUser.objects.get(id=self.project.client_poc.id)
        self.assertTrue(may_view_project_loc_kit(project, client_user))


    def test_client_coworker_may_view(self):
        # a new user, but within the same client as the project
        coworker_user = create_client_user(u"waseem@example.com", self.project.client)
        self.assertTrue(may_view_project_loc_kit(self.project, coworker_user))


    def test_client_other_may_not_edit(self):
        another_client = create_client(u"Sunshine Brigade")
        other_client_user = create_client_user(u"other-client@example.com",
                                               another_client)
        self.assertFalse(may_view_project_loc_kit(self.project,
                                                  other_client_user))
