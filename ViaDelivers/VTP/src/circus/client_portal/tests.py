from django.test import TestCase
from django.core.urlresolvers import reverse

from shared.datafactory import create_project
from services.models import Locale
from projects.states import STARTED_STATUS


class TestClientPortalViews(TestCase):
    def setUp(self):
        pass

    def test_detail_view(self):
        corsican = Locale.objects.get(lcid=1155)  # description="Corsican"
        faroese = Locale.objects.get(lcid=1080)  # description="Faroese"

        self.project = create_project(
            u'Super Detail Test Project',
            targets=[corsican, faroese],
            status=STARTED_STATUS
        )

        self.client.login(email="client@test.com", password="test")
        url = reverse('client_project_detail', kwargs={'pk': self.project.id})
        response = self.client.get(url)

        self.assertEquals(response.status_code, 200)
        self.assertContains(response, "Corsican")
        self.assertContains(response, "Faroese")


# TODO Test With Multiple Client Projects
# Make sure only one the right Client's projects appear in the view.
