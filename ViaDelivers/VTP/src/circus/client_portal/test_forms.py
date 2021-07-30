# -*- coding: utf-8 -*-
from django.test import TestCase

from client_portal.forms import ClientOrderForm
from clients.models import ClientService
from services.managers import TRANSLATION_EDIT_PROOF_SERVICE_TYPE, \
    DTP_SERVICE_TYPE, ATTESTATION_SERVICE_TYPE, IMAGE_LOCALIZATION_SERVICE_TYPE, \
    NOTARIZATION_SERVICE_TYPE
from services.models import ServiceType
from shared.datafactory import create_project


class TestClientOrderForm(TestCase):
    def setUp(self):
        self.project = create_project(self.id())
        self.client = self.project.client
        self.client_poc = self.project.client_poc


    def test_client_services(self):
        # ServiceType.code, ServiceType.available, ClientService.client, ClientService.available
        service_records = [
            # not enabled at all
            (IMAGE_LOCALIZATION_SERVICE_TYPE, False, False, False),
            # has a ClientService, but disabled globally
            (DTP_SERVICE_TYPE, False, True, True),
            # all enabled
            (TRANSLATION_EDIT_PROOF_SERVICE_TYPE, True, True, True),
            # enabled globally, but no ClientService
            (ATTESTATION_SERVICE_TYPE, True, False, False),
            # disabled in ClientService
            (NOTARIZATION_SERVICE_TYPE, True, True, False),
        ]
        expected_services = {
            ServiceType.objects.get(code=TRANSLATION_EDIT_PROOF_SERVICE_TYPE).id
        }
        for code, available, for_client, cs_available in service_records:
            service_type = ServiceType.objects.get(code=code)
            service_type.available = available
            service_type.save()

            if for_client:
                ClientService.objects.create(
                    client=self.client,
                    service=service_type,
                    available=cs_available
                )

        form = ClientOrderForm(instance=self.project, user=self.client_poc)

        self.assertEqual(expected_services,
                         set(pk for (pk, desc) in
                             form.fields["services"].choices))
