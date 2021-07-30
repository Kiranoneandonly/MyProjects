from django.contrib import admin
from finance.models import ProjectPayment


class ProjectPaymentAdmin(admin.ModelAdmin):
    list_display = ['payment_method',
        'ca_invoice_number', 'note']

    def project_name(self, obj):
        return obj.project.name

admin.site.register(ProjectPayment, ProjectPaymentAdmin)
