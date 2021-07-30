from datetime import datetime
from decimal import Decimal
import io
from unittest import TestCase

from django.contrib.auth.models import Group
from django.core.urlresolvers import reverse
from django.test import TestCase as DjangoTestCase, RequestFactory
from django.contrib.auth.forms import PasswordResetForm
from django.conf import settings
from django.utils import timezone
from django.utils.timezone import get_default_timezone
from mock import Mock, patch, create_autospec, DEFAULT
import pytz
import unicodecsv

from accounts.forms import CircusUserCreationForm
from accounts.models import CircusUser
import client_portal.views
from client_portal.views import CreateUserView, send_new_user_password_reset, \
    ProjectListViewExport
from clients.models import ClientContact, Client
from finance import payflow
from finance.models import CA_PAYMENT_CHOICE, CC_PAYMENT_CHOICE
from localization_kits.models import FileAsset, SOURCEFILE_ASSET
from people.models import ContactRole
from projects.models import Project, EXPRESS_SPEED
from projects.states import CREATED_STATUS, STARTED_STATUS, QUOTED_STATUS, get_reversed_status, OVERDUE_STATUS, \
    VIA_STATUS_DETAIL, ALL_STATUS
from services.models import Locale
from shared.datafactory import create_project, create_client
from shared.group_permissions import DEPARTMENT_ADMINISTRATOR_GROUP
from shared.management.commands.create_lookups import CONTACT_ROLES
from shared.unittest_help import ViewTestCase, PageObject


UTC = pytz.utc
PST = pytz.timezone(settings.PST_TIME_ZONE)  # "America/Los_Angeles"
via_tz = get_default_timezone()

class TestCreateUserView(TestCase):
    @patch("client_portal.views.send_new_user_password_reset")
    def test_form_valid_emails_new_user(self, send_new_user_password_reset):
        new_user = Mock(CircusUser, name="New User")
        request = Mock(name="request")

        view = CreateUserView(request=request)
        view.get_success_url = lambda: "SUCCESS_URL"

        form = Mock(CircusUserCreationForm,
                    # TODO: I think form_valid doesn't need to explicitly do
                    # this, as it's in the ModelForm.save too.
                    cleaned_data={'password1': 'secret'})
        form.save.return_value = new_user

        # Invoke method under test
        view.form_valid(form)

        # Assertions
        called_user, = send_new_user_password_reset.call_args[0]
        self.assertEqual(called_user, new_user)


class TestSendNewUserPasswordReset(TestCase):
    def test_password_reset_to_new_user_email(self):
        forms = []

        class FormSpy(PasswordResetForm):
            """keep a list of created forms so we can spy on them."""
            # It seems like with as extensive as Mock is, it we oughta be
            # able to do this with standard Mock machinery, but I can't figure
            # out how to get return values from wrapped objects.
            def __init__(self, *a, **kw):
                super(FormSpy, self).__init__(*a, **kw)
                self.save = Mock(wraps=self.save)
                forms.append(self)

        form_constructor = Mock(wraps=FormSpy)
        new_user_email = "new_user@example.com"
        new_user = Mock(CircusUser, name="New User",
                        is_active=True,
                        email=new_user_email)
        https = settings.LINKS_USE_HTTPS

        with patch('client_portal.views.PasswordResetForm', form_constructor):
            # noinspection PyTypeChecker
            send_new_user_password_reset(new_user)

            form = forms[0]

            self.assertEqual(form['email'].value(), new_user_email)
            form.save.assert_called_once_with(
                email_template_name='notifications/new_user_password_reset_email.txt',
                subject_template_name='notifications/new_user_password_reset_subject.txt',
                from_email=settings.FROM_EMAIL_ADDRESS,
                use_https=https
            )


