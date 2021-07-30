from django.contrib import admin
from localization_kits.models import LocalizationKit, LocaleTranslationKit, FileAsset, FileAnalysis


class FileAssetInline(admin.TabularInline):
    model = FileAsset
    extra = 1


class FileAnalysisInline(admin.TabularInline):
    model = FileAnalysis
    extra = 1


class LocalizationKitAdmin(admin.ModelAdmin):
    list_display = ['project', 'analysis_code', 'get_files_list']
    inlines = [FileAssetInline]

    def get_files_list(self, obj):
        return u', '.join([unicode(f.orig_file) for f in obj.files.all()])
    get_files_list.allow_tags = True
    get_files_list.short_description = 'Files'

    search_fields = ('project__job_number', 'project__name', )
    ordering = ('project__job_number', 'project__name', )


class FileAssetAdmin(admin.ModelAdmin):
    list_display = ['kit', 'orig_name', 'orig_file', 'asset_type', 'status']
    # list_filter = ['status']
    inlines = [FileAnalysisInline]

    search_fields = ('orig_name', 'orig_file', 'status', 'asset_type', 'source_locale__description', 'kit__project__job_number', 'kit__project__id',)
    readonly_fields = ('kit',)
    ordering = ('-kit', 'orig_name', )


class FileAnalysisAdmin(admin.ModelAdmin):
    list_display = ['asset', 'source_locale', 'target_locale', 'page_count', 'image_count']

    search_fields = ('asset__orig_name', 'asset__orig_file', 'asset__prepared_name', 'source_locale__description', 'target_locale__description',)
    ordering = ('-asset', 'source_locale', 'target_locale', )


class LocaleTranslationKitAdmin(admin.ModelAdmin):
    list_display = ['kit', 'analysis_code', 'target_locale', 'translation_file', 'reference_file']

    search_fields = ('kit__id', 'kit__analysis_code', 'analysis_code', 'target_locale__description',)
    readonly_fields = ('kit', 'target_locale',)
    ordering = ('-kit', 'target_locale', )


admin.site.register(FileAsset, FileAssetAdmin)
admin.site.register(FileAnalysis, FileAnalysisAdmin)
admin.site.register(LocaleTranslationKit, LocaleTranslationKitAdmin)
admin.site.register(LocalizationKit, LocalizationKitAdmin)
