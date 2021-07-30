import logging
from django.conf import settings

from django.contrib.messages import ERROR, WARNING, SUCCESS
from django.db.models import Q

from projects.duedates import get_job_standard_duration, get_job_express_duration, get_review_hours, \
    get_approval_task_duration, get_dtp_hours, get_post_process_task_duration, \
    get_attorney_review_hours, get_attorney_review_standard_duration, \
    get_attorney_review_express_duration, get_proofreading_hours, \
    get_proofreading_express_duration, get_proofreading_standard_duration, \
    get_non_workflow_hours, get_proof_third_party_review_hours, \
    get_dtp_standard_duration, get_review_standard_duration, get_review_express_duration, \
    get_proof_third_party_review_standard_duration, get_proof_third_party_review_express_duration, \
    get_dtp_express_duration, get_image_localization_hours, get_image_localization_task_duration, get_lso_hours, \
    get_lso_standard_duration, get_lso_express_duration
from services.managers import TRANSLATION_ONLY_SERVICE_TYPE, FINAL_APPROVAL_SERVICE_TYPE, \
    THIRD_PARTY_REVIEW_SERVICE_TYPE, DTP_SERVICE_TYPE, TRANSLATION_EDIT_PROOF_SERVICE_TYPE, \
    HOURS_UNITS, POST_PROCESS_SERVICE_TYPE, WORDS_UNITS, \
    ATTESTATION_SERVICE_TYPE, NOTARIZATION_SERVICE_TYPE, \
    FIXED_UNITS, FILES_UNITS, ATTORNEY_REVIEW_SERVICE_TYPE, \
    PROOFREADING_SERVICE_TYPE, service_units, LINGUISTIC_TASK_SERVICE_TYPE, MT_POST_EDIT_SERVICE_TYPE, \
    IMAGE_LOCALIZATION_SERVICE_TYPE, LINGUISTIC_SIGN_OFF_SERVICE_TYPE, PROOFREADING_THIRD_PARTY_REVIEW_SERVICE_TYPE, \
    LINGUISTIC_QA_SERVICE_TYPE, L10N_ENGINEERING_SERVICE_TYPE, DTP_EDITS_SERVICE_TYPE, ACCESSIBILITY_SERVICE_TYPE, \
    CLIENT_REVIEW_SERVICE_TYPE, CLIENT_REVIEW_BILINGUAL_FORMAT_SERVICE_TYPE, CLIENT_REVIEW_FINAL_PRODUCT_SERVICE_TYPE, \
    FILE_PREP_SERVICE_TYPE, PM_SERVICE_TYPE, PM_HOUR_SERVICE_TYPE, FEEDBACK_MANAGEMENT_SERVICE_TYPE, \
    DISCOUNT_SERVICE_TYPE, RECREATE_SOURCE_FROM_PDF_SERVICE_TYPE, AUDIO_SERVICE_TYPE, ALPHA_SERVICE_TYPE, \
    BETA_SERVICE_TYPE, GAMA_SERVICE_TYPE, AUDIO_QA_SERVICE_TYPE, ALPHA_QA_SERVICE_TYPE, BETA_QA_SERVICE_TYPE, \
    GAMA_QA_SERVICE_TYPE
from services.models import ServiceType, ScopeUnit, Service
from tasks.models import TranslationTask, NonTranslationTask, Task, TranslationTaskAnalysis
from projects.models import ProjectServicesGlobal
from decimal import Decimal


# we should really rename this file manage_tasks or something. Is this a ViewModel? A generator?

logger = logging.getLogger('circus.' + __name__)


def _make_translation_task(project, target, analysis):
    wordcount = analysis.total_wordcount()

    service_object = None
    trans_task = None

    tep = project.services.filter(code=TRANSLATION_EDIT_PROOF_SERVICE_TYPE)
    if tep:
        service_object = _make_service_by_code(TRANSLATION_EDIT_PROOF_SERVICE_TYPE, WORDS_UNITS, project.source_locale, target)
    trans_only = project.services.filter(code=TRANSLATION_ONLY_SERVICE_TYPE)
    if trans_only:
        service_object = _make_service_by_code(TRANSLATION_ONLY_SERVICE_TYPE, WORDS_UNITS, project.source_locale, target)
    if service_object:
        if service_object.service_type.is_translation():
            # Allow customer to have specific Translation Words per Day factor
            translation_words_per_day_standard = project.client.manifest.standard_translation_words_per_day
            standard_days = get_job_standard_duration(wordcount, translation_words_per_day_standard)
            express_factor = project.client.manifest.express_factor if project.client.manifest.express_factor else settings.EXPRESS_FACTOR
            translation_words_per_day_express = translation_words_per_day_standard * express_factor if translation_words_per_day_standard else None
            express_days = get_job_express_duration(wordcount, translation_words_per_day_express)
            if standard_days <= express_days:
                standard_days = express_days + 1

            trans_task = TranslationTask.objects.create(
                project=project,
                service=service_object,
                analysis=analysis,
                standard_days=standard_days,
                express_days=express_days,
                billable=service_object.service_type.billable
            )
        else:
            logger.error(
                u"_make_translation_task %s is %s but is_translation is %r, not sure what kind of task to make.",
                service_object, service_object.service_type, service_object.service_type.is_translation())

    return trans_task


