from django.views.generic import ListView, DetailView, CreateView, UpdateView
from vendors.forms import VendorForm
from vendors.models import Vendor


class VendorsListView(ListView):
    template_name = "via/vendors/list.html"

    def get_queryset(self):
        return Vendor.objects.all().order_by('id')

    def get_context_data(self, **kwargs):
        context = super(VendorsListView, self).get_context_data(**kwargs)
        return context


class VendorDetailView(DetailView):
    template_name = "via/vendors/detail.html"
    queryset = Vendor.objects.all()
    context_object_name = 'vendor'

    def get_context_data(self, **kwargs):
        context = super(VendorDetailView, self).get_context_data(**kwargs)
        return context


class VendorCreateView(CreateView):
    template_name = "via/vendors/create.html"
    form_class = VendorForm
    context_object_name = 'vendor'

    def get_context_data(self, **kwargs):
        context = super(VendorCreateView, self).get_context_data(**kwargs)
        return context


class VendorUpdateView(UpdateView):
    template_name = "via/vendors/edit.html"
    form_class = VendorForm
    queryset = Vendor.objects.all()
    context_object_name = 'vendor'

    def get_context_data(self, **kwargs):
        context = super(VendorUpdateView, self).get_context_data(**kwargs)
        return context


class VendorTranslationRatesView(UpdateView):
    template_name = "via/vendors/rates.html"
    queryset = Vendor.objects.all()
    context_object_name = 'trans_rates'

    def get_context_data(self, **kwargs):
        context = super(VendorTranslationRatesView, self).get_context_data(**kwargs)
        return context


class VendorNonTranslationRatesView(UpdateView):
    template_name = "via/vendors/rates.html"
    queryset = Vendor.objects.all()
    context_object_name = 'service_rates'

    def get_context_data(self, **kwargs):
        context = super(VendorNonTranslationRatesView, self).get_context_data(**kwargs)
        return context