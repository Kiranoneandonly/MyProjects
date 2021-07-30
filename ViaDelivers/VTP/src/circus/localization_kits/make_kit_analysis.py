from django.contrib.messages import ERROR, WARNING, SUCCESS
from localization_kits.models import FileAnalysis

# we should really rename this file manage_kit_analysis or something. Is this a ViewModel? A generator?


def make_project_loc_kit_analysis(project):

    if not project.source_locale or not project.target_locales_count():
        return ERROR, u"Source and target locales must be set to generate kit analysis"

    assets = list(project.kit.source_files())
    if not assets:
        return WARNING, u"Could not generate kit analysis: no source assets"

    # delete existing analysis for assets / locales
    # FileAnalysis.objects.filter(asset=project.kit.source_files()).delete()

    # For each FileAsset in a LocKit, we need to build a base Analysis entry for each language
    for target in project.target_locales.all():
        for asset in assets:
            # -------------
            # make baseline analysis
            analysis_for_locale, created = FileAnalysis.objects.get_or_create(
                asset_id=asset.id,
                source_locale=project.source_locale,
                target_locale=target
            )
            analysis_for_locale.save()

    return SUCCESS, u"Estimate > Analysis generated for project"
