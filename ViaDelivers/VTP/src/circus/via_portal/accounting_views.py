from decimal import Decimal
from django.contrib import messages
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from django.views.generic import base, DetailView, UpdateView
from invoices.models import Invoice
from projects.models import Project
from via_portal.forms import ProjectAccountingSummaryForm, InvoiceForm
from via_portal.views import ViaLoginRequiredMixin, ProjectDetailMixin


class ProjectAccountingSummaryView(ViaLoginRequiredMixin, base.ContextMixin, base.View):
    template_name = 'via/projects/accounting/summary.html'

    def form_invalid(self, form):
        pass

    def get_context_data(self, project=None, **kwargs):
        context = super(ProjectAccountingSummaryView, self).get_context_data(**kwargs)

        sum_via_invoices_all = project.sum_via_invoices_all()
        sum_via_invoices_billed = project.sum_via_invoices_billed()
        sum_via_invoices_yet_to_bill = sum_via_invoices_all - sum_via_invoices_billed

        original_order_amount = project.original_order_amount()
        sum_orders = project.sum_orders()
        sum_change_orders = sum_orders - original_order_amount
        invoice_order_discrepancy = sum_via_invoices_all - sum_orders

        # TODO dgf 2013-08-12: replace with real spend, estimated_gm
        total_spend = sum_via_invoices_all * Decimal(0.33).quantize(Decimal('.001'))
        estimated_gm = sum_via_invoices_all * Decimal(0.50).quantize(Decimal('.001'))

        data = {
            'sum_via_invoices_all': sum_via_invoices_all,
            'sum_via_invoices_sent': sum_via_invoices_billed,
            'sum_via_invoices_yet_to_send': sum_via_invoices_yet_to_bill,
            'original_order_amount': original_order_amount, 'sum_change_orders': sum_change_orders,
            'invoice_order_discrepancy': invoice_order_discrepancy, 'total_spend': total_spend,
            'actual_gm': sum_via_invoices_all - total_spend, 'estimated_gm': estimated_gm,
            'invoices_or_orders_exist': project.invoice_set.exists()
        }
        return dict(context, **data)

    def get(self, request, pk=None):
        project = get_object_or_404(Project, pk=pk)
        form = ProjectAccountingSummaryForm(instance=project)
        context_data = self.get_context_data(project=project, form=form)

        return render(request, self.template_name, context_data)

    def post(self, request, pk=None, *args, **kwargs):
        project = get_object_or_404(Project, pk=pk)
        form = ProjectAccountingSummaryForm(request.POST, instance=project)

        if form.is_valid():
            data = form.clean()
            project.payment_details.ca_invoice_number = data['ca_invoice_number']
            project.payment_details.save()
            project.current_user = request.user.id
            project.save()

            if not project.invoice_set.count() and data['original_price'] and data['original_invoice_count']:
                # initialize invoices not yet generated for this job
                initialize_invoices(project, data)

            form = ProjectAccountingSummaryForm(instance=project)
        else:
            self.form_invalid(form)

        context_data = self.get_context_data(project=project, form=form)

        # TODO: fix validation errors when string passed to form.original_invoice_count
        return render(request, self.template_name, context_data)


def initialize_invoices(project, data):
    # TODO
    # initialize one invoice with order_amount for the total value of data['original_price']
    # initialize n invoices with invoice_amount / n where invoice_amount == data['original_price']
    # and n == original_invoice_count
    original_price = data['original_price']
    original_invoice_count = data['original_invoice_count']
    price_per_invoice = original_price / original_invoice_count
    now = timezone.now()

    order = Invoice.objects.create(project=project, order_amount=original_price, due_date=now)
    order.save()

    while original_invoice_count > 0:
        original_invoice_count -= 1
        original_price -= price_per_invoice
        invoice = Invoice.objects.create(project=project, invoice_amount=price_per_invoice, due_date=now)
        invoice.save()


class InvoiceCreateView(ViaLoginRequiredMixin, base.View):
    template_name = 'via/projects/accounting/invoice.html'

    def get(self, request, pk=None, *args, **kwargs):
        project = get_object_or_404(Project, pk=pk)
        form = InvoiceForm({"project": project})
        return render(request, self.template_name, {"form": form, 'project': project})

    def post(self, request, pk=None, *args, **kwargs):
        project = get_object_or_404(Project, pk=pk)
        form = ProjectAccountingSummaryForm(request.POST, instance=project)

        if form.is_valid():
            data = form.clean()
            project.payment_details.ca_invoice_number = data['ca_invoice_number']
            project.payment_details.save()
            project.current_user = request.user.id
            project.save()
            form = ProjectAccountingSummaryForm(instance=project)
        else:
            # FIXME: This doesn't have FormMixin, it's got no .form_invalid
            self.form_invalid(form)

        return render(request, self.template_name, {'form': form, 'project': project})


class InvoiceEditView(ViaLoginRequiredMixin, base.View):
    template_name = 'via/projects/accounting/invoice.html'

    def get(self, request, *args, **kwargs):
        return render(request, self.template_name, {})


class InvoiceDeleteView(ViaLoginRequiredMixin, base.View):
    template_name = 'via/projects/accounting/invoice_delete.html'

    def get(self, request, pk=None, invoice_pk=None, *args, **kwargs):
        project = get_object_or_404(Project, pk=pk)
        invoice = get_object_or_404(Invoice, pk=invoice_pk)
        return render(request, self.template_name, {'project': project, 'invoice': invoice})

    def post(self, request, pk=None, invoice_pk=None, *args, **kwargs):
        pk = pk
        invoice_pk = invoice_pk
        invoice = Invoice.objects.get(id=invoice_pk)
        invoice.delete()
        messages.success(request, _(u"Invoice {0} deleted.".format(invoice_pk)))
        return HttpResponseRedirect(reverse('via_job_accounting_invoice_list', args=(pk,)))


class ProjectAccountingInvoiceListView(ViaLoginRequiredMixin, DetailView):
    template_name = 'via/projects/accounting/invoice_list.html'

    def get(self, request, pk=None, *args, **kwargs):
        project = get_object_or_404(Project, pk=pk)
        invoices = Invoice.objects.filter(project=project).order_by('id', '-order_amount', '-invoice_amount')
        return render(request, self.template_name, {"invoices": invoices, "project": project})


class ProjectAccountingPurchaseOrderListView(ViaLoginRequiredMixin, ProjectDetailMixin, DetailView):
    template_name = 'via/projects/accounting/purchase_order_list.html'


class PurchaseOrderView(ViaLoginRequiredMixin, UpdateView):
    template_name = 'via/projects/accounting/purchase_order.html'
