#!/usr/bin/python
# -*- coding: utf-8 -*-
import json
import logging
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.db.models import Q
import requests

from django.core.management import BaseCommand
from jams_api.engine import JAMSAPIFailure
from people.models import AccountType
from projects.models import Project
from projects.states import STARTED_STATUS
from services.managers import FIXED_UNITS, TRANSLATION_EDIT_PROOF_SERVICE_TYPE
from services.models import ScopeUnit, ServiceType
from shared.viewmodels import TargetAnalysisSetViewModel
from tasks.models import Task, VendorPurchaseOrder
from vendors.models import Vendor
from projects.states import COMPLETED_STATUS
from django.utils import timezone

logger = logging.getLogger('circus.' + __name__)


API_HEADERS = {
    'content-type': 'application/json',
    'x-apikey': settings.VIA_DVX_API_KEY
}

def import_failed_action(where_are_we=''):
    logger.info(u'jams_api.engine.import_failed_action: ' + unicode(where_are_we))
    pass


def create_payload_translationtask(self, ta=None):

    # Task Type is Translation/Proofreading
        # (TRANSLATION_EDIT_PROOF_SERVICE_TYPE, 'Translation and Proofreading', True, True, 2),
    # translation unit words in system, but jams needs source (1) or target (2)
        # (WORDS_UNITS, 'Words', None),
        # ('source', 'Source', 1),  NEED TO DYNAMICALLY PICK WHEN WORDS CHOSEN IN VTP AND PASSED JAMS API
        # ('target', 'Target', 2),  NEED TO DYNAMICALLY PICK WHEN WORDS CHOSEN IN VTP AND PASSED JAMS API
    # if minimum, unit is fixed fee
        # ('fixed', 'Fixed Fee', 6),

    quantity = None
    rate = None
    unit = self.service.unit_of_measure.jams_basisid

    if unit is None:
        if self.translationtask.vendor_rates:
            unit = self.translationtask.vendor_rates.basis.id
        else:
            return {}

    if self.is_minimum_vendor():
        unit = ScopeUnit.objects.get(code=FIXED_UNITS).jams_basisid
        quantity = 1
        rate = self.translationtask.vendor_rates.minimum
    else:
        rate = self.translationtask.vendor_rates.word_rate

    source_locale = self.service.source.normalize_english()

    data_payload = {
        'vtpTaskID': self.id,
        'taskItemID': self.service.service_type.jams_jobtaskid,
        'source_lcid': source_locale.jams_lcid,
        'target_lcid': self.service.target.jams_lcid,
        'generatePO': True,
        'poStatus': 'New',
        'deliverVia': settings.APP_SLUG_VTP,
        'returnVia': settings.APP_SLUG_VTP,
        'isTranslation': True,
        'quantity': quantity,
        'rate': u'{0}'.format(rate),
        'uom': unit,
        'TaskID': self.jams_taskid,
        'JobID': self.project.jams_jobid,
        'TaskItem': self.service.service_type.description,
        'LanguagePairID': None,
        'SupplierID': self.assigned_to.account_number,
        'SupplierName': self.assigned_to.name,
        'DueDate': u'{0}'.format(self.due),
        'DueTime': 'EOB',
        'PONew': None,
        'POSent': None,
        'Confirmed': None,
        'Received': None,
        'Complete': None,
        'POCreated': None,
        'SortOrder': None,
        'Notes': None,
        'MinFee': None,
        'PurchaseOrderID': None,
        'TrxPrfNoMatch': ta.total_no_match,
        'Match50_74': ta.total_fuzzy5074,
        'Match75_84': ta.total_fuzzy7584,
        'Match85_94': ta.total_fuzzy8594,
        'Match95_99': ta.total_fuzzy9599,
        'Match100': ta.total_exact,
        'MatchRepetitions': ta.total_duplicate,
        'MatchPerfect': ta.total_guaranteed,
        'CatToolID': 1,
        'Filename': settings.APP_SLUG_VTP,
        'QBPO': None,
        'tblCatTool': 1,
        'Total': None,
        'Language_pairs': None,
        'CustomerID': u"{0}".format(self.project.client.account_number),
        'CatToolDescription': u'Déjà Vu',
        'File': None
    }
    return data_payload


