# from decimal import Decimal
# from django.utils.translation import ugettext as _
# from django.core.exceptions import PermissionDenied
# from django.http import HttpResponse
# from django.views.decorators.csrf import csrf_exempt
# from django.views.generic import TemplateView


# def clean_price(value):
#     return Decimal(value)

#
# class PricesView(TemplateView):
#     template_name = "via/prices/prices.html"
#
#     def get_context_data(self, **kwargs):
#         context = super(PricesView, self).get_context_data()
#
#         filters = set_price_filter_defaults(self.request.GET.copy())
#         form = ServiceChargeForm(filters)
#
#         context['form'] = form
#         context['services'] = get_service_rows(form.data)
#
#         self.request.breadcrumbs(_("Prices"), self.request.path_info)
#         return context


# @csrf_exempt
# def update_price(request):
#     if not request.method == 'POST' or not request.is_ajax():
#         raise PermissionDenied
#
#     charge_object = ServiceCharge.objects.from_id_string(request.POST.get('service'))
#     charge_amount = request.POST.get('price')
#     if charge_amount == '':
#         try:
#             charge_object.delete()
#         except:
#             pass
#         return HttpResponse('')
#
#     else:
#         charge_amount = clean_price(charge_amount)
#         charge_object.unit_price = charge_amount
#         charge_object.save()
#
#     return HttpResponse(str(charge_object.unit_price))
