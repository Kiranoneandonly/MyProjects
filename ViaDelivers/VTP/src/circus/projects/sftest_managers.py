# -*- coding: utf-8 -*-
from decimal import Decimal
from django.test import TestCase
from accounts.models import SalesforceUser
from people.models import SalesforceAccount

from projects.models import SalesforceOpportunity
from projects.managers import SalesforceOpportunityManager
from shared.datafactory import create_project, create_via_user

# assume salesforce is already set up with the Developer's Edition accounts
# and contacts.
ACCOUNT_NAME = "sForce"


class TestSalesforceOpportunityManager(TestCase):
    def test_is_manager(self):
        self.assertIsInstance(SalesforceOpportunity.objects,
                              SalesforceOpportunityManager)

    def test_create_for_project(self):
        user = SalesforceUser.objects.first()
        account = SalesforceAccount.objects.get(name=ACCOUNT_NAME)
        contact = account.contacts.first()

        account_exec = create_via_user('ae@via.example.com',
                                       salesforce_user_id=user.pk)[0]

        project = create_project(self.id(), account_executive=account_exec)
        project.client.salesforce_account_id = account.pk
        project.client.save()

        project.client_poc.salesforce_contact_id = contact.pk
        project.client_poc.save()

        price = Decimal('249999.97')
        project.price = lambda speed=None: price

        opportunity = SalesforceOpportunity.objects.create_for_project(project)
        # salesforce doesn't support the transaction rollback thing used
        # by django's TestCase, so clean up after ourselves.
        self.addCleanup(opportunity.delete)

        contact_roles = list(opportunity.contact_roles.all())
        self.addCleanup(lambda: [cr.delete() for cr in contact_roles])

        self.assertEqual(18, len(opportunity.pk))
        self.assertEqual(opportunity.pk, project.salesforce_opportunity_id)

        self.assertEqual(1, len(contact_roles))
        self.assertEqual(contact, contact_roles[0].contact)
