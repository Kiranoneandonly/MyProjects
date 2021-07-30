# coding=utf-8
import logging
from django.conf import settings
from django.utils import timezone
from celery.task import task
from localization_kits.models import FileAnalysis, ANALYSIS_STATUS_SUCCESS, ANALYSIS_STATUS_ERROR, FileAsset, LocaleTranslationKit, get_translation_file_path
from services.models import Locale
from shared.api_engine import api_post, api_get
from shared.utils import copy_file_asset

logger = logging.getLogger('circus.' + __name__)


def file_dict(asset):
    if asset.prepared_file:
        name = asset.prepared_name
        path = asset.prepared_file
    else:
        name = asset.orig_name
        path = asset.orig_file

    if '.' in name:
        extension = name.rsplit('.', 1)[-1]
    else:
        extension = ''
    return {
        "id": asset.id,
        "name": name,
        "type": extension,
        "uri": u"{0}{1}".format(settings.MEDIA_URL[1:], unicode(path)),
    }


def analysis_failed_action(localization_kit):
    localization_kit.analysis_completed = timezone.now()
    localization_kit.save()


def _import_payload(trans_kit):
    if '.' in trans_kit.output_file_name():
        extension = trans_kit.output_file_name().rsplit('.', 1)[-1]
    else:
        extension = 'rtf'
    project = trans_kit.task.project
    payload = {
        'jobID': project.id,
        'analysisCode': project.kit.analysis_code,
        's3Bucket': settings.AWS_STORAGE_BUCKET_NAME,
        "file": [
            {
                "id": 0,
                "name": trans_kit.output_file_name(),
                "type": extension,
                "uri": u"{0}{1}".format(settings.MEDIA_URL[1:],
                                        unicode(trans_kit.output_file)),
                "source": {"lcid": trans_kit.task.service.source.dvx_lcid},
                "target": {"lcid": trans_kit.task.service.target.dvx_lcid},
            }
        ]
    }
    return payload

def _import_payload_for_tm(trans_kit):
    if '.' in trans_kit.tm_update_file_name():
        extension = trans_kit.tm_update_file_name().rsplit('.', 1)[-1]
    else:
        extension = 'rtf'
    project = trans_kit.task.project
    payload = {
        'jobID': project.id,
        'analysisCode': project.kit.analysis_code,
        's3Bucket': settings.AWS_STORAGE_BUCKET_NAME,
        "file": [
            {
                "id": 0,
                "name": trans_kit.tm_update_file_name(),
                "type": extension,
                "uri": u"{0}{1}".format(settings.MEDIA_URL[1:],
                                        unicode(trans_kit.tm_update_file)),
                "source": {"lcid": trans_kit.task.service.source.dvx_lcid},
                "target": {"lcid": trans_kit.task.service.target.dvx_lcid},
            }
        ]
    }
    return payload

def import_translation(trans_kit):
    """Provide a translation to DéjàVu.

    :type trans_kit: TaskLocaleTranslationKit
    :raises DVXFailure: if the connection to the server fails, or the server
        returns a non-success status code for this action.
    :rtype: None
    """
    payload = _import_payload(trans_kit)
    api_post(settings.VIA_IMPORT_URL, payload)


def import_translation_v2(trans_kit, bg_task):
    payload = _import_payload(trans_kit)
    payload['bg_task'] = bg_task.id
    api_post(settings.VIA_IMPORT_URL, payload)

def import_translation_v2_for_tm(trans_kit, bg_task):
    payload = _import_payload_for_tm(trans_kit)
    payload['bg_task'] = bg_task.id
    api_post(settings.VIA_IMPORT_URL, payload)

def _generate_delivery_payload(trans_kit):
    project = trans_kit.task.project
    payload = {
        'jobID': project.id,
        'analysisCode': project.kit.analysis_code,
        's3Bucket': settings.AWS_STORAGE_BUCKET_NAME,
        'fileID': 0,
        'sLangID': trans_kit.task.service.source.dvx_lcid,
        'tLangID': trans_kit.task.service.target.dvx_lcid,
    }
    return payload


def delivery_files_from_json(to_task_id, json_files):
    from tasks.models import TaskLocalizedAsset

    for out_file in json_files['file']:
        # add a new delivery file to to_task
        la, created = TaskLocalizedAsset.objects.get_or_create(
            task_id=to_task_id,
            name=out_file['name']
        )
        la.input_file = out_file['uri'][len(settings.MEDIA_URL) - 1:]
        la.output_file = la.input_file
        la.source_asset_id = out_file['id']
        la.save()

    from via_portal.views import rename_approved_file
    #Rename file - Automatic renaming the files by appending the target locale
    rename_approved_file(to_task_id)


