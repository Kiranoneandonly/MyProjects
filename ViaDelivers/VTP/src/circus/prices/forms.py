# from django import forms
# from clients.models import Client
# from services.models import Service, ServiceType, ScopeUnit, Locale, Vertical
#
#
# SERVICE_FIELDS = {
#     'service_type': {
#         'field': forms.ModelChoiceField,
#         'kwargs': {
#             'required': True,
#             'empty_label': None,
#         },
#     },
#     'unit_of_measure': {
#         'field': forms.ModelChoiceField,
#         'kwargs': {
#             'required': True,
#             'empty_label': None,
#         },
#     },
#     'source': {
#         'field': forms.ModelChoiceField,
#         'kwargs': {
#             'required': False,
#         },
#     },
#     'target': {
#         'field': forms.ModelMultipleChoiceField,
#         'kwargs': {
#             'required': False,
#         },
#     }
# }
#
# CHARGE_FIELDS = {
#     'vertical': {
#         'field': forms.ModelChoiceField,
#         'kwargs': {
#             'required': True,
#             'empty_label': None,
#         }
#     },
#     'client': {
#         'field': forms.ModelChoiceField,
#         'kwargs': {
#             'required': False
#         }
#     }
# }
#
# COST_FIELDS = {
#     'vertical': {
#         'field': forms.ModelChoiceField,
#         'kwargs': {
#             'required': True,
#             'empty_label': None,
#         }
#     }
# }
#
#
# def set_service_filter_defaults(filters):
#     for field, properties in SERVICE_FIELDS.iteritems():
#         if not filters.get(field) and properties['kwargs']['required']:
#             filters[field] = Service._meta.get_field(field).rel.to.objects.default_id()
#     return filters

#
# def set_price_filter_defaults(filters):
#     filters = set_service_filter_defaults(filters)
#     for field, properties in CHARGE_FIELDS.iteritems():
#         if not filters.get(field) and properties['kwargs']['required']:
#             filters[field] = ServiceCharge._meta.get_field(field).rel.to.objects.default_id()
#     return filters


# def get_service_rows(filters):
#     rows = []
#     client = Client.objects.for_filter(filters)
#     vertical = Vertical.objects.for_filter(filters)
#     for service_type in ServiceType.objects.for_filter(filters):
#         for uom in ScopeUnit.objects.for_filter(filters):
#             for source in Locale.objects.for_filter(filters, 'source'):
#                 for target in Locale.objects.for_filter(filters, 'target'):
#                     price = ServiceCharge.objects.price_for_service(
#                         vertical, client, service_type, uom, source, target) or ''
#
#                     default_price = None
#                     if client:
#                         default_price = ServiceCharge.objects.price_for_service(
#                             vertical, None, service_type, uom, source, target)
#
#                     price_name = ServiceCharge.objects.serialize_ids(
#                         vertical, client, service_type, uom, source, target)
#
#                     rows.append({
#                         'vertial': vertical,
#                         'service_type': service_type,
#                         'unit_of_measure': uom,
#                         'source': source,
#                         'target': target,
#                         'client': client,
#                         'price': {
#                             'id': price_name,
#                             'name': price_name,
#                             'value': price,
#                         },
#                         'default_price': default_price,
#                     })
#     return rows


# class PriceFilterForm(forms.Form):
#     def __init__(self, *args, **kwargs):
#         super(PriceFilterForm, self).__init__(*args, **kwargs)
#         for field, properties in SERVICE_FIELDS.iteritems():
#             field_kwargs = properties['kwargs'].copy()
#             field_kwargs['queryset'] = Service._meta.get_field(field).rel.to.objects.all()
#             self.fields[field] = properties['field'](**field_kwargs)

#
# class ServiceChargeForm(PriceFilterForm):
#     def __init__(self, *args, **kwargs):
#         super(ServiceChargeForm, self).__init__(*args, **kwargs)
#         for field, properties in CHARGE_FIELDS.iteritems():
#             field_kwargs = properties['kwargs'].copy()
#             field_kwargs['queryset'] = ServiceCharge._meta.get_field(field).rel.to.objects.all()
#             self.fields[field] = properties['field'](**field_kwargs)