def _make_non_translation_task(project, predecessor, service, quantity, standard_days, express_days, billable, price_flag=False):

    if service.service_type.workflow is True and predecessor is None and standard_days <= express_days:
        standard_days = express_days + 1

    task, created = NonTranslationTask.objects.get_or_create(
            project=project,
            predecessor=predecessor,
            service=service,
            quantity=quantity,
            standard_days=standard_days,
            express_days=express_days,
            billable=billable
        )

    if price_flag and task:
        task.unit_price = quantity/Decimal('100.0')
        task.save()

    if task:
        logger.info(
            u"Success: Job %s created_make_non_translation_task %s success.",
            project, service
        )
    else:
        logger.warning(
            u"Error : Job %s created_make_non_translation_task %s error.",
            project, service
        )
    return task


def _make_service_by_code(code=None, unit_of_measure=None, source=None, target=None):
    service = service_type = scope_unit = None
    if code:
        service_type = ServiceType.objects.get_or_none(code=code)
    if unit_of_measure:
        scope_unit = ScopeUnit.objects.get(code=unit_of_measure)

    if service_type and scope_unit:
        service, created = Service.objects.get_or_create(
            service_type=service_type,
            unit_of_measure=scope_unit,
            source=source,
            target=target
        )
    return service


def _make_post_process_task(project, target, predecessor, wordcount=None, use_globals=True):
    service_object = _make_service_by_code(POST_PROCESS_SERVICE_TYPE, HOURS_UNITS, project.source_locale, target)

    psg, psg_valid = _get_project_services_global(project, service_object.service_type)
    if use_globals and psg:
        quantity = psg.quantity
        standard_days = psg.standard_days
        express_days = psg.express_days
    else:
        quantity = 1
        express_days = standard_days = get_post_process_task_duration(project)

    billable = service_object.service_type.billable

    task = _make_non_translation_task(project, predecessor, service_object, quantity, standard_days, express_days, billable)

    return task


def _make_dtp_task(project, target, predecessor, wordcount=None, use_globals=True):
    service_object = _make_service_by_code(DTP_SERVICE_TYPE, HOURS_UNITS, project.source_locale, target)

    psg, psg_valid = _get_project_services_global(project, service_object.service_type)
    if use_globals and psg:
        quantity = psg.quantity
        standard_days = psg.standard_days
        express_days = psg.express_days
    else:
        quantity = get_dtp_hours(wordcount)
        standard_days = get_dtp_standard_duration(quantity)
        express_days = get_dtp_express_duration(quantity)

    billable = service_object.service_type.billable

    task = _make_non_translation_task(project, predecessor, service_object, quantity, standard_days, express_days, billable)

    return task


def _make_dtp_edits_task(project, target, predecessor, wordcount=None, use_globals=True):
    service_object = _make_service_by_code(DTP_EDITS_SERVICE_TYPE, HOURS_UNITS, project.source_locale, target)

    psg, psg_valid = _get_project_services_global(project, service_object.service_type)
    if use_globals and psg:
        quantity = psg.quantity
        standard_days = psg.standard_days
        express_days = psg.express_days
    else:
        quantity = 1
        express_days = standard_days = 1

    billable = service_object.service_type.billable

    task = _make_non_translation_task(project, predecessor, service_object, quantity, standard_days, express_days, billable)

    return task


def _make_image_localization_task(project, target, predecessor, wordcount=None, use_globals=True):
    service_object = _make_service_by_code(IMAGE_LOCALIZATION_SERVICE_TYPE, HOURS_UNITS, project.source_locale, target)

    psg, psg_valid = _get_project_services_global(project, service_object.service_type)
    if use_globals and psg:
        quantity = psg.quantity
        standard_days = psg.standard_days
        express_days = psg.express_days
    else:
        quantity = get_image_localization_hours()
        express_days = standard_days = get_image_localization_task_duration(quantity)

    billable = service_object.service_type.billable

    task = _make_non_translation_task(project, predecessor, service_object, quantity, standard_days, express_days, billable)

    return task


def _make_proofreading_task(project, target, predecessor, wordcount=None, use_globals=True):
    service_object = _make_service_by_code(PROOFREADING_SERVICE_TYPE, HOURS_UNITS, project.source_locale, target)

    psg, psg_valid = _get_project_services_global(project, service_object.service_type)
    if use_globals and psg:
        quantity = psg.quantity
        standard_days = psg.standard_days
        express_days = psg.express_days
    else:
        quantity = get_proofreading_hours(wordcount)
        standard_days = get_proofreading_standard_duration(quantity)
        express_days = get_proofreading_express_duration(quantity)

    billable = service_object.service_type.billable

    task = _make_non_translation_task(project, predecessor, service_object, quantity, standard_days, express_days, billable)

    return task


def _make_review_task(project, target, predecessor, wordcount=None, use_globals=True):
    service_object = _make_service_by_code(THIRD_PARTY_REVIEW_SERVICE_TYPE, HOURS_UNITS, project.source_locale, target)

    psg, psg_valid = _get_project_services_global(project, service_object.service_type)
    if use_globals and psg:
        quantity = psg.quantity
        standard_days = psg.standard_days
        express_days = psg.express_days
    else:
        quantity = get_review_hours(wordcount)
        standard_days = get_review_standard_duration(quantity)
        express_days = get_review_express_duration(quantity)

    billable = service_object.service_type.billable

    task = _make_non_translation_task(project, predecessor, service_object, quantity, standard_days, express_days, billable)

    return task


def _make_proof_third_party_review_task(project, target, predecessor, wordcount=None, use_globals=True):
    service_object = _make_service_by_code(PROOFREADING_THIRD_PARTY_REVIEW_SERVICE_TYPE, HOURS_UNITS, project.source_locale, target)

    psg, psg_valid = _get_project_services_global(project, service_object.service_type)
    if use_globals and psg:
        quantity = psg.quantity
        standard_days = psg.standard_days
        express_days = psg.express_days
    else:
        quantity = get_proof_third_party_review_hours(wordcount)
        standard_days = get_proof_third_party_review_standard_duration(quantity)
        express_days = get_proof_third_party_review_express_duration(quantity)

    billable = service_object.service_type.billable

    task = _make_non_translation_task(project, predecessor, service_object, quantity, standard_days, express_days, billable)

    return task