class TestProjectListViewExport(DjangoTestCase):
    maxDiff = None

    def test_csv(self):
        timezone.activate(PST)

        view = ProjectListViewExport(status=ALL_STATUS)
        targets = [Locale.objects.get_or_none(lcid=lcid) for lcid in (1049, 8251)]
        est_due = datetime(2013, 12, 24, 15, tzinfo=PST)
        job_due = datetime(2013, 12, 30, 15, tzinfo=PST)
        started = datetime(2013, 12, 26, 9, tzinfo=PST)

        project1 = create_project(u'Row One', targets=targets,
                                  started_timestamp=started,
                                  quote_due=est_due, due=job_due)

        reversed_status1 = OVERDUE_STATUS if project1.is_overdue() else get_reversed_status(project1.status)
        project1.workflow = VIA_STATUS_DETAIL[reversed_status1]

        project2 = create_project(u'Row Two', status=CREATED_STATUS,
                                  client_poc=project1.client_poc,
                                  quote_due=est_due)

        reversed_status2 = OVERDUE_STATUS if project1.is_overdue() else get_reversed_status(project1.status)
        project2.workflow = VIA_STATUS_DETAIL[reversed_status2]

        projects = [project1, project2]

        project1.price = lambda: Decimal('98.76')

        loc_kit = project1.kit
        FileAsset.objects.create(orig_name="beta.rtf", asset_type=SOURCEFILE_ASSET, kit=loc_kit)
        FileAsset.objects.create(orig_name="alpha.txt", asset_type=SOURCEFILE_ASSET, kit=loc_kit)

        expected_headers = [
            u'\ufeffJob', 'Speed', 'Warnings', 'Approved', 'Workflow', 'Purchase Order', 'Reference', 'Files',
            'Source', 'Targets', 'Price', 'Requester', 'Department', 'PM', 'AE', 'Estimate', 'Started',
            'Due', 'Delivered'
        ]

        expected_record = {
            u'\ufeffJob': unicode(projects[0].job_number),
            u'Speed': u'standard',
            u'Warnings': u'Job Overdue!',
            u'Approved': u'False',
            u'Workflow': unicode(projects[0].workflow.get('text')),
            u'Purchase Order': u'',
            u'Reference': u'',
            u'Files': u'alpha.txt, beta.rtf',
            u'Source': u'English',
            u'Targets': u'Russian, Samoan',
            u'Price': u'98.76',
            u'Requester': u'client@test.com',
            u'Department': u'',
            u'PM': u'',
            u'AE': u'',
            u'Estimate': u'2013-12-24',
            u'Started': u'2013-12-26',
            u'Due': u'2013-12-30',
            u'Delivered': u''
        }

        content = view.csv(projects)
        csvfile = io.BytesIO(content)

        # check headers
        reader = unicodecsv.DictReader(csvfile)
        self.assertEqual(expected_headers, reader.fieldnames)

        # check project 1
        project_record = reader.next()
        self.assertEqual(expected_record, project_record)

        # check project 2
        project_record = reader.next()
        # not-yet-started project should have an estimate overdue warning
        self.assertEqual(project2.client_warnings(),
                         project_record['Warnings'])

        # that should be all
        self.assertRaises(StopIteration, reader.next)


    def test_queryset_search(self):
        view = ProjectListViewExport()
        req_factory = RequestFactory()
        req = req_factory.get('?q=needle')
        req.user = create_autospec(CircusUser, instance=True)
        view.request = req
        view.kwargs = {'status': 'all'}

        # expect results to be in descending order by job_number
        expected_queryset = [
            create_autospec(Project, instance=True, job_number='789'),
            create_autospec(Project, instance=True, job_number='456'),
            create_autospec(Project, instance=True, job_number='123'),
        ]

        # have get_matches return a shuffled order, so we can tell if sort works
        matched_projects = expected_queryset[1:] + expected_queryset[0:1]
        mock_get_matches = create_autospec(view._get_matches)
        mock_get_matches.return_value = matched_projects
        view._get_matches = mock_get_matches

        with patch('client_portal.views._client_projects',
                   autospec=True) as mock_client_projects:
            projects = mock_client_projects.return_value

            queryset = view.get_queryset()

            mock_get_matches.assert_called_once_with(projects, 'needle')

        self.assertEqual(expected_queryset, queryset)


    def test_queryset_without_search(self):
        view = ProjectListViewExport()
        req_factory = RequestFactory()
        req = req_factory.get('/')
        req.user = create_autospec(CircusUser, instance=True)
        view.request = req
        view.kwargs = {'status': 'all'}

        mock_get_matches = create_autospec(view._get_matches)
        view._get_matches = mock_get_matches

        with patch('client_portal.views._client_projects',
                   autospec=True) as mock_client_projects:
            queryset = view.get_queryset()

            # no search query, don't run get_matches
            self.assertEqual([], mock_get_matches.mock_calls)

            # queryset is as determined by _client_projects()
            self.assertEqual(mock_client_projects.return_value, queryset)



