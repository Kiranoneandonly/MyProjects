import re

from django import forms
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ObjectDoesNotExist
from tinymce import TinyMCE

from accounts.models import CircusUser
from preferred_vendors.models import PreferredVendor
from prices.models import VendorTranslationRate, VendorNonTranslationRate
from projects.states import TASK_CREATED_STATUS
from services.models import Service, PricingFormula
from services.managers import TRANSLATION_EDIT_PROOF_SERVICE_TYPE, TRANSLATION_ONLY_SERVICE_TYPE,\
    LINGUISTIC_QA_SERVICE_TYPE, PROOFREADING_SERVICE_TYPE, MT_POST_EDIT_SERVICE_TYPE, GLOSSARY_DEVELOPMENT_SERVICE_TYPE, LINGUISTIC_TASK_SERVICE_TYPE
from services.models import Service
from tasks.models import Task, VendorPurchaseOrder
from shared.widgets import DateTimeWidget
from django.utils.translation import ugettext_lazy as _
from shared.group_permissions import PROTECTED_HEALTH_INFORMATION_GROUP

class VendorPurchaseOrderAdminForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super(VendorPurchaseOrderAdminForm, self).__init__(*args, **kwargs)
        if self.instance and hasattr(self.instance, 'vendor'):
            qs = Task.objects.select_related().filter(assignee_object_id=self.instance.vendor.id).exclude(status=TASK_CREATED_STATUS)
        else:
            qs = Task.objects.get_empty_query_set()
        self.fields['task'].queryset = qs

    class Meta:
        model = VendorPurchaseOrder
        fields = "__all__"


def encode_assignee(obj, prefix=None):
    type_id = ContentType.objects.get_for_model(obj.__class__).id
    obj_id = obj.id
    form_value = "type:%s-id:%s" % (type_id, obj_id) # e.g."type:12-id:3"
    display_text = str(obj)
    if prefix:
        display_text = prefix + ': ' + display_text
    return form_value, display_text


def decode_assignee(assignee_string):
    matches = re.match("type:(\d+)-id:(\d+)", assignee_string).groups()
    assignee_type_id = matches[0]   # get 45 from "type:45-id:38"
    assignee_id = matches[1]        # get 38 from "type:45-id:38"
    assignee_type = ContentType.objects.get(id=assignee_type_id)
    return assignee_type, assignee_id


