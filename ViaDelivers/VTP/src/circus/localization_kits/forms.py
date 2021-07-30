from django import forms
from django.forms.models import inlineformset_factory
from localization_kits.models import FileAsset, LocalizationKit, FileAnalysis, SOURCEFILE_ASSET
from shared.widgets import DateTimeWidget

class LocalizationKitForm(forms.ModelForm):
    class Meta:
        model = LocalizationKit
        exclude = ('is_deleted', 'obsolete_analyzing', 'analysis_code', 'analysis_started', 'analysis_completed',)


class FileAssetForm(forms.ModelForm):

    class Meta:
        model = FileAsset
        exclude = ('orig_name', 'is_deleted', 'locale', 'asset_type', 'status', 'queued_timestamp', 'analysis')


class FileAnalysisForm(forms.ModelForm):

    def __init__(self, *args, **kwargs):
        file_analysis = kwargs.get("instance")
        super(FileAnalysisForm, self).__init__(*args, **kwargs)

        self.fields['guaranteed'].label = 'Perfect'
        self.fields['no_match'].label = 'No Match'

        if file_analysis.asset.asset_type == SOURCEFILE_ASSET:
            self.fields['asset'].widget = forms.HiddenInput()
        else:
            # Since placeholder, give option to change to Source File
            self.fields['asset'].queryset = FileAsset.objects.filter(id__in=[sf.id for sf in file_analysis.asset.kit.source_files()])

    class Meta:
        model = FileAnalysis
        exclude = ('source_locale', 'target_locale', 'message', 'is_deleted', 'page_count', 'image_count')


FileAssetFormSet = inlineformset_factory(LocalizationKit, FileAsset, form=FileAssetForm, extra=1, can_delete=True)