class TestQuoteView(ViewTestCase):
    def setUp(self):
        self.project = create_project(self.id(), status=QUOTED_STATUS)
        self.client.login(email='client@test.com', password='test')


    def test_post_place_order_with_invoice(self):
        project = self.project
        url = reverse('client_quote', args=(project.id,))

        post_data = {
            'place_order': 'submit',
            'payment_method': CA_PAYMENT_CHOICE,
            'ca_invoice_number': '012345678901234567890123456789012345678901234567890123456789',
            'accept_terms_and_conditions': 'true',
            'project_speed': EXPRESS_SPEED
        }

        # To start a project, it either needs to have tasks defined ... or we fake it.
        # noinspection PyUnresolvedReferences
        with patch.multiple(
                'projects.models.Project', tasks_are_priced=DEFAULT,
                start_project=DEFAULT,
                autospec=True) as patcher, \
                patch('projects.models.SalesforceOpportunity', autospec=True):
            patcher['tasks_are_priced'].return_value = True
            response = self.client.post(url, post_data)

            self.assertNoFormError(response)

            self.assertTrue(patcher['start_project'].called)

        self.assertRedirects(
            response, reverse('client_project_detail', args=(project.id,)))

        project = Project.objects.select_related().get(id=project.id)
        payment = project.payment_details
        self.assertEqual(CA_PAYMENT_CHOICE, payment.payment_method)
        self.assertEqual('01234567890123456789012345678901234567890123456789', payment.ca_invoice_number[:50])
        self.assertFalse(payment.cc_response_auth_code)

        self.assertTrue(project.approved)
        self.assertTrue(project.quoted)
        self.assertEqual(STARTED_STATUS, project.status)

        # If we ever actually figure out how to test for messages, we could
        # assert that the success message was added.
        # http://stackoverflow.com/questions/16143149/


    def test_post_place_order_with_credit_card(self):
        project = self.project
        url = reverse('client_quote', args=(project.id,))

        post_data = {
            'place_order': 'submit',
            'payment_method': CC_PAYMENT_CHOICE,
            'accept_terms_and_conditions': 'true',
            'project_speed': EXPRESS_SPEED
        }

        # To start a project, it either needs to have tasks defined ... or we
        # fake it.
        # noinspection PyUnresolvedReferences
        with patch.multiple(
                'projects.models.Project', tasks_are_priced=DEFAULT,
                start_project=DEFAULT, autospec=True) as patcher:
            patcher['tasks_are_priced'].return_value = True
            response = self.client.post(url, post_data)

            self.assertNoFormError(response)

            self.assertFalse(patcher['start_project'].called)

        self.assertRedirects(
            response, reverse('client_pay', args=(project.id,)))

        project = Project.objects.select_related().get(id=project.id)
        payment = project.payment_details
        self.assertEqual(CC_PAYMENT_CHOICE, payment.payment_method)
        self.assertFalse(payment.ca_invoice_number)
        self.assertFalse(payment.cc_response_auth_code)

        self.assertTrue(project.quoted)

        # This project is *not* to have advanced to Started before the payment
        # goes through.
        self.assertEqual(QUOTED_STATUS, project.status)
        self.assertFalse(project.approved)


class NewPaymentPage(PageObject):
    view_name = 'client_pay'

    @classmethod
    def credentials(cls):
        return {'email': 'client@test.com', 'password': 'test'}

    def price(self):
        return self.doc(".price")[0].text.strip()