class TaskForm(forms.ModelForm):
    # GenericForeignKey form field, will hold combined object_type and object_id
    assignee = forms.ChoiceField(required=False)
    quantity = forms.DecimalField(required=False)
    po_number = forms.IntegerField(required=False)
    actual_hours = forms.DecimalField(required=False)
    reschedule_all_due_dates = forms.BooleanField(required=False, initial=False)
    resend_notification = forms.BooleanField(required=False, initial=False)
    unit_cost = forms.DecimalField(required=False)
    unit_price = forms.DecimalField(required=False)
    price_is_percentage = forms.BooleanField(required=False, disabled=True)
    formula = forms.DecimalField(required=False, disabled=True)
    vendor_minimum = forms.DecimalField(required=False, disabled=True)
    qa_approved = forms.BooleanField(required=False, initial=False)

    notes = forms.CharField(widget=TinyMCE(attrs={'cols': settings.TINYMCE_COLS, 'rows': settings.TINYMCE_ROWS}), required=False)
    via_notes = forms.CharField(widget=TinyMCE(attrs={'cols': settings.TINYMCE_COLS, 'rows': settings.TINYMCE_ROWS}), required=False)
    vendor_notes = forms.CharField(widget=TinyMCE(attrs={'cols': settings.TINYMCE_COLS, 'rows': settings.TINYMCE_ROWS}), required=False)

    class Meta:
        model = Task
        exclude = ['project', 'is_deleted', 'current_user']
        widgets = {
            'accepted_timestamp': DateTimeWidget(),
            'scheduled_start_timestamp': DateTimeWidget(),
            'started_timestamp': DateTimeWidget(),
            'completed_timestamp': DateTimeWidget(),
            'due': DateTimeWidget(),
            'overdue_email_last_sent': DateTimeWidget(),
        }

    def __init__(self, *args, **kwargs):
        project = kwargs.pop("project")
        super(TaskForm, self).__init__(*args, **kwargs)

        self.fields['reschedule_all_due_dates'].label = _('Reschedule')
        self.fields['scheduled_start_timestamp'].label = _('Scheduled Start')
        self.fields['accepted_timestamp'].label = _('Accepted')
        self.fields['started_timestamp'].label = _('Actual Start')
        self.fields['completed_timestamp'].label = _('Actual Completion')
        self.fields['standard_days'].label = _('Standard Days')
        self.fields['express_days'].label = _('Express Days')
        self.fields['rating'].label = _('Rating')
        self.fields['vendor_feedback'].label = _('Vendor feedback')
        self.fields['notes'].label = _('Task Instructions')
        self.fields['via_notes'].label = _('Client Delivery Notes')
        self.fields['vendor_notes'].label = _('Supplier Delivery Notes')
        self.fields['po_number'].label = _('PO #')
        self.fields['quantity'].label = _('Estimate Hours')
        self.fields['unit_cost'].label = _('Unit Cost / %s') % self.instance.service.unit_of_measure
        self.fields['unit_price'].label = _('Unit Price / %s') % self.instance.service.unit_of_measure
        self.fields['price_is_percentage'].label = _('Price is Percentage')
        self.fields['vendor_minimum'].label = _('Vendor minimum')
        self.fields['actual_hours'].label = _('Actual Hours')
        self.fields['create_po_needed'].label = _('Approved')
        self.fields['qa_approved'].label = _('QA Approved')
        self.fields['qa_lead'].label = _('QA Lead')
        self.fields['qa_lead'].widget.attrs['disabled'] = True

        # hide fields
        self.fields['assignee_content_type'].widget = forms.HiddenInput()
        self.fields['assignee_object_id'].widget = forms.HiddenInput()

        try:
            if self.instance.project:
                self.fields['assignee'].choices = self.assignee_as_choices()
                self.fields['assignee'].label = _('Assigned To')

                assignee_content_type_id = self.instance.assignee_content_type_id if self.instance.assignee_content_type_id else 0
                assignee_object_id = self.instance.assignee_object_id if self.instance.assignee_object_id else 0

                self.fields['assignee'].initial = "type:%s-id:%s" % (assignee_content_type_id, assignee_object_id)
        except ObjectDoesNotExist:
            self.fields['assignee'].widget = forms.HiddenInput()

        try:
            self.fields['po_number'].initial = unicode(self.instance.po.po_number or "")
        except ObjectDoesNotExist:
            self.fields['po_number'].initial = ""

        try:
            self.fields['quantity'].initial = self.instance.quantity()
            self.fields['formula'].initial = self.instance.formula()
            self.fields['unit_cost'].initial = self.instance.unit_cost()
            self.fields['unit_price'].initial = self.instance.unit_price()
            self.fields['vendor_minimum'].initial = self.instance.vendor_minimum()
            self.fields['price_is_percentage'].initial = self.instance.price_is_percentage()
            self.fields['actual_hours'].initial = self.instance.actual_hours()
            self.fields['create_po_needed'].initial = self.instance.create_po_needed
            self.fields['qa_approved'].initial = self.instance.qa_approved
        except ObjectDoesNotExist:
            self.fields['quantity'].initial = ""
            self.fields['formula'].initial = ""
            self.fields['unit_cost'].initial = ""
            self.fields['unit_price'].initial = ""
            self.fields['vendor_minimum'].initial = ""
            self.fields['price_is_percentage'].initial = ""
            self.fields['actual_hours'].initial = ""
            self.fields['create_po_needed'].initial = not self.instance.project.delay_job_po
            self.fields['qa_approved'].initial = ""

        self.fields['service'].queryset = Service.objects.filter(source=self.instance.service.source,
                                                                 target=self.instance.service.target,
                                                                 service_type_id=self.instance.service.service_type_id
                                                                 )

        # all other tasks may be predecessor to this task
        self.fields['predecessor'].queryset = Task.objects.filter(project=project, service__target=self.instance.service.target).exclude(id=self.instance.id)

    def assignee_as_choices(self):
        #combine object_type and object_id into a single 'generic_obj' field
        #get all the objects that we want the user to be able to choose from
        #todo figure out how to set the value of the generic_obj select to the choice from db
        choices = []
        choices.insert(0, ('type:0-id:0', '---'))

        #: :type: Task
        task = self.instance
        if task.project.internal_via_project:
            pref_vendors = PreferredVendor.objects.all()
        else:
            pref_vendors = PreferredVendor.objects.vendors(task.project.client.manifest.vertical,
            task.project.client, task.service.source, task.service.target, task.service.service_type,
            task.project.is_phi_secure_client_job()
            )

        already_included_vendors = set()
        for v in pref_vendors.select_related("vendor"):
            vendor = v.vendor
            if vendor.id in already_included_vendors:
                continue

            if task.project.is_phi_secure_client_job():
                if vendor.can_access_phi_secure_job():
                    already_included_vendors.add(vendor.id)
                    assignee = encode_assignee(vendor, 'PS')
                    choices.append(assignee)
            else:
                already_included_vendors.add(vendor.id)
                assignee = encode_assignee(vendor, 'PS')
                choices.append(assignee)

        if task.is_translation():
            rates = VendorTranslationRate.objects.filter(*task.service_filters())
        else:
            rates = VendorNonTranslationRate.objects.filter(*task.service_filters())

        for rate in rates.select_related("vendor"):
            #: :type: Vendor
            vendor = rate.vendor
            if vendor is None:
                continue

            if vendor.id in already_included_vendors:
                continue

            if task.project.is_phi_secure_client_job():
                if vendor.can_access_phi_secure_job():
                    already_included_vendors.add(vendor.id)
                    assignee = encode_assignee(vendor, 'S')
                    choices.append(assignee)
            else:
                already_included_vendors.add(vendor.id)
                assignee = encode_assignee(vendor, 'S')
                choices.append(assignee)

        if task.project.is_phi_secure_client_job():
            via_users = CircusUser.objects.filter(user_type=settings.VIA_USER_TYPE, groups__name=PROTECTED_HEALTH_INFORMATION_GROUP)
        else:
            via_users = CircusUser.objects.filter(user_type=settings.VIA_USER_TYPE)
        for via_user in via_users:
            assignee = encode_assignee(via_user, 'VIA')
            choices.append(assignee)

        return choices

    def save(self, *args, **kwargs):
        # get object_type and object_id values from combined generic_obj field
        assignee_string = self.cleaned_data['assignee']
        if assignee_string != u'type:0-id:0':
            assignee_type, assignee_id = decode_assignee(assignee_string)
        else:
            assignee_type = None
            assignee_id = None

        # add object_type and object_id
        self.cleaned_data['assignee_content_type'] = assignee_type
        self.cleaned_data['assignee_object_id'] = assignee_id
        self.instance.assignee_object_id = assignee_id
        self.instance.assignee_content_type = assignee_type
        # if not self.cleaned_data['service'].service_type.code in [TRANSLATION_EDIT_PROOF_SERVICE_TYPE, TRANSLATION_ONLY_SERVICE_TYPE]:
        if not self.cleaned_data['service'].service_type.code in [TRANSLATION_EDIT_PROOF_SERVICE_TYPE, TRANSLATION_ONLY_SERVICE_TYPE,
                                                                  LINGUISTIC_QA_SERVICE_TYPE, PROOFREADING_SERVICE_TYPE, MT_POST_EDIT_SERVICE_TYPE,
                                                                  GLOSSARY_DEVELOPMENT_SERVICE_TYPE, LINGUISTIC_TASK_SERVICE_TYPE]:
            self.instance.nontranslationtask.quantity = self.cleaned_data['quantity']
            self.instance.nontranslationtask.unit_cost = self.cleaned_data['unit_cost']
            self.instance.nontranslationtask.unit_price = self.cleaned_data['unit_price']
            self.instance.nontranslationtask.vendor_minimum = self.cleaned_data['vendor_minimum']
            self.instance.nontranslationtask.price_is_percentage = self.cleaned_data['price_is_percentage']
            self.instance.nontranslationtask.actual_hours = self.cleaned_data['actual_hours']
            self.instance.nontranslationtask.save()
            formula_id = self.instance.nontranslationtask.formula_id
            if formula_id and self.cleaned_data['formula']:
                self.instance.nontranslationtask.formula.percent_calculation = self.cleaned_data['formula']
                self.instance.nontranslationtask.formula.save()

        # TODO if vendor changed, we need to recalculate the pricing for the Task or set to 0 so Auto-set Costs and Prices can be re-run
        return super(TaskForm, self).save(*args, **kwargs)


class RatingForm(forms.Form):
    rating = forms.CharField(label="",widget=forms.NumberInput(attrs={'class':'rating' ,'data-max':'5','data-min':'1','data-icon-lib':'fa','data-active-icon':'fa-star','data-inactive-icon':'fa-star-o'}))