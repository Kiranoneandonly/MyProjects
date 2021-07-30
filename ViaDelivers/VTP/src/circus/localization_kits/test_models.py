from django.test import TestCase
from django.conf import settings
from localization_kits.models import LocalizationKit, FileAsset, \
    SOURCEFILE_ASSET, PLACEHOLDERFILE_ASSET, LocaleTranslationKit
from services.models import Locale, DocumentType
from shared.datafactory import create_project
from mock import patch


class TestLocalizationKit(TestCase):
    def setUp(self):
        self.localization_kit = LocalizationKit.objects.create()
        self.file1 = FileAsset.objects.create(orig_name="first",
                                              asset_type=SOURCEFILE_ASSET,
                                              kit=self.localization_kit)
        self.file2 = FileAsset.objects.create(orig_name="second",
                                              asset_type=SOURCEFILE_ASSET,
                                              kit=self.localization_kit)
        self.file3 = FileAsset.objects.create(orig_name="placeholder",
                                              asset_type=PLACEHOLDERFILE_ASSET,
                                              kit=self.localization_kit)

        for ext in 'odt', 'html':
            DocumentType.objects.get_or_create(code=ext, can_auto_estimate=True)

        for ext in '7z', 'zip':
            DocumentType.objects.get_or_create(code=ext, can_auto_estimate=False)


    def test_source_files(self):
        self.assertEqual(
            list(self.localization_kit.source_files().order_by('id')),
            [self.file1, self.file2])


    def test_placeholder_files(self):
        self.assertEqual(list(self.localization_kit.placeholder_files()),
                         [self.file3])


    def test_can_auto_estimate_doctype(self):
        self.file1.orig_name = 'first.html'
        self.file2.orig_name = 'second.odt'
        self.file1.save()
        self.file2.save()
        self.assertTrue(self.localization_kit.can_auto_estimate_doctype())


    def test_can_auto_estimate_doctype_negative(self):
        self.file1.orig_name = 'first.html'
        self.file2.orig_name = 'second.zip'
        self.file1.save()
        self.file2.save()
        self.assertFalse(self.localization_kit.can_auto_estimate_doctype())

        self.file2.orig_name = 'second.wat_unknown'
        self.file2.save()
        self.assertFalse(self.localization_kit.can_auto_estimate_doctype())


    def test_can_auto_estimate_doctype_prepped(self):
        self.file1.orig_name = 'first.html'
        # .zip is not an auto-estimate type; add a prepared file as .odt,
        # which is.
        self.file2.orig_name = 'second.zip'
        self.file2.prepared_name = 'second.odt'
        self.file1.save()
        self.file2.save()
        self.assertTrue(self.localization_kit.can_auto_estimate_doctype())


    def test_can_auto_estimate_locale(self):
        project = create_project(self.id())
        self.localization_kit.project = project
        result = self.localization_kit.can_auto_estimate_locale()
        self.assertTrue(result)


    def test_can_auto_estimate_locale_too_many_languages(self):
        project = create_project(self.id())
        self.localization_kit.project = project

        # Add a whole bunch of targets to the project.
        targets = []
        for loc in Locale.objects.filter(
                available=True, is_deleted=False,
                if_target_no_auto_estimate=False):
            targets.append(loc)
            if len(targets) > settings.LANGUAGE_COUNT_MAX_TO_AUTO_ESTIMATE:
                break
        else:
            self.fail("Could only add %d targets, need at least %d for test!"
                      % (len(targets),
                         settings.LANGUAGE_COUNT_MAX_TO_AUTO_ESTIMATE))
        project.target_locales.add(*targets)

        result = self.localization_kit.can_auto_estimate_locale()
        self.assertFalse(result)

    # V1 not valid anymore

    #  def test_queue_analysis_tasks(self):
    #     from localization_kits.engine import analyze_kit
    #     project = create_project(self.id())
    #     self.localization_kit.project = project
    #     result = self.localization_kit.queue_analysis_tasks()
    #
    #     self.assertTrue(analyze_kit.name in result.callback_sig)
    #
    #     # TODO: how to inspect the args passed to the async calls?
    #     # also, we didn't mock queue_analysis_tasks, did it actually get queued?
    #     result.revoke()


    def test_queue_analysis_tasks_with_callback(self):
        from projects.models import BackgroundTask
        from localization_kits.engine import prep_kit
        project = create_project(self.id())
        self.localization_kit.project = project
        callback_name = prep_kit.name

        # noinspection PyUnresolvedReferences
        with patch.object(BackgroundTask.objects, 'start_with_callback') as mock_start:
            result = self.localization_kit.queue_analysis_tasks(
                callback=prep_kit.s()
            )

        sig = mock_start.call_args[0][3]
        self.assertEqual(callback_name, sig['task'])

        # TODO: how to inspect the args passed to the async calls?
        # also, we didn't mock queue_analysis_tasks, did it actually get queued?
        result.revoke()


class TestLocaleTranslationKit(TestCase):

    def setUp(self):
        self.loc_kit = LocalizationKit.objects.create()
        self.ltk = LocaleTranslationKit.objects.create(
            kit=self.loc_kit,
            target_locale=Locale.objects.get(lcid=1049))


    def test_reference_file(self):
        self.assertEqual(self.ltk.reference_file, None)

        my_file = "something_reference.doc"
        self.ltk.reference_file = my_file

        self.ltk.save()

        # reload
        self.ltk = LocaleTranslationKit.objects.get(id=self.ltk.id)

        self.assertEqual(self.ltk.reference_file, my_file)


    def test_reference_file_name(self):
        self.ltk.reference_file = "foo/bar/baz/The Reasons.ppt"
        self.assertEqual(self.ltk.reference_file_name(), "The Reasons.ppt")
