from django.contrib.messages import SUCCESS, ERROR
from localization_kits.models import LocaleTranslationKit

# we should really rename this file manage_locale_translation_kit or something. Is this a ViewModel? A generator?

def make_localetranslationkit(project):
    # Clear Cache to ensure proper rebuild when Languages have been removed
    from shared.utils import clear_cache
    clear_cache()

    for tl in project.target_locales.all():
        ltk, created = LocaleTranslationKit.objects.get_or_create(
            kit=project.kit,
            target_locale=tl
        )
    return SUCCESS, u"Locale Localization Kits generated for project"


def purge_old_localetranslationkit(project):
    try:
        # delete LocaleTranslationKit for all removed Target Locales
        LocaleTranslationKit.objects.filter(kit_id=project.kit.id).exclude(
            target_locale_id__in=project.target_locales.all().values_list('id', flat=True)
        ).exclude(target_locale=None).delete()
        return SUCCESS, u"Old Locale Localization Kits purged from project"
    except:
        return ERROR, u"Old Locale Localization Kits purged from project issues"