def _make_linguistic_task_task(project, target, predecessor, wordcount=None, use_globals=True):
    service_object = _make_service_by_code(LINGUISTIC_TASK_SERVICE_TYPE, HOURS_UNITS, project.source_locale, target)

    psg, psg_valid = _get_project_services_global(project, service_object.service_type)
    if use_globals and psg:
        quantity = psg.quantity
        standard_days = psg.standard_days
        express_days = psg.express_days
    else:
        quantity = 1
        express_days = standard_days = 1

    billable = service_object.service_type.billable

    task = _make_non_translation_task(project, predecessor, service_object, quantity, standard_days, express_days, billable)

    return task


def _make_lso_task(project, target, predecessor, wordcount=None, use_globals=True):
    service_object = _make_service_by_code(LINGUISTIC_SIGN_OFF_SERVICE_TYPE, HOURS_UNITS, project.source_locale, target)

    psg, psg_valid = _get_project_services_global(project, service_object.service_type)
    if use_globals and psg:
        quantity = psg.quantity
        standard_days = psg.standard_days
        express_days = psg.express_days
    else:
        quantity = get_lso_hours(wordcount)
        standard_days = get_lso_standard_duration(quantity)
        express_days = get_lso_express_duration(quantity)

    billable = service_object.service_type.billable

    task = _make_non_translation_task(project, predecessor, service_object, quantity, standard_days, express_days, billable)

    return task


def _make_linguistic_qa_task(project, target, predecessor, wordcount=None, use_globals=True):
    service_object = _make_service_by_code(LINGUISTIC_QA_SERVICE_TYPE, HOURS_UNITS, project.source_locale, target)

    psg, psg_valid = _get_project_services_global(project, service_object.service_type)
    if use_globals and psg:
        quantity = psg.quantity
        standard_days = psg.standard_days
        express_days = psg.express_days
    else:
        quantity = 1
        express_days = standard_days = 1

    billable = service_object.service_type.billable

    task = _make_non_translation_task(project, predecessor, service_object, quantity, standard_days, express_days, billable)

    return task


def _make_mt_pe_task(project, target, predecessor, wordcount=None, use_globals=True):
    service_object = _make_service_by_code(MT_POST_EDIT_SERVICE_TYPE, HOURS_UNITS, project.source_locale, target)

    psg, psg_valid = _get_project_services_global(project, service_object.service_type)
    if use_globals and psg:
        quantity = psg.quantity
        standard_days = psg.standard_days
        express_days = psg.express_days
    else:
        quantity = 1
        express_days = standard_days = 1

    billable = service_object.service_type.billable

    task = _make_non_translation_task(project, predecessor, service_object, quantity, standard_days, express_days, billable)

    return task


def _make_l10n_engineering_task(project, target, predecessor, wordcount=None, use_globals=True):
    service_object = _make_service_by_code(L10N_ENGINEERING_SERVICE_TYPE, HOURS_UNITS, project.source_locale, target)

    psg, psg_valid = _get_project_services_global(project, service_object.service_type)
    if use_globals and psg:
        quantity = psg.quantity
        standard_days = psg.standard_days
        express_days = psg.express_days
    else:
        quantity = 1
        express_days = standard_days = 1

    billable = service_object.service_type.billable

    task = _make_non_translation_task(project, predecessor, service_object, quantity, standard_days, express_days, billable)

    return task


def _make_client_review_task(project, target, predecessor, wordcount=None, use_globals=True):
    service_object = _make_service_by_code(CLIENT_REVIEW_SERVICE_TYPE, HOURS_UNITS, project.source_locale, target)

    psg, psg_valid = _get_project_services_global(project, service_object.service_type)
    if use_globals and psg:
        quantity = psg.quantity
        standard_days = psg.standard_days
        express_days = psg.express_days
    else:
        quantity = 1
        express_days = standard_days = 1

    billable = service_object.service_type.billable

    task = _make_non_translation_task(project, predecessor, service_object, quantity, standard_days, express_days, billable)

    return task


def _make_client_review_bilingual_format_task(project, target, predecessor, wordcount=None, use_globals=True):
    service_object = _make_service_by_code(CLIENT_REVIEW_BILINGUAL_FORMAT_SERVICE_TYPE, HOURS_UNITS, project.source_locale, target)

    psg, psg_valid = _get_project_services_global(project, service_object.service_type)
    if use_globals and psg:
        quantity = psg.quantity
        standard_days = psg.standard_days
        express_days = psg.express_days
    else:
        quantity = 1
        express_days = standard_days = 1

    billable = service_object.service_type.billable

    task = _make_non_translation_task(project, predecessor, service_object, quantity, standard_days, express_days, billable)

    return task


def _make_client_review_final_product_task(project, target, predecessor, wordcount=None, use_globals=True):
    service_object = _make_service_by_code(CLIENT_REVIEW_FINAL_PRODUCT_SERVICE_TYPE, HOURS_UNITS, project.source_locale, target)

    psg, psg_valid = _get_project_services_global(project, service_object.service_type)
    if use_globals and psg:
        quantity = psg.quantity
        standard_days = psg.standard_days
        express_days = psg.express_days
    else:
        quantity = 1
        express_days = standard_days = 1

    billable = service_object.service_type.billable

    task = _make_non_translation_task(project, predecessor, service_object, quantity, standard_days, express_days, billable)

    return task


def _make_accessibility_task(project, target, predecessor, wordcount=None, use_globals=True):
    service_object = _make_service_by_code(ACCESSIBILITY_SERVICE_TYPE, HOURS_UNITS, project.source_locale, target)

    psg, psg_valid = _get_project_services_global(project, service_object.service_type)
    if use_globals and psg:
        quantity = psg.quantity
        standard_days = psg.standard_days
        express_days = psg.express_days
    else:
        quantity = 1
        express_days = standard_days = 1

    billable = service_object.service_type.billable

    task = _make_non_translation_task(project, predecessor, service_object, quantity, standard_days, express_days, billable)

    return task


def _make_notarization_task(project, target, predecessor, wordcount=None, use_globals=True):
    service_object = _make_service_by_code(NOTARIZATION_SERVICE_TYPE, FIXED_UNITS, project.source_locale, target)

    psg, psg_valid = _get_project_services_global(project, service_object.service_type)
    if use_globals and psg:
        quantity = psg.quantity
        standard_days = psg.standard_days
        express_days = psg.express_days
    else:
        quantity = 1
        express_days = standard_days = 0

    billable = service_object.service_type.billable

    task = _make_non_translation_task(project, predecessor, service_object, quantity, standard_days, express_days, billable)

    return task


def _make_attestation_task(project, target, predecessor, wordcount=None, use_globals=True):
    service_object = _make_service_by_code(ATTESTATION_SERVICE_TYPE, FILES_UNITS, project.source_locale, target)

    psg, psg_valid = _get_project_services_global(project, service_object.service_type)
    if use_globals and psg:
        quantity = psg.quantity
        standard_days = psg.standard_days
        express_days = psg.express_days
    else:
        quantity = project.kit.source_files().count()
        express_days = standard_days = 0

    billable = service_object.service_type.billable

    task = _make_non_translation_task(project, predecessor, service_object, quantity, standard_days, express_days, billable)

    return task


def _make_attorney_review_task(project, target, predecessor, wordcount=None, use_globals=True):
    service_object = _make_service_by_code(ATTORNEY_REVIEW_SERVICE_TYPE, HOURS_UNITS, project.source_locale, target)

    psg, psg_valid = _get_project_services_global(project, service_object.service_type)
    if use_globals and psg:
        quantity = psg.quantity
        standard_days = psg.standard_days
        express_days = psg.express_days
    else:
        quantity = get_attorney_review_hours(wordcount)
        standard_days = get_attorney_review_standard_duration(quantity)
        express_days = get_attorney_review_express_duration(quantity)

    billable = service_object.service_type.billable

    task = _make_non_translation_task(project, predecessor, service_object, quantity, standard_days, express_days, billable)

    return task


def _make_approval_task(project, target, predecessor, wordcount=None, use_globals=True):
    service_object = _make_service_by_code(FINAL_APPROVAL_SERVICE_TYPE, HOURS_UNITS, project.source_locale, target)

    psg, psg_valid = _get_project_services_global(project, service_object.service_type)
    if use_globals and psg:
        quantity = psg.quantity
        standard_days = psg.standard_days
        express_days = psg.express_days
    else:
        quantity = 1
        express_days = standard_days = get_approval_task_duration(project)

    billable = service_object.service_type.billable
    task = _make_non_translation_task(project, predecessor, service_object, quantity, standard_days, express_days, billable)

    return task


def _make_client_discount_task(project, target, discount, wordcount=None):
    service_object = _make_service_by_code(DISCOUNT_SERVICE_TYPE, HOURS_UNITS, project.source_locale, target)

    quantity = get_non_workflow_hours(service_object.service_type, wordcount)
    express_days = standard_days = 0
    predecessor = None
    billable = service_object.service_type.billable

    if service_object.service_type.workflow is True and predecessor is None and standard_days <= express_days:
        standard_days = express_days + 1

    task, created = NonTranslationTask.objects.get_or_create(
            project=project,
            predecessor=predecessor,
            service=service_object,
            quantity=quantity,
            standard_days=standard_days,
            express_days=express_days,
            price_is_percentage=True,
            billable=billable
        )

    if task:
        task.unit_price = discount/Decimal('100.0')
        task.save()

    if task:
        logger.info(
            u"Success: Job %s _make_client_discount_task %s success.",
            project, service_object
        )
    else:
        logger.warning(
            u"Error : Job %s _make_client_discount_task %s error.",
            project, service_object
        )
    return task


def _make_non_workflow_tasks(project, target, wordcount=None, use_globals=True):

    try:
        for service_type in project.services.filter(workflow=False):

            unit_code = service_units.get(service_type.code, HOURS_UNITS)
            service_object = _make_service_by_code(service_type.code, unit_code, project.source_locale, target)

            psg, psg_valid = _get_project_services_global(project, service_object.service_type)
            price_flag = False
            if use_globals and psg:
                if service_object.is_percent():
                    price_flag = True
                quantity = psg.quantity
                standard_days = psg.standard_days
                express_days = psg.express_days
            else:
                quantity = get_non_workflow_hours(service_type, wordcount)
                express_days = standard_days = 0

            predecessor = None
            billable = service_type.billable

            task = _make_non_translation_task(project, predecessor, service_object, quantity, standard_days, express_days, billable, price_flag)

    except Exception:
        logger.error("_make_non_workflow_tasks failed for %s %s", project, target, exc_info=True)


