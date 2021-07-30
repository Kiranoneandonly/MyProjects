from django.contrib import admin
from quality_defects.models import QualityDefect


class QualityDefectAdmin(admin.ModelAdmin):
    list_display = ['pk', 'quality_defect', 'title']
    search_fields = ('pk', 'quality_defect', 'title',)

admin.site.register(QualityDefect, QualityDefectAdmin)