def generate_delivery_files(trans_kit, to_task_id):
    """Generate delivery files from a translation kit.

    The files will be added as TaskLocalizedAssets to the specified Task.

    :type trans_kit: TaskLocaleTranslationKit
    :type to_task_id: int
    :raises DVXFailure: if the connection to the server fails, or the server
        returns a non-success status code for this action.
    :rtype: None
    """
    payload = _generate_delivery_payload(trans_kit)

    r = api_get(settings.VIA_DELIVERY_URL, payload)

    # todo: do something smart with the contents of the file array
    delivery_files_from_json(to_task_id, r)


def generate_delivery_files_v2(trans_kit, bg_task=None):
    payload = _generate_delivery_payload(trans_kit)
    if bg_task:
        payload['bg_task'] = bg_task.id
    r = api_get(settings.VIA_DELIVERY_URL, payload)


def generate_task_files_manual(trans_kit, to_task):
    """
    :type trans_kit: tasks.models.TaskLocaleTranslationKit
    """
    from tasks.models import TaskLocalizedAsset
    for source_file in trans_kit.task.project.kit.source_files():
        la, created = TaskLocalizedAsset.objects.get_or_create(
            task=to_task,
            name=source_file.orig_name
        )
        la.input_file = trans_kit.output_file
        la.output_file = None
        la.source_asset_id = source_file.id
        la.save()
    return True


def kits_from_json(localization_kit, json_kits):
    analysis_code = localization_kit.analysis_code

    for f in json_kits['file']:
        target_locale = Locale.objects.get(dvx_lcid=int(f['target']['lcid']))
        locale_trans_kit, created = LocaleTranslationKit.objects.get_or_create(
            kit=localization_kit,
            target_locale=target_locale
        )
        in_filename = get_translation_file_path(locale_trans_kit, f['name'])

        from_key = f['uri']
        to_key = settings.MEDIA_URL[1:] + in_filename

        if from_key:
            copy_file_asset(from_key, to_key)

        locale_trans_kit.translation_file = in_filename
        locale_trans_kit.analysis_code = analysis_code
        locale_trans_kit.save()


@task
def prep_kit(localization_kit_id, callback=None):
    """
    :param int localization_kit_id: ID of a LocalizationKit
    :raises DVXFailure: if the connection to the server fails, or the server
        returns a non-success status code for this action.
    :rtype: None
    """
    from localization_kits.models import LocalizationKit
    localization_kit = LocalizationKit.objects.get(pk=localization_kit_id)

    payload = {
        's3Bucket': settings.AWS_STORAGE_BUCKET_NAME,
        'jobID': localization_kit.project.id,
        'analysisCode': localization_kit.analysis_code,
    }

    r = api_get(settings.VIA_PREP_KIT_URL, payload)

    kits_from_json(localization_kit, r)

    if callback:
        # Run the callback synchronously, in-process. Not using celery's
        # workflow canvas (either link=callback or chain(analyze, callback))
        # because tracking the state of multi-task workflows becomes
        # unreasonable and the delay between tasks is significant.
        callback()


def prep_kit_v2(localization_kit, bg_task):
    """
    :type localization_kit: LocalizationKit
    :raises DVXFailure: if the connection to the server fails, or the server
        returns a non-success status code for this action.
    :rtype: None
    """
    from vendors.models import VendorManifest

    try:
        t_lcid = localization_kit.tep_task.service.target.dvx_lcid
        vendormanifest_result = VendorManifest.objects.filter(vendor=localization_kit.tep_task.assignee_object_id)[0]
        payload = {
            's3Bucket': settings.AWS_STORAGE_BUCKET_NAME,
            'jobID': localization_kit.project.id,
            'analysisCode': localization_kit.analysis_code,
            'bg_task': bg_task.id,
            'tLangId': t_lcid,
            'ExportFormat': vendormanifest_result.vendortranslationtaskfiletype.code,
        }

        r = api_get(settings.VIA_PREP_KIT_URL, payload)

    except Exception:
        logger.warn(u"VendorManifest issue with original payload, trying standard Word RTF %s" % (localization_kit.tep_task.assignee_object_id))
        payload = {
            's3Bucket': settings.AWS_STORAGE_BUCKET_NAME,
            'jobID': localization_kit.project.id,
            'analysisCode': localization_kit.analysis_code,
            'bg_task': bg_task.id,
            'tLangId': t_lcid,
            'ExportFormat': settings.DVX_EXTERNAL_FORMAT_RTF,
        }
        
        r = api_get(settings.VIA_PREP_KIT_URL, payload)


