import json
import logging
from django.conf import settings
from django.utils import timezone
import requests
from shared import har
from shared.utils import remove_html_tags

logger = logging.getLogger('circus.' + __name__)

API_HEADERS = {
    'content-type': 'application/json',
    'x-apikey': settings.VIA_DVX_API_KEY
}


class JAMSAPIFailure(Exception):

    def __init__(self, url, response_data=None, http_archive=None, exception=None):
        super(JAMSAPIFailure, self).__init__(url, response_data, http_archive, exception)
        self.url = url
        self.http_archive = http_archive
        self.response_data = response_data
        self.__cause__ = exception


    @classmethod
    def from_http_response(cls, http_response, response_data=None):
        # Instead of figuring out which bits to parse out now, save everything.
        archive = har.request_and_response(http_response,
                                           include_post_body=True)
        return cls(url=http_response.url,
                   response_data=response_data,
                   http_archive=archive)


    @classmethod
    def from_exception(cls, exception, http_request):
        archive = har.request(http_request, include_post_body=True)
        url = http_request.url
        return cls(url=url, http_archive=archive, exception=exception)

    @property
    def api_status(self):
        if self.response_data:
            return self.response_data.get('status')


    def __str__(self):
        status = self.api_status
        name = self.url.replace(settings.VIA_DVX_BASE_URL, '')
        if self.__cause__:
            cause = ' cause:%r' % (self.__cause__,)
        else:
            cause = ''
        return ('<%(cls)s %(name)s status:%(status)s%(cause)s>' % dict(
            name=name,
            cause=cause,
            cls=self.__class__.__name__,
            status=status,
        ))


def import_failed_action(where_are_we=''):
    logger.info('jams_api.engine.import_failed_action: ' + unicode(where_are_we))


def create_jams_job_number(project):

    project_manager_jams_username = project.project_manager.jams_username if project.project_manager else None
    account_executive_jams_username = project.account_executive.jams_username if project.account_executive else None

    data_payload = {
        'vtpID': project.id,
        'jobID': 0,
        'jobNumber': '',
        'jobName': u"{0}".format(project.name),
        'customerID': u"{0}".format(project.client.account_number),
        'customerName': u"{0}".format(project.client.name),
        'orderedBy': u"{0}".format(project.client_poc),
        'clientPO_RefNumber': None,
        'expressFlag': 0,
        'price': 0,
        'clientNotes': u"",
        'pMInstructions': u"",
        'projectManager': u"{0}".format(project_manager_jams_username) if project_manager_jams_username else None,
        'accountExecutive': u"{0}".format(account_executive_jams_username) if account_executive_jams_username else None,
        'estimateID': None,
        'jobDateStarted': None,
        'jobDateDue': None,
        "source": None,
        "target": None,
    }

    try:
        logger.info('Payload JSON: ' + json.dumps(data_payload))
        logger.info('VIA_JAMS_JOB_URL_V1 URL: ' + settings.VIA_JAMS_JOB_URL_V1)
        http_response = requests.post(settings.VIA_JAMS_JOB_URL_V1,
                                      data=json.dumps(data_payload),
                                      headers=API_HEADERS,
                                      timeout=settings.VIA_API_CALL_TIMEOUT_SECONDS
                                      )
    except requests.RequestException, err:
        # Sometimes a request to the API fails with a nice error message.
        # On occasion it may fail with a status 500 error page.
        # And sometimes it may crash and close the connection without sending
        # an HTTP response *at all*, which manifests as a ConnectionError here.
        logger.error("Error retrieving response.", exc_info=True)
        raise JAMSAPIFailure.from_exception(err, err.request)

    logger.info(
        'Response Text: ' + unicode(http_response) + unicode(http_response.text))

    try:
        response_data = http_response.json()

        logger.info('Response JSON: ' + unicode(response_data))

    except ValueError:
        raise JAMSAPIFailure.from_http_response(http_response)

    try:
        if response_data.get('JobNumber'):
            return True, response_data.get('JobNumber'), response_data.get('JobID')
        else:
            raise JAMSAPIFailure.from_http_response(http_response, response_data)
            return False, 'N/A', -1
    except Exception:
        logger.error("create_jams_job_number error", exc_info=True)
        raise JAMSAPIFailure.from_http_response(http_response, response_data)
        return False, 'N/A', -1


