# -*- coding: utf-8 -*-
from urlparse import urljoin
from django import template
from django.conf import settings
from django.core.urlresolvers import reverse
from localization_kits.models import get_project_asset_path
from services.models import DocumentType
from shared.forms import S3UploadForm

register = template.Library()


@register.simple_tag
def source_upload_form(loc_kit):
    """
    :type loc_kit: localization_kits.models.LocalizationKit
    """
    redirect = reverse('source_file_upload_complete', args=(loc_kit.id,))

    asset_path = settings.MEDIA_URL[1:] + get_project_asset_path(loc_kit, '${filename}')

    form = S3UploadForm(asset_path, settings.BASE_URL + redirect)

    return form.as_form_html()

@register.simple_tag
def auto_job_source_upload_form(loc_kit):
    """
    :type loc_kit: localization_kits.models.LocalizationKit
    """
    redirect = reverse('auto_job_source_file_upload_complete', args=(loc_kit.id,))

    asset_path = settings.MEDIA_URL[1:] + get_project_asset_path(loc_kit, '${filename}')

    form = S3UploadForm(asset_path, settings.BASE_URL + redirect)

    return form.as_form_html()

@register.simple_tag
def reference_upload_form(loc_kit):
    """
    :type loc_kit: localization_kits.models.LocalizationKit
    """
    redirect = reverse('reference_file_upload_complete', args=(loc_kit.id,))

    asset_path = settings.MEDIA_URL[1:] + get_project_asset_path(loc_kit, '${filename}')

    form = S3UploadForm(asset_path, settings.BASE_URL + redirect)

    return form.as_form_html()


@register.simple_tag
def reference_replace_form(loc_kit, asset_id):
    """
    :type loc_kit: localization_kits.models.LocalizationKit
    """
    redirect = reverse('reference_file_replace_complete', args=(asset_id,))

    asset_path = settings.MEDIA_URL[1:] + get_project_asset_path(loc_kit, '${filename}')

    form = S3UploadForm(asset_path, settings.BASE_URL + redirect)

    return form.as_form_html()

@register.simple_tag
def translation_file_upload_form(ltk):
    """
    :type ltk: localization_kits.models.LocaleTranslationKit
    """
    redirect = reverse('kit_translation_file_upload_complete', args=(ltk.id,))

    asset_path = settings.MEDIA_URL[1:] + \
        ltk.translation_file.field.generate_filename(ltk, '${filename}')

    import re
    if re.search(r"\\+", asset_path):
        asset_path = re.sub(r"\\+", '/', asset_path)

    asset_path = asset_path.replace("filename", "${filename}")

    form = S3UploadForm(asset_path, settings.BASE_URL + redirect)

    return form.as_form_html()


@register.simple_tag
def reference_file_upload_form(ltk):
    """
    :type ltk: localization_kits.models.LocaleTranslationKit
    """
    redirect_to = reverse('ltk_reference_upload_complete',
                          kwargs={'ltk_id': ltk.id})
    redirect_to = urljoin(settings.BASE_URL, redirect_to)

    asset_path = (
        settings.MEDIA_URL[1:] +
        ltk.reference_file.field.generate_filename(ltk, '${filename}'))

    import re
    if re.search(r"\\+", asset_path):
        asset_path = re.sub(r"\\+", '/', asset_path)

    asset_path = asset_path.replace("filename", "${filename}")

    form = S3UploadForm(asset_path, redirect_to)
    return form.as_form_html()


@register.simple_tag
def prepared_file_upload_form(asset):
    """
    :type asset: localization_kits.models.FileAsset
    """
    redirect_to = reverse('prepared_file_upload_complete',
                          kwargs={'file_asset_id': asset.id})
    redirect_to = urljoin(settings.BASE_URL, redirect_to)

    asset_path = (
        settings.MEDIA_URL[1:] +
        asset.prepared_file.field.generate_filename(asset, '${filename}'))

    import re
    if re.search(r"\\+", asset_path):
        asset_path = re.sub(r"\\+", '/', asset_path)

    asset_path = asset_path.replace("filename", "${filename}")

    form = S3UploadForm(asset_path, redirect_to)
    accepted_types = DocumentType.objects.filter(can_auto_estimate=True)
    accepted_types = [('.' + doc_type.code) for doc_type in accepted_types]
    form.fields['file'].widget.attrs['accept'] = ','.join(accepted_types)
    return form.as_form_html()