def create_payload_nontranslationtask(self):

    unit = None
    quantity = None
    rate = None

    if not self.unit_cost():
        return {}

    if self.is_minimum_vendor():
        unit = ScopeUnit.objects.get(code=FIXED_UNITS).jams_basisid
        quantity = 1
        rate = self.vendor_minimum
    else:
        unit = self.service.unit_of_measure.jams_basisid
        quantity = self.actual_hours() if self.actual_hours() else self.quantity()
        rate = self.unit_cost()

    source_locale = self.service.source.normalize_english()

    data_payload = {
        'vtpTaskID': self.id,
        'taskItemID': self.service.service_type.jams_jobtaskid,
        'source_lcid': source_locale.jams_lcid,
        'target_lcid': self.service.target.jams_lcid,
        'generatePO': True,
        'poStatus': 'New',
        'deliverVia': settings.APP_SLUG_VTP,
        'returnVia': settings.APP_SLUG_VTP,
        'isTranslation': False,
        'quantity': u'{0}'.format(quantity),
        'rate': u'{0}'.format(rate),
        'uom': unit,
        'TaskID': self.jams_taskid,
        'JobID': self.project.jams_jobid,
        'TaskItem': self.service.service_type.description,
        'LanguagePairID': None,
        'SupplierID': self.assigned_to.account_number,
        'SupplierName': self.assigned_to.name,
        'DueDate': u'{0}'.format(self.due),
        'DueTime': 'EOB',
        'PONew': None,
        'POSent': None,
        'Confirmed': None,
        'Received': None,
        'Complete': None,
        'POCreated': None,
        'SortOrder': None,
        'Notes': None,
        'MinFee': None,
        'PurchaseOrderID': None,
        'TrxPrfNoMatch': None,
        'Match50_74': None,
        'Match75_84': None,
        'Match85_94': None,
        'Match95_99': None,
        'Match100': None,
        'MatchRepetitions': None,
        'MatchPerfect': None,
        'CatToolID': None,
        'Filename': None,
        'QBPO': None,
        'tblCatTool': 1,
        'Total': None,
        'Language_pairs': None,
        'CustomerID': u"{0}".format(self.project.client.account_number),
        'CatToolDescription': None,
        'File': None
    }
    return data_payload


def create_jams_job_tasks_and_po(job_number=None, delay_job_po=False):

    pos_created = 0

    # project.show_start_workflow()
    active_projects = Project.objects.select_related().filter(status=STARTED_STATUS,  delay_job_po=delay_job_po)
    started_workflow_projects_ids = [p.id for p in active_projects if p.show_start_workflow() is False]

    # Look for VTP Tasks without a jams_taskid
    tasks_without_jams_task_id = Task.objects.select_related().filter(project_id__in=started_workflow_projects_ids,
                                                                      assignee_object_id__isnull=False,
                                                                      jams_taskid__isnull=True,
                                                                      billable=True,
                                                                      po__po_number__isnull=True,
                                                                      service__service_type__workflow=True,
                                                                      create_po_needed=True,
                                                                      )

    if job_number:
        logger.info(u'Job: {0}'.format(job_number))
        # Look for VTP Tasks without a jams_taskid for specific job_number
        tasks_without_jams_task_id = tasks_without_jams_task_id.filter(project__job_number=job_number)

        if delay_job_po:
            tasks_without_jams_task_id = tasks_without_jams_task_id.filter(status=COMPLETED_STATUS)

    # Do not generate JAMS POs for VIA Panama TEP tasks, they outsource Translation always so remove any TEP tasks assigned to them.
    if settings.VIA_PANAMA_NO_AUTO_GENERATE_TEP_PO_JAMS:
        logger.info(u'Do not generate JAMS POs for VIA Panama TEP tasks, they outsource Translation always so remove any TEP tasks assigned to them.')
        via_panama_vendor = Vendor.objects.get(account_number=settings.VIA_PANAMA_VENDOR_JAMS_ID)
        tep_service_type = ServiceType.objects.get(code=TRANSLATION_EDIT_PROOF_SERVICE_TYPE)
        tasks_without_jams_task_id = tasks_without_jams_task_id.filter(
            ~Q(service__service_type=tep_service_type, assignee_content_type=ContentType.objects.get_for_model(via_panama_vendor), assignee_object_id=via_panama_vendor.id)
        )

    for jt in tasks_without_jams_task_id:

        logger.info(u'Job Task: {0}'.format(jt))

        data_payload = {}

        # only generate PO for tasks assigned to Vendor Account
        # there are 2 options:
        #     when Vendor assigned_to, object is Account
        #     when VIA assigned_to, object is CircusUser, has no account_type property
        is_vendor_account = False
        if hasattr(jt.assigned_to, 'account_type'):
            if jt.assigned_to.account_type == AccountType.objects.get(code=settings.VENDOR_USER_TYPE):
                is_vendor_account = True

        if is_vendor_account:
            if jt.is_translation():
                target_analysis = TargetAnalysisSetViewModel(jt.service.target, jt.project, include_placeholder=False)
                data_payload = create_payload_translationtask(jt, target_analysis)
            else:
                data_payload = create_payload_nontranslationtask(jt)

            if data_payload:
                logger.info(u'Payload JSON: ' + json.dumps(data_payload))
                logger.info(u'VIA_JAMS_TASK_URL_V1 URL: ' + settings.VIA_JAMS_TASK_URL_V1)

                try:
                    http_response = requests.post(settings.VIA_JAMS_TASK_URL_V1,
                                                  data=json.dumps(data_payload),
                                                  headers=API_HEADERS,
                                                  timeout=settings.VIA_API_CALL_TIMEOUT_SECONDS,
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
                except ValueError:
                    raise JAMSAPIFailure.from_http_response(http_response)

                # responses surrounded by "" or [] can make .json() return strings or
                # lists, so make sure we have a dict.
                if not isinstance(response_data, dict):
                    raise JAMSAPIFailure.from_http_response(http_response)

                logger.info(u'Response JSON: ' + unicode(response_data))

                # save jams_jobtaskid and jams_purchaseorderid
                if response_data.get('TaskID'):
                    jt.jams_taskid = response_data.get('TaskID')
                    jt.po_created_date = timezone.now()
                    jt.save()
                else:
                    raise JAMSAPIFailure.from_http_response(http_response, response_data)

                if response_data.get('PurchaseOrderID'):
                    vpo = VendorPurchaseOrder.objects.filter(task=jt)
                    if vpo:
                        vpo.delete()
                    po, created = VendorPurchaseOrder.objects.get_or_create(task=jt,
                                                                            vendor_id=jt.assignee_object_id,
                                                                            )
                    if po:
                        po.po_number = response_data.get('PurchaseOrderID')
                        po.due = response_data.get('DueDate')
                        po.save()
                        pos_created += 1
                        logger.info(u'PO created: {0}!'.format(po.po_number))
                else:
                    raise JAMSAPIFailure.from_http_response(http_response, response_data)
            else:
                logger.warning(u'Job Task: {0} - No Data Payload returned!'.format(jt))
        pass

    else:
        logger.info(u'{0} POs created'.format(pos_created))

    # Look for VTP Tasks without a purchase order
    # tasks_without_pos = Task.objects.select_related().filter(project__status=STARTED_STATUS, assignee_object_id__isnull=False, jams_taskid__isnull=False, po__po_number__isnull=True)
    # for jtpo in tasks_without_pos:
    #     pass
    # pass


class Command(BaseCommand):
    args = ''
    help = 'Scheduler to sync VTP to JAMS API for Tasks, POs, etc.'

    def handle(self, *args, **options):

        job_number = None
        delay_job_po = False

        if args.__len__() == 1:
            job_number = args[0]
        elif args.__len__() == 2:
            job_number = args[0]
            delay_job_po = args[1]

        try:
            create_jams_job_tasks_and_po(job_number, delay_job_po)
        except Exception:
            # unlike django request handling, management commands don't have
            # any top-level exception logger. add one here as this is run
            # unattended by heroku scheduler.
            logger.error("error in create_job_task_and_po", exc_info=True)
            raise