def pre_translate_kit_v2(localization_kit, bg_task):
    """
    :type localization_kit: LocalizationKit
    :raises DVXFailure: if the connection to the server fails, or the server
        returns a non-success status code for this action.
    :rtype: None
    """
    payload = {
        's3Bucket': settings.AWS_STORAGE_BUCKET_NAME,
        'jobID': localization_kit.project.id,
        'analysisCode': localization_kit.analysis_code,
        'bg_task': bg_task.id,
    }

    r = api_get(settings.VIA_PRE_TRANS_URL, payload)


def analysis_from_json(localization_kit, json_analysis):
    localization_kit.analysis_code = json_analysis['analysisCode']
    localization_kit.analysis_completed = timezone.now()
    localization_kit.save()

    for f in json_analysis['file']:
        for s in f['statistics']:
            analysis_attributes = s['wordCount'].copy()
            source = Locale.objects.get(dvx_lcid=s['sLangID'])
            target = Locale.objects.get(dvx_lcid=s['tLangID'])
            analysis_attributes.update(
                {
                    'asset_id': f['id'],
                    'source_locale': source,
                    'target_locale': target,
                    'page_count': s['pageCount'],
                    'image_count': s['imageCount'],
                    'no_match': s['wordCount']['noMatch'],
                }
            )
            for field in ['noMatch', 'locked', 'total']:
                del analysis_attributes[field]

            asset = FileAsset.objects.get(pk=f['id'])

            try:
                analysis = asset.analysis_for_target(target)
            except FileAnalysis.DoesNotExist:
                FileAnalysis.objects.create(**analysis_attributes)
            else:
                for key, value in analysis_attributes.items():
                    setattr(analysis, key, value)
                analysis.save()

            if s['wordCount']['total'] == 0:
                asset.status = ANALYSIS_STATUS_ERROR
            else:
                asset.status = ANALYSIS_STATUS_SUCCESS
            asset.save()


def analyze_payload(localization_kit):
    localization_kit.analysis_started = timezone.now()
    localization_kit.save()
    file_set = localization_kit.source_files()
    client = localization_kit.project.client
    dvx_subject_code = client.manifest.teamserver_client_subject.dvx_subject_code
    payload = {
        "customerID": u"{0}".format(client.manifest.teamserver_client_code),
        "customerName": u"{0}".format(client.name),
        "subjectCode": u"{0}".format(dvx_subject_code),
        "jobID": localization_kit.project.id,
        "jobName": u"{0}".format(localization_kit.project.name),
        "type": u"TRANS",
        "tm": u"{0}".format(localization_kit.project.industry.code),
        "UseTeamServerTM": settings.VIA_API_DVX_TEAMSERVER_USE_TM and client.manifest.teamserver_tm_enabled,
        "UseMachineTranslation": settings.VIA_API_DVX_TEAMSERVER_USE_MT,
        "target": [dict(lcid=locale.dvx_lcid) for locale in
                   localization_kit.project.target_locales.all()],
        "source": [{"lcid": localization_kit.project.source_locale.dvx_lcid}],
        "s3Bucket": u"{0}".format(settings.AWS_STORAGE_BUCKET_NAME),
        "file": [file_dict(asset) for asset in file_set]
    }
    return payload


@task
def analyze_kit(localization_kit_id, callback=None):
    """
    :param int localization_kit_id: ID of a LocalizationKit
    :param celery.signature callback: run this next (in this process)
    :raises DVXFailure: if the connection to the server fails, or the server
        returns a non-success status code for this action.
    :rtype: None
    """
    from localization_kits.models import LocalizationKit
    localization_kit = LocalizationKit.objects.get(pk=localization_kit_id)
    payload = analyze_payload(localization_kit)

    try:
        r = api_post(settings.VIA_ANALYSIS_URL, payload)

        analysis_from_json(localization_kit, r)
    except Exception:
        analysis_failed_action(localization_kit)
        raise

    if callback:
        # Run the callback synchronously, in-process. Not using celery's
        # workflow canvas (either link=callback or chain(analyze, callback))
        # because tracking the state of multi-task workflows becomes
        # unreasonable and the delay between tasks is significant.
        callback()


def analyze_kit_v2(localization_kit, bg_task=None):
    """Request an analysis.

    Instead of waiting the analysis in this HTTP response, the v2 API will
    POST the result back to localization_kits.api_views.Analysis.
    """
    payload = analyze_payload(localization_kit)
    payload['bg_task'] = bg_task.id
    try:
        # FIXME: V2 URL?
        api_post(settings.VIA_ANALYSIS_URL, payload)
    except Exception:
        analysis_failed_action(localization_kit)
        raise