def _make_qa_workflow_task(qa_service, project, target, last_task, use_globals=False):
    service_object = _make_service_by_code(qa_service, HOURS_UNITS, project.source_locale, target)
    psg = ProjectServicesGlobal.objects.get_or_none(project=project, servicetype=service_object.service_type)
    if use_globals and psg:
        quantity = psg.quantity
        standard_days = psg.standard_days
        express_days = psg.express_days
    else:
        quantity = 1
        standard_days = express_days = 0

    billable = service_object.service_type.billable
    predecessor = last_task
    task = _make_non_translation_task(project, predecessor, service_object, quantity, standard_days, express_days, billable)
    return task


def _make_tasks_for_target(project, target, use_globals=True):
    """
    :type project: projects.models.Project
    :type target: services.models.Locale
    """
    # li = [AUDIO_SERVICE_TYPE, ALPHA_SERVICE_TYPE, BETA_SERVICE_TYPE, GAMA_SERVICE_TYPE, AUDIO_QA_SERVICE_TYPE, ALPHA_QA_SERVICE_TYPE, BETA_QA_SERVICE_TYPE, GAMA_QA_SERVICE_TYPE]

    workflow_flag = False
    ps = project.services.all()

    if any(service.category.id == 5 for service in project.services.all()):
        workflow_flag = True

    # for qa_service in li:
    #     if ps.filter(code=qa_service).exists():
    #         workflow_flag = True

    if workflow_flag:
        Task.objects.filter(
            project=project,
            service__source=project.source_locale,
            service__target=target,
        ).delete()

        # for service_type in project.services.filter(category_id=5):
        #     unit_code = service_units.get(service_type.code, HOURS_UNITS)
        #     service_object = _make_service_by_code(service_type.code, unit_code, project.source_locale, target)
        #
        #     psg = ProjectServicesGlobal.objects.get_or_none(project=project, servicetype=service_object.service_type)
        #     if use_globals and psg:
        #         quantity = psg.quantity
        #         standard_days = psg.standard_days
        #         express_days = psg.express_days
        #     else:
        #         quantity = 1
        #         standard_days = express_days = 0
        #
        #     billable = service_object.service_type.billable
        #     predecessor = None
        #     _make_non_translation_task(project, predecessor, service_object, quantity, standard_days, express_days, billable)

        #####Another method to do generate the tasks

        last_task = None
        if ps.filter(code=AUDIO_SERVICE_TYPE).exists():
            task = _make_qa_workflow_task(AUDIO_SERVICE_TYPE, project, target, last_task)
            last_task = task

        if ps.filter(code=ALPHA_SERVICE_TYPE).exists():
            task = _make_qa_workflow_task(ALPHA_SERVICE_TYPE, project, target, last_task)
            last_task = task

        if ps.filter(code=BETA_SERVICE_TYPE).exists():
            task = _make_qa_workflow_task(BETA_SERVICE_TYPE, project, target, last_task)
            last_task = task

        if ps.filter(code=GAMA_SERVICE_TYPE).exists():
            task = _make_qa_workflow_task(GAMA_SERVICE_TYPE, project, target, last_task)
            last_task = task

        if ps.filter(code=AUDIO_QA_SERVICE_TYPE).exists():
            task = _make_qa_workflow_task(AUDIO_QA_SERVICE_TYPE, project, target, last_task)
            last_task = task

        if ps.filter(code=ALPHA_QA_SERVICE_TYPE).exists():
            task = _make_qa_workflow_task(ALPHA_QA_SERVICE_TYPE, project, target, last_task)
            last_task = task

        if ps.filter(code=BETA_QA_SERVICE_TYPE).exists():
            task =  _make_qa_workflow_task(BETA_QA_SERVICE_TYPE, project, target, last_task)
            last_task = task

        if ps.filter(code=GAMA_QA_SERVICE_TYPE).exists():
            task = _make_qa_workflow_task(GAMA_QA_SERVICE_TYPE, project, target, last_task)
            last_task = task

        wordcount = None
        _make_approval_task(project, target, last_task, wordcount, use_globals)

        return SUCCESS, ""

    else:
        # delete current tasks to be recreated by function
        Task.objects.filter(
            project=project,
            service__source=project.source_locale,
            service__target=target,
        ).delete()

        # make translation tasks first
        analysis = wordcount = None
        analysis = TranslationTaskAnalysis.objects.create_from_kit(project.kit, target)
        if analysis:
            wordcount = analysis.total_wordcount()

        if not wordcount:
            return ERROR, u"Wordcount was 0 for project {0} and locale {1}".format(project.job_number, target)

        # -------------
        # make Translation and Proofreading tasks if applicable

        # todo - need to use new service_type.is_translation() to determine which kind of task to create

        trans_task = _make_translation_task(project, target, analysis)
        last_task = trans_task

        ps = project.services

        if trans_task and project.is_manual_estimate():
            # Make sure these get a post-processing step.
            if not ps.filter(code=POST_PROCESS_SERVICE_TYPE).exists():
                ps.add(ServiceType.objects.get(code=POST_PROCESS_SERVICE_TYPE))

        if ps.filter(code=PROOFREADING_SERVICE_TYPE).exists():
            task = _make_proofreading_task(project, target, last_task, wordcount, use_globals)
            last_task = task

        if ps.filter(code=LINGUISTIC_TASK_SERVICE_TYPE).exists():
            task = _make_linguistic_task_task(project, target, last_task, wordcount, use_globals)
            last_task = task

        if ps.filter(code=CLIENT_REVIEW_BILINGUAL_FORMAT_SERVICE_TYPE).exists():
            task = _make_client_review_bilingual_format_task(project, target, last_task, wordcount, use_globals)
            last_task = task

        if ps.filter(code=MT_POST_EDIT_SERVICE_TYPE).exists():
            task = _make_mt_pe_task(project, target, last_task, wordcount, use_globals)
            last_task = task

        if ps.filter(code=POST_PROCESS_SERVICE_TYPE).exists():
            task = _make_post_process_task(project, target, last_task, wordcount, use_globals)
            last_task = task

        if ps.filter(code=DTP_SERVICE_TYPE).exists():
            task = _make_dtp_task(project, target, last_task, wordcount, use_globals)
            last_task = task

            # DTP tasks also get Third Party Review.
            if settings.DTP_THIRD_PARTY_REVIEW_REQUIRED:
                if not ps.filter(code=THIRD_PARTY_REVIEW_SERVICE_TYPE).exists():
                    review_service = ServiceType.objects.get(code=THIRD_PARTY_REVIEW_SERVICE_TYPE)
                    ps.add(review_service)

            # DTP tasks also get LSO.
            if settings.DTP_LSO_REQUIRED:
                if not ps.filter(code=LINGUISTIC_SIGN_OFF_SERVICE_TYPE).exists():
                    lso_service = ServiceType.objects.get(code=LINGUISTIC_SIGN_OFF_SERVICE_TYPE)
                    ps.add(lso_service)

        if ps.filter(code=LINGUISTIC_SIGN_OFF_SERVICE_TYPE).exists():
            task = _make_lso_task(project, target, last_task, wordcount, use_globals)
            last_task = task

        if ps.filter(code=IMAGE_LOCALIZATION_SERVICE_TYPE).exists():
            task = _make_image_localization_task(project, target, last_task, wordcount, use_globals)
            last_task = task

        if ps.filter(code=THIRD_PARTY_REVIEW_SERVICE_TYPE).exists():
            task = _make_review_task(project, target, last_task, wordcount, use_globals)
            last_task = task

        if ps.filter(code=PROOFREADING_THIRD_PARTY_REVIEW_SERVICE_TYPE).exists():
            task = _make_proof_third_party_review_task(project, target, last_task, wordcount, use_globals)
            last_task = task

        if ps.filter(code=DTP_EDITS_SERVICE_TYPE).exists():
            task = _make_dtp_edits_task(project, target, last_task, wordcount, use_globals)
            last_task = task

        if ps.filter(code=L10N_ENGINEERING_SERVICE_TYPE).exists():
            task = _make_l10n_engineering_task(project, target, last_task, wordcount, use_globals)
            last_task = task

        if ps.filter(code=LINGUISTIC_QA_SERVICE_TYPE).exists():
            task = _make_linguistic_qa_task(project, target, last_task, wordcount, use_globals)
            last_task = task

        if ps.filter(code=ACCESSIBILITY_SERVICE_TYPE).exists():
            task = _make_accessibility_task(project, target, last_task, wordcount, use_globals)
            last_task = task

        if ps.filter(code=ATTORNEY_REVIEW_SERVICE_TYPE).exists():
            task = _make_attorney_review_task(project, target, last_task, wordcount, use_globals)
            last_task = task

        if ps.filter(code=NOTARIZATION_SERVICE_TYPE).exists():
            task = _make_notarization_task(project, target, last_task, wordcount, use_globals)
            last_task = task

        if ps.filter(code=ATTESTATION_SERVICE_TYPE).exists():
            task = _make_attestation_task(project, target, last_task, wordcount, use_globals)
            last_task = task

        if ps.filter(code=CLIENT_REVIEW_SERVICE_TYPE).exists():
            task = _make_client_review_task(project, target, last_task, wordcount, use_globals)
            last_task = task

        if ps.filter(code=CLIENT_REVIEW_FINAL_PRODUCT_SERVICE_TYPE).exists():
            task = _make_client_review_final_product_task(project, target, last_task, wordcount, use_globals)
            last_task = task

        _make_non_workflow_tasks(project, target, wordcount, use_globals)

        _verify_add_client_discount_task(project)

        _make_approval_task(project, target, last_task, wordcount, use_globals)

        return SUCCESS, ""


