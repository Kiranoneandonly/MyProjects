from django.forms import HiddenInput
from django.shortcuts import render
from django.utils.translation import ugettext as _
from django.core.exceptions import PermissionDenied
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import TemplateView
from django.contrib import messages
from preferred_vendors.forms import PreferredVendorFilterForm, PreferredVendorFormSet
from preferred_vendors.models import PreferredVendor


class PreferredVendorsView(TemplateView):
    template_name = "via/preferred_vendors/preferred_vendors.html"

    def get_vendor_formset(self, filter_form):
        if 'save-vendors' in self.request.POST:
            preferred_vendors_formset = PreferredVendorFormSet(self.request.POST)
            if preferred_vendors_formset.is_valid():
                # TODO Fix service_type save issue
                preferred_vendors_formset.save()
                messages.add_message(self.request, messages.SUCCESS, _('Preferred Suppliers has been saved.'))
        else:
            preferred_vendors_formset = PreferredVendorFormSet(queryset=PreferredVendor.objects.filter(
                vertical=filter_form.cleaned_data['vertical'],
                client=filter_form.cleaned_data['client'],
                source=filter_form.cleaned_data['source'],
                target=filter_form.cleaned_data['target'],
                service_type=filter_form.cleaned_data['service_type'],
            ).order_by('priority', 'vendor__name'))

        for form in preferred_vendors_formset.forms:
            for key in ['vertical', 'client', 'source', 'target', 'service_type']:
                if key not in form.initial:
                    form.initial[key] = filter_form.cleaned_data[key]
                form.fields[key].widget = HiddenInput()
        return preferred_vendors_formset

    def post(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        return render(request=request, template_name=self.template_name, context=context)

    def get_context_data(self, **kwargs):
        context = super(PreferredVendorsView, self).get_context_data()
        if self.request.POST:
            filter_form = PreferredVendorFilterForm(self.request.POST)
            if filter_form.is_valid():
                context['preferred_vendors_formset'] = self.get_vendor_formset(filter_form)

        else:
            filter_form = PreferredVendorFilterForm()

        context['filter_form'] = filter_form

        self.request.breadcrumbs(_("Preferred Vendors"), self.request.path_info)
        return context


@csrf_exempt
def update_preferred_vendor(request):
    if not request.method == 'POST' or not request.is_ajax():
        raise PermissionDenied

    preferred_vendor_object = PreferredVendor.objects.from_id_string(request.POST.get('service'))
    # set the vendor for the params given