class TestNewPaymentView(ViewTestCase):
    def setUp(self):
        self.project = create_project(self.id(), status=QUOTED_STATUS)

        # patch process_sale to avoid running payments from unit tests
        payflow_patcher = patch('finance.payflow.process_sale', autospec=True)
        self.addCleanup(payflow_patcher.stop)
        self.process_sale = payflow_patcher.start()

        # patch Project.price to avoid building out tasks and pricing tables.
        price_patcher = patch('projects.models.Project.price', autospec=True)
        self.addCleanup(price_patcher.stop)
        self.project_price = price_patcher.start()


    def test_new_payment_get(self):
        self.project_price.return_value = 1098.76

        page = NewPaymentPage.get(self.client, proj_id=self.project.id)

        response = page.response

        self.assert_200(response)

        self.assertEqual(self.project, response.context['project'])
        self.assertTrue(response.context['cc_form'])
        self.assertFalse(response.context['already_paid'])

        self.assertTemplateUsed(
            response, 'clients/order/credit_card_payment_form.html')

        self.assertEqual('$1,098.76', page.price())
        self.assertEqual([], self.process_sale.mock_calls)


    def test_new_payment_post_cancel(self):
        post_data = {'cancel': ''}

        # For this test where we're just checking a redirect and not any HTML,
        # doesn't make sense to construct a Page with the response.
        url = NewPaymentPage.url(proj_id=self.project.id)
        NewPaymentPage.login(self.client)
        response = self.client.post(url, post_data)

        self.assertRedirectsToName(response, 'client_quote',
                                   pk=str(self.project.id))
        self.assertEqual([], self.process_sale.mock_calls)


    def test_new_payment_post_invalid_form(self):
        # form submitted without necessary things like CC#
        post_data = {
            'cardnum': u'',
            'expdate': u'',
        }

        page = NewPaymentPage.post(self.client, post_data, proj_id=self.project.id)
        response = page.response

        self.assert_200(response)

        self.assertEqual(self.project, response.context['project'])
        self.assertTrue(response.context['cc_form'])

        self.assertFormError(response, 'cc_form', 'cardnum',
                             u'This field is required.')

        self.assertTemplateUsed(
            response, 'clients/order/credit_card_payment_form.html')

        self.assertEqual([], self.process_sale.mock_calls)


    def test_new_payment_post_changed_price(self):
        price = 999.90
        self.project_price.return_value = price

        post_data = {
            'cardnum': u'4111111111111111',
            'expdate': u'01/2024',
            'security_code': '',
            'street': u'700 SW Taylor Street, Suite 300',
            'city': u'Portland',
            'zip': u'97205',
            'state': 'OR',
            'charge': '',
            # A much lower price than the current one!
            'price': '19.95',
        }

        page = NewPaymentPage.post(self.client, post_data,
                                   proj_id=self.project.id)
        response = page.response

        self.assert_200(response)

        self.assertEqual(self.project, response.context['project'])

        self.assertFormError(response, 'cc_form', None,
                             u'The project price has changed.')

        self.assertEqual([], self.process_sale.mock_calls)


    def test_new_payment_post_failed_transaction(self):
        price = 234.56
        self.project_price.return_value = price

        respmsg = u"Transaction failed"
        self.process_sale.return_value = payflow.PayflowResponse(
            payflow.GENERAL_ERROR, respmsg, None, None, "XXN")

        post_data = {
            'cardnum': u'4111111111112345',
            'expdate': u'01/2024',
            'security_code': '',
            'street': u'700 SW Taylor Street, Suite 300',
            'city': u'Portland',
            'zip': u'97205',
            'state': 'OR',
            'charge': '',
            'price': str(price)
        }

        page = NewPaymentPage.post(self.client, post_data,
                                   proj_id=self.project.id)
        response = page.response

        self.assert_200(response)

        self.assertEqual(self.project, response.context['project'])
        self.assertTrue(response.context['cc_form'])

        # assertFormError works well, until your error message gets really long
        # and wordy
        form_errors = response.context['cc_form'].non_field_errors()
        self.assertEqual(1, len(form_errors))
        self.assertIn(respmsg, form_errors[0])

        self.assertTemplateUsed(
            response, 'clients/order/credit_card_payment_form.html')

        cc_data = post_data.copy()
        del cc_data['charge']
        del cc_data['price']
        self.assertEqual(price, self.process_sale.call_args[0][0])
        self.assertEqual(cc_data, self.process_sale.call_args[0][1])
        self.assertEqual(1, self.process_sale.call_count)


    def test_new_payment_post_succeed(self):
        price = 234.56
        self.project_price.return_value = price

        respmsg = u"Approved"
        pnref = "8BA4A944"
        self.process_sale.return_value = payflow.PayflowResponse(
            payflow.APPROVED, respmsg, pnref, "001122", "YYY")

        post_data = {
            'cardnum': u'4111111111111111',
            'expdate': u'01/2024',
            'security_code': '',
            'street': u'700 SW Taylor Street, Suite 300',
            'city': u'Portland',
            'zip': u'97205',
            'state': 'OR',
            'charge': '',
            'price': str(price)
        }

        # For this test where we're just checking a redirect and not any HTML,
        # doesn't make sense to construct a Page with the response.
        url = NewPaymentPage.url(proj_id=self.project.id)
        NewPaymentPage.login(self.client)

        with patch('projects.models.Project.transition', autospec=True) \
                as project_transition:
            response = self.client.post(url, post_data)

        self.assertRedirectsToName(response, 'client_project_detail',
                                   pk=str(self.project.id))

        cc_data = post_data.copy()
        del cc_data['charge']
        del cc_data['price']
        self.assertEqual(price, self.process_sale.call_args[0][0])
        self.assertEqual(cc_data, self.process_sale.call_args[0][1])
        self.assertEqual(1, self.process_sale.call_count)

        project = Project.objects.select_related().get(id=self.project.id)
        payment = project.payment_details
        self.assertEqual(CC_PAYMENT_CHOICE, payment.payment_method)
        self.assertEqual(pnref, payment.cc_response_auth_code)
        self.assertFalse(payment.ca_invoice_number)

        self.assertIn(str(price), payment.note)

        project_transition.assert_called_once_with(project, STARTED_STATUS)

    def test_get_project_already_paid(self):
        self.project.payment_details.payment_method = CC_PAYMENT_CHOICE
        self.project.payment_details.cc_response_auth_code = '0b57ac1e'
        self.project.payment_details.save()

        page = NewPaymentPage.get(self.client, proj_id=self.project.id)

        response = page.response

        self.assert_200(response)

        self.assertEqual(self.project, response.context['project'])
        self.assertTrue(response.context['already_paid'])

        self.assertTemplateUsed(
            response, 'clients/order/credit_card_payment_form.html')

        self.assertEqual([], self.process_sale.mock_calls)