def make_project_tasks(project, use_globals=True):
    if not project.is_inestimate_status():
        return ERROR, u'Cannot make job tasks when in state {0}'.format(project.machine.state.label)

    if not project.source_locale or not project.target_locales_count():
        return ERROR, u"Source and target locales must be set to generate tasks"

    if not project.services.count():
        return ERROR, u"Services must be set to generate tasks"

    assets = list(project.kit.source_files())
    if not project.internal_via_project:
        if not assets:
            return WARNING, u"Could not generate tasks: no source assets"

    # delete existing tasks for locales not in our target list
    # project.clean_tasks()
    # delete all existing tasks
    project.delete_all_tasks()

    has_errors = False
    has_errors_status = has_errors_msg = ''

    for target in project.target_locales.all():
        try:
            status, msg = _make_tasks_for_target(project, target, use_globals)
        except Exception:
            logger.error("make_project_tasks failed for %s %s",
                         project, target, exc_info=True)

            return ERROR, u"Errors during Generate Tasks for {0}".format(target)

        if status != SUCCESS:
            has_errors = True
            has_errors_status = status
            has_errors_msg = ', '.join([has_errors_msg, msg])

    if has_errors:
        return has_errors_status, has_errors_msg

    return SUCCESS, u"Tasks generated for Job Estimate"


def _insert_lso_task(project, target):
    pass