def update_jams_job(project):

    params_payload = {'id': project.jams_jobid}

    project_manager_jams_username = project.project_manager.jams_username if project.project_manager else None
    account_executive_jams_username = project.account_executive.jams_username if project.account_executive else None
    clientpo_refnumber = project.payment_details.ca_invoice_number[:50] if project.payment_details.ca_invoice_number else ''

    data_payload = {
        'vtpID': project.id,
        'jobID': project.jams_jobid,
        'jobNumber': u"{0}".format(project.job_number),
        'jobName': u"{0}".format(project.name),
        'customerID': u"{0}".format(project.client.account_number),
        'customerName': u"{0}".format(project.client.name),
        'orderedBy': u"{0}".format(project.client_poc),
        'clientPO_RefNumber': u"{0}".format(clientpo_refnumber),
        'expressFlag': project.project_speed,
        'price': float(project.price()) if project.price() else 0,  # JSON doesn't do Decimal
        'clientNotes': u"{0}".format(''),
        'pMInstructions': u"{0}".format(remove_html_tags(project.instructions)),
        'projectManager': u"{0}".format(project_manager_jams_username) if project_manager_jams_username else None,
        'accountExecutive': u"{0}".format(account_executive_jams_username) if account_executive_jams_username else None,
        'estimateID': project.jams_estimateid,
        'jobDateStarted': u"{0}".format(project.started_timestamp),
        'jobDateDue': u"{0}".format(project.due),
        "source": [{"lcid": project.source_locale.jams_lcid}],
        "target": [dict(lcid=locale.jams_lcid) for locale in project.target_locales.all()],
    }

    try:
        logger.info('Payload JSON: ' + json.dumps(data_payload))
        logger.info('VIA_JAMS_JOB_URL_V1 URL: ' + settings.VIA_JAMS_JOB_URL_V1)
        http_response = requests.post(settings.VIA_JAMS_JOB_URL_V1,
                                      params=params_payload,
                                      data=json.dumps(data_payload),
                                      headers=API_HEADERS,
                                      timeout=settings.VIA_API_CALL_TIMEOUT_SECONDS
        )
    except requests.RequestException, err:
        # Sometimes a request to the API fails with a nice error message.
        # On occasion it may fail with a status 500 error page.
        # And sometimes it may crash and close the connection without sending
        # an HTTP response *at all*, which manifests as a ConnectionError here.
        logger.error("Error retrieving response.", exc_info=True)
        raise JAMSAPIFailure.from_exception(err, err.request)
        return False

    logger.info(
        'Response Text: ' + unicode(http_response) + unicode(http_response.text))

    try:
        response_data = http_response.json()

        logger.info('Response JSON: ' + unicode(response_data))

    except ValueError:
        raise JAMSAPIFailure.from_http_response(http_response)

    try:
        if response_data.get('JobID'):
            return True
        else:
            raise JAMSAPIFailure.from_http_response(http_response, response_data)
            return False

    except Exception:
        logger.error("update_jams_job error", exc_info=True)
        raise JAMSAPIFailure.from_http_response(http_response, response_data)
        return False


def create_jams_job_estimate(project, rush_estimate=False):

    project_manager_jams_username = project.project_manager.jams_username if project.project_manager else None
    account_executive_jams_username = project.account_executive.jams_username if project.account_executive else None
    estimator_jams_username = project.estimator.jams_username if project.estimator else None
    clientpo_refnumber = project.payment_details.ca_invoice_number[:50] if project.payment_details.ca_invoice_number else ''

    rush_order = -1 if rush_estimate else 0

    data_payload = {
        'vtpID': project.id,
        'jobID': project.jams_jobid,
        'jobNumber': u"{0}".format(project.job_number),
        'jobName': u"{0}".format(project.name),
        'estimateID': 0,
        'estimateRequestDate': u"{0}".format(timezone.now()),
        'estimateNeededDate': u"{0}".format(project.quote_due),
        'customerID': u"{0}".format(project.client.account_number),
        'customerName': u"{0}".format(project.client.name),
        'orderedBy': u"{0}".format(project.client_poc),
        'clientPO_RefNumber': u"{0}".format(clientpo_refnumber),
        'projectManager': u"{0}".format(project_manager_jams_username) if project_manager_jams_username else None,
        'accountExecutive': u"{0}".format(account_executive_jams_username) if account_executive_jams_username else None,
        'estimator': u"{0}".format(estimator_jams_username) if estimator_jams_username else None,
        'deliverables': u"{0}".format(remove_html_tags(project.instructions_via)),
        'locationOfFilesOnServer': u"{0}".format(''),
        'otherServices': u"{0}".format(''),
        'otherNotes': u"{0}".format(remove_html_tags(project.instructions)),
        'rushOrder': rush_order,
        'rates': u"{0}".format(project.client.manifest.pricing_scheme),
        'vertical': u"{0}".format(project.client.manifest.vertical),
        'complexQuote': None,
        'avProject': None,
        'webSoftwareProject': None,
        "source": [{"lcid": project.source_locale.jams_lcid}],
        "target": [dict(lcid=locale.jams_lcid) for locale in project.target_locales.all()],
    }

    try:
        logger.info('Payload JSON: ' + json.dumps(data_payload))
        logger.info('VIA_JAMS_ESTIMATE_URL_V1 URL: ' + settings.VIA_JAMS_ESTIMATE_URL_V1)
        http_response = requests.post(settings.VIA_JAMS_ESTIMATE_URL_V1,
                                      data=json.dumps(data_payload),
                                      headers=API_HEADERS,
                                      timeout=settings.VIA_API_CALL_TIMEOUT_SECONDS
        )
    except requests.RequestException, err:
        # Sometimes a request to the API fails with a nice error message.
        # On occasion it may fail with a status 500 error page.
        # And sometimes it may crash and close the connection without sending
        # an HTTP response *at all*, which manifests as a ConnectionError here.
        logger.error("Error retrieving response.", exc_info=True)
        raise JAMSAPIFailure.from_exception(err, err.request)
        return False

    logger.info(
        'Response Text: ' + unicode(http_response) + unicode(http_response.text))

    try:
        response_data = http_response.json()

        logger.info('Response JSON: ' + unicode(response_data))

    except ValueError:
        raise JAMSAPIFailure.from_http_response(http_response)

    try:
        if response_data.get('estimateID'):
            return True, response_data.get('estimateID')
        else:
            raise JAMSAPIFailure.from_http_response(http_response, response_data)
            return False, 'N/A'

    except Exception:
        logger.error("create_jams_job_estimate error", exc_info=True)
        raise JAMSAPIFailure.from_http_response(http_response, response_data)
        return False, 'N/A'