class TestUpdateClientAccountView(ViewTestCase):
    def setUp(self):
        # do the datafactory.create_client to make sure all the related models
        # exist (Client AccountType, Target PricingBasis, etc.)
        create_client(u"throwaway")

        roles = [ContactRole(code=code, description=desc) for code, desc in
                 CONTACT_ROLES]
        ContactRole.objects.bulk_create(roles)

        Group.objects.get_or_create(name=DEPARTMENT_ADMINISTRATOR_GROUP)

    def test_notify_on_new_client(self):

        username = 'newclient@example.com'
        user = ClientContact.objects.create(
            user_type=settings.CLIENT_USER_TYPE,
            email=username,
            is_active=True,
            # "Profile Complete" is True when the user has entered their
            # personal information (e.g. first_name).
            # "Registration Complete" happens after the user.account has been
            #     set up.
            profile_complete=True,
            registration_complete=False,
        )
        user.set_password("test")
        # Make new Client account as we'd see for a new client at this step.
        user.account = Client.objects.create_for_user(user)
        user.add_to_group(DEPARTMENT_ADMINISTRATOR_GROUP)
        user.save()

        self.assertTrue(self.client.login(email=username, password='test'))

        account_id = user.account.id

        url = reverse('new_client_organization', args=(account_id,))

        # noinspection PyUnresolvedReferences
        with patch.object(client_portal.views,
                          'notify_via_new_client_account', autospec=True) as notify:
            new_client_name = self.id()

            response = self.client.post(url, {'name': new_client_name})

            self.assertRedirectsToName(response, 'client_dashboard')

            notify.assert_called_once_with(user.account)

            # Assert the model that got passed to the notification has the
            # new values on it.
            called_with_client = notify.call_args[0][0]
            self.assertEqual(new_client_name, called_with_client.name)