def _insert_post_processing_task(project, target):
    """Inserts a post processing task after the translation task.

    If there are no translation tasks, there is no change.
    :type project: projects.models.Project
    :type target: services.models.Locale
    """
    if project.task_set.filter(
            service__target=target,
            service__service_type__code=POST_PROCESS_SERVICE_TYPE).exists():
        # if a post-process task already exists, leave it alone.
        return None

    root_task = project.workflow_root_tasks_target_locale(target).first()

    pp_task = None
    this_task = root_task

    while True:
        try:
            next_task = project.task_set.get(predecessor=this_task)
        except project.task_set.DoesNotExist:
            next_task = None

        if this_task.is_translation():
            if (not next_task) or (not next_task.is_translation()):
                pp_task = _make_post_process_task(project, target, this_task)
                if next_task:
                    next_task.predecessor = pp_task
                    next_task.save()

                if not project.services.filter(code=POST_PROCESS_SERVICE_TYPE).exists():
                    project.services.add(
                        ServiceType.objects.get(code=POST_PROCESS_SERVICE_TYPE))
                break

        if not next_task:
            break

    return pp_task


def convert_project_to_manual_tasks(project):
    """
    :type project: projects.models.Project
    """

    if not project.is_manual_estimate():
        logger.warning(u"convert_project_to_manual_tasks called but estimate_type is not manual, but %r", project.estimate_type)

    if not project.is_inestimate_status():
        return ERROR, u'Cannot make job tasks when in state {0}'.format(project.machine.state.label)

    if project.has_tasks():
        for target in project.target_locales.all():
            _insert_post_processing_task(project, target)

    return SUCCESS, u"Job converted to Manual Estimate"


def default_global_service_quantity(project):
    dic = {}
    service_list = [service for service in project.services.all() if service.translation_task is False]
    services = project.add_fa_service(service_list)

    analysis = wordcount = None

    for target in project.target_locales.all():
        analysis = TranslationTaskAnalysis.objects.create_from_kit(project.kit, target)
        if analysis:
            wordcount = analysis.total_wordcount()
            break

    for service in services:
        if service.code == DTP_SERVICE_TYPE:
            quantity = get_dtp_hours(wordcount)
            dic.setdefault(DTP_SERVICE_TYPE, []).append(quantity)
            dic.setdefault(DTP_SERVICE_TYPE, []).append(get_dtp_standard_duration(quantity))
            dic.setdefault(DTP_SERVICE_TYPE, []).append(get_dtp_express_duration(quantity))

        elif service.code == THIRD_PARTY_REVIEW_SERVICE_TYPE:
            quantity = get_review_hours(wordcount)
            dic.setdefault(THIRD_PARTY_REVIEW_SERVICE_TYPE, []).append(quantity)
            dic.setdefault(THIRD_PARTY_REVIEW_SERVICE_TYPE, []).append(get_review_standard_duration(quantity))
            dic.setdefault(THIRD_PARTY_REVIEW_SERVICE_TYPE, []).append(get_review_express_duration(quantity))

        elif service.code == FINAL_APPROVAL_SERVICE_TYPE:
            dic.setdefault(FINAL_APPROVAL_SERVICE_TYPE, []).append(1)
            dic.setdefault(FINAL_APPROVAL_SERVICE_TYPE, []).append(get_approval_task_duration(project))
            dic.setdefault(FINAL_APPROVAL_SERVICE_TYPE, []).append(get_approval_task_duration(project))

        elif service.code == LINGUISTIC_TASK_SERVICE_TYPE:
            quantity = get_review_hours(wordcount)
            dic.setdefault(LINGUISTIC_TASK_SERVICE_TYPE, []).append(quantity)
            dic.setdefault(LINGUISTIC_TASK_SERVICE_TYPE, []).append(get_review_standard_duration(quantity))
            dic.setdefault(LINGUISTIC_TASK_SERVICE_TYPE, []).append(get_review_express_duration(quantity))

        elif service.code == POST_PROCESS_SERVICE_TYPE:
            dic.setdefault(POST_PROCESS_SERVICE_TYPE, []).append(1)
            dic.setdefault(POST_PROCESS_SERVICE_TYPE, []).append(get_post_process_task_duration(project))
            dic.setdefault(POST_PROCESS_SERVICE_TYPE, []).append(get_post_process_task_duration(project))

        elif service.code == PROOFREADING_THIRD_PARTY_REVIEW_SERVICE_TYPE:
            quantity = get_proof_third_party_review_hours(wordcount)
            dic.setdefault(PROOFREADING_THIRD_PARTY_REVIEW_SERVICE_TYPE, []).append(quantity)
            dic.setdefault(PROOFREADING_THIRD_PARTY_REVIEW_SERVICE_TYPE, []).append(get_proof_third_party_review_standard_duration(quantity))
            dic.setdefault(PROOFREADING_THIRD_PARTY_REVIEW_SERVICE_TYPE, []).append(get_proof_third_party_review_express_duration(quantity))

        elif service.code == PROOFREADING_SERVICE_TYPE:
            quantity = get_proofreading_hours(wordcount)
            dic.setdefault(PROOFREADING_SERVICE_TYPE, []).append(quantity)
            dic.setdefault(PROOFREADING_SERVICE_TYPE, []).append(get_proofreading_standard_duration(quantity))
            dic.setdefault(PROOFREADING_SERVICE_TYPE, []).append(get_proofreading_express_duration(quantity))

        elif service.code == FILE_PREP_SERVICE_TYPE:
            quantity = get_non_workflow_hours(service, wordcount)
            dic.setdefault(FILE_PREP_SERVICE_TYPE, []).append(quantity)
            dic.setdefault(FILE_PREP_SERVICE_TYPE, []).append(0)
            dic.setdefault(FILE_PREP_SERVICE_TYPE, []).append(0)

        elif service.code == ATTORNEY_REVIEW_SERVICE_TYPE:
            quantity = get_attorney_review_hours(wordcount)
            dic.setdefault(ATTORNEY_REVIEW_SERVICE_TYPE, []).append(quantity)
            dic.setdefault(ATTORNEY_REVIEW_SERVICE_TYPE, []).append(get_attorney_review_standard_duration(quantity))
            dic.setdefault(ATTORNEY_REVIEW_SERVICE_TYPE, []).append(get_attorney_review_express_duration(quantity))

        elif service.code == IMAGE_LOCALIZATION_SERVICE_TYPE:
            quantity = get_image_localization_hours()
            dic.setdefault(IMAGE_LOCALIZATION_SERVICE_TYPE, []).append(quantity)
            dic.setdefault(IMAGE_LOCALIZATION_SERVICE_TYPE, []).append(get_image_localization_task_duration(quantity))
            dic.setdefault(IMAGE_LOCALIZATION_SERVICE_TYPE, []).append(get_image_localization_task_duration(quantity))

        elif service.code == NOTARIZATION_SERVICE_TYPE:
            dic[NOTARIZATION_SERVICE_TYPE] = [1, 0, 0]

        elif service.code == ATTESTATION_SERVICE_TYPE:
            dic.setdefault(ATTESTATION_SERVICE_TYPE, []).append(project.kit.source_files().count())
            dic.setdefault(ATTESTATION_SERVICE_TYPE, []).append(0)
            dic.setdefault(ATTESTATION_SERVICE_TYPE, []).append(0)

        elif service.code == PM_SERVICE_TYPE:
            dic.setdefault(PM_SERVICE_TYPE, []).append(0)
            dic.setdefault(PM_SERVICE_TYPE, []).append(0)
            dic.setdefault(PM_SERVICE_TYPE, []).append(0)

        elif service.code == PM_HOUR_SERVICE_TYPE:
            quantity = get_non_workflow_hours(service, wordcount)
            dic.setdefault(PM_HOUR_SERVICE_TYPE, []).append(quantity)
            dic.setdefault(PM_HOUR_SERVICE_TYPE, []).append(0)
            dic.setdefault(PM_HOUR_SERVICE_TYPE, []).append(0)

        elif service.code == FEEDBACK_MANAGEMENT_SERVICE_TYPE:
            quantity = get_non_workflow_hours(service, wordcount)
            dic.setdefault(FEEDBACK_MANAGEMENT_SERVICE_TYPE, []).append(quantity)
            dic.setdefault(FEEDBACK_MANAGEMENT_SERVICE_TYPE, []).append(0)
            dic.setdefault(FEEDBACK_MANAGEMENT_SERVICE_TYPE, []).append(0)

        elif service.code == RECREATE_SOURCE_FROM_PDF_SERVICE_TYPE:
            quantity = get_non_workflow_hours(service, wordcount)
            dic.setdefault(RECREATE_SOURCE_FROM_PDF_SERVICE_TYPE, []).append(quantity)
            dic.setdefault(RECREATE_SOURCE_FROM_PDF_SERVICE_TYPE, []).append(0)
            dic.setdefault(RECREATE_SOURCE_FROM_PDF_SERVICE_TYPE, []).append(0)

        elif service.code == DISCOUNT_SERVICE_TYPE:
            dic.setdefault(DISCOUNT_SERVICE_TYPE, []).append(0)
            dic.setdefault(DISCOUNT_SERVICE_TYPE, []).append(0)
            dic.setdefault(DISCOUNT_SERVICE_TYPE, []).append(0)

        else:
            dic[service.code] = [1, 1, 1]

    return dic


