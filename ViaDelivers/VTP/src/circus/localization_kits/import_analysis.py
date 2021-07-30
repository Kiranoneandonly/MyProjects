from __future__ import unicode_literals
import csv
import logging
from localization_kits.models import FileAsset, PLACEHOLDERFILE_ASSET, FileAnalysis, LocaleTranslationKit, SOURCEFILE_ASSET
from services.models import Locale

LOG_ENCODING = 'latin-1'

logger = logging.getLogger('circus.' + __name__)


def skip_rows(rows, count):
    for x in xrange(count):
        rows.pop(0)


def skip_until(rows, starts_with, column=0):
    while not unicode(rows[0][column], LOG_ENCODING).replace('"', '').strip().startswith(starts_with):
        rows.pop(0)


def get_cell_data(cell, starts_with):
    if not cell.replace('"', '').strip().startswith(starts_with):
        return None
    return cell.replace('"', '').strip().replace(starts_with, '')


def get_count_row(log_rows):
    row = log_rows.pop(0)
    return row[1], row[3]


def get_counts_block(log_rows):
    data = {}
    errors = []
    try:
        skip_until(log_rows, 'Duplicates', 1)
        while True:
            row = log_rows.pop(0)
            if row[1] == 'Internal Repetition':
                break
            try:
                data[row[1]] = int(row[3])
            except:
                data[row[1]] = 0
                errors.append("couldn't decode value for {0}".format(row[1]))
    except:
        errors.append('get_counts_block')
    return data, errors


def consume_language(log_rows):
    data = {}
    errors = []
    language_name = ''
    try:
        language_name = get_cell_data(unicode(log_rows.pop(0)[0], LOG_ENCODING), 'Summary - ')
        skip_rows(log_rows, 4)
        data['file_count'] = get_cell_data(unicode(log_rows.pop(0)[0], LOG_ENCODING), 'Files: ')

        skip_until(log_rows, 'All Files')
        data['totals'], data['errors'] = get_counts_block(log_rows)
        data['files'] = {}

        skip_until(log_rows, 'File Details')
        skip_rows(log_rows, 2)

        while not unicode(log_rows[0][0], LOG_ENCODING).replace('"', '').strip().startswith('Summary'):
            filename = unicode(log_rows[0][0], LOG_ENCODING)
            data['files'][filename], count_errors = get_counts_block(log_rows)
            if count_errors:
                errors.extend(count_errors)
            if len(log_rows) < 2:
                log_rows = []
                break
            skip_rows(log_rows, 1)
    except Exception:
        logger.error("consume_language error, language=%r", language_name, exc_info=True)
        errors.append('consume_language (language=%r)' % (language_name,))
    return language_name, data, errors


def process_log(log_reader):
    results = {'errors': [], 'languages': {}}
    try:
        # this could use a lot of memory for a large log
        log_rows = list(log_reader)
        while log_rows:
            lang, data, errors = consume_language(log_rows)
            results['errors'].extend(errors)
            if lang:
                results['languages'][lang] = data
    except Exception, error:
        logger.error("import_analysis error", exc_info=True)
        results['errors'].append(u"Error in process_log: %s" % (error,))
    return results


def process_log_file(project, analysis_file):
    log_reader = csv.reader(analysis_file, delimiter=str(','), quotechar=str('"'))
    data = process_log(log_reader)
    errors = data['errors']
    if not errors:
        errors = update_analysis(project, data['languages'])
    return errors


LOG_CATEGORY_TO_FIELD_NAME = {
    'Duplicates': 'duplicate',
    'Guaranteed Matches': 'guaranteed',
    'Exact Matches': 'exact',
    '95% - 99%': 'fuzzy9599',
    '85% - 94%': 'fuzzy8594',
    '75% - 84%': 'fuzzy7584',
    '50% - 74%': 'fuzzy5074',
    'No Match': 'no_match',
}


def update_analysis(project, language_data):
    """
    :type project: projects.models.Project project
    :param dict[str, dict] language_data: data for each language in the analysis
    :return: list of errors
    :rtype: list[unicode]
    """
    errors = []
    source_locale = project.source_locale
    for language, analysis in language_data.iteritems():
        try:
            target_locale = Locale.objects.get(dvx_log_name=language)
        except Locale.DoesNotExist:
            logger.error("Analysis encountered unknown dvx_log_name %r", language)
            errors.append(u'unknown locale: {0}'.format(language))
            continue

        project.target_locales.add(target_locale)

        locale_trans_kit, created = LocaleTranslationKit.objects.get_or_create(
            kit=project.kit,
            target_locale=target_locale
        )

        sourcefiles_qs = FileAsset.objects.filter(
            asset_type=SOURCEFILE_ASSET,
            kit_id=project.kit_id)

        for analyzed_file, counts in analysis['files'].iteritems():
            try:
                asset = sourcefiles_qs.get(orig_name=analyzed_file)
            except FileAsset.DoesNotExist:
                try:
                    asset = sourcefiles_qs.get(prepared_name=analyzed_file)
                except FileAsset.DoesNotExist:
                    asset = None

            if not asset:
                asset, created = FileAsset.objects.get_or_create(
                    asset_type=PLACEHOLDERFILE_ASSET,
                    kit_id=project.kit_id,
                    orig_name=analyzed_file
                )

            analysis_for_locale, created = FileAnalysis.objects.get_or_create(
                asset_id=asset.id,
                source_locale=source_locale,
                target_locale=target_locale
            )
            analysis_for_locale.message = 'From imported log'

            for log_key, field in LOG_CATEGORY_TO_FIELD_NAME.iteritems():
                try:
                    setattr(analysis_for_locale, field, counts[log_key])
                except:
                    errors.append('could not set {0} to {1}'.format(field, counts.get(log_key, None)))
            analysis_for_locale.save()
            asset.status = "analysis_complete"
            asset.save()
    return errors
