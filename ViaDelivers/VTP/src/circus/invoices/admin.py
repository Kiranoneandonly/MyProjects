from django.contrib import admin
from invoices.models import Invoice, InvoiceNotes


class InvoiceAdmin(admin.ModelAdmin):
    list_display = ['project', 'due_date', 'order_amount', 'invoice_amount',
                    'ok_to_invoice', 'billing_paid']


class InvoiceNotesAdmin(admin.ModelAdmin):
    list_display = ['invoice', 'note', 'user']


admin.site.register(Invoice, InvoiceAdmin)
admin.site.register(InvoiceNotes, InvoiceNotesAdmin)