def _add_project_services_global(project, service_type, quantity=0, standard_days=0, express_days=0):
    psg, created = ProjectServicesGlobal.objects.get_or_create(project=project, servicetype=service_type)
    psg.quantity=quantity
    psg.standard_days=standard_days
    psg.express_days=express_days
    psg.save()
    return psg


def _delete_project_services_global(project, service_type):
    psg = ProjectServicesGlobal.objects.get_or_none(project=project, servicetype=service_type)
    if psg:
        psg.delete()
        return True
    else:
        return False


def _get_project_services_global(project, service_type):
    psg = ProjectServicesGlobal.objects.get_or_none(
        project=project,
        servicetype=service_type
    )
    psg_valid = True if psg and psg.quantity is not None and psg.quantity != 0 else False
    return psg, psg_valid


def _get_service_type_client_discount():
    return ServiceType.objects.get_or_none(code=DISCOUNT_SERVICE_TYPE)


def _get_client_discount(client_id, check_date):
    from clients.models import ClientDiscount
    cd = ClientDiscount.objects.filter(
        Q(client_id=client_id) & Q(start_date__lte=check_date) & Q(end_date__gte=check_date))
    return cd


def _add_client_discount(project):
    service_type = _get_service_type_client_discount()
    project.services.add(service_type)
    from tasks.make_tasks import _add_project_services_global
    psg = _add_project_services_global(project, service_type)
    if psg:
        return True
    else:
        return False


def _delete_client_discount(project):
    service_type = _get_service_type_client_discount()
    project.services.filter(code=service_type.code).delete()
    return _delete_project_services_global(project, service_type)


def _verify_client_discount_task(project):
    client_discount_flag = False
    if any(project.task_set.filter(service__service_type__code=DISCOUNT_SERVICE_TYPE)):
        client_discount_flag = True
    return client_discount_flag


def _verify_add_client_discount_task(project):
    client_discount_flag = _verify_client_discount_task(project)

    if not client_discount_flag and project.created:
        cd = _get_client_discount(project.client.id, project.created)
        if cd:
            client_discount_flag = _add_client_discount(project)
            for target in project.target_locales.all():
                _make_client_discount_task(project, target, cd.values_list('discount', flat=True)[0])
            from projects.set_prices import set_project_rates_and_prices
            set_project_rates_and_prices(project)
    return client_discount_flag
