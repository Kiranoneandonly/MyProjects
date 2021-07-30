from django.contrib.messages import ERROR, WARNING, SUCCESS
from preferred_vendors.models import PreferredVendor
from services.managers import THIRD_PARTY_REVIEW_SERVICE_TYPE, TRANSLATION_EDIT_PROOF_SERVICE_TYPE
from services.models import ServiceType


def assign_project_tasks(project):
    try:
        if not project.is_inestimate_status():
            return ERROR, u'Cannot assign job tasks when in state {0}'.format(project.machine.state.label)

        new_assignments = 0

        for task in project.task_set.all():
            task.assigned_to = None
            top_vendor = PreferredVendor.objects.top_vendor(project.client.manifest.vertical,
                                                            project.client,
                                                            task.service.source,
                                                            task.service.target,
                                                            task.service.service_type,
                                                            project.is_phi_secure_client_job()
                                                            )

            if top_vendor:
                task.assigned_to = top_vendor.vendor
                task.reset_task_vendor_costs()
                new_assignments += 1

            task.save()

        # -----------------
        # review tasks : assign to TEP preferred vendor is not assigned
        tep_service_type = ServiceType.objects.get(code=TRANSLATION_EDIT_PROOF_SERVICE_TYPE)
        review_service_type = ServiceType.objects.get(code=THIRD_PARTY_REVIEW_SERVICE_TYPE)
        for review_task in project.task_set.filter(service__service_type=review_service_type):
            if not review_task.assigned_to:
                review_vendor = PreferredVendor.objects.top_vendor(project.client.manifest.vertical,
                                                                   project.client,
                                                                   review_task.service.source,
                                                                   review_task.service.target,
                                                                   tep_service_type,
                                                                   project.is_phi_secure_client_job()
                                                                   )
                if review_vendor:
                    new_assignments += 1
                    review_task.assigned_to = review_vendor.vendor
                    review_task.nontranslationtask.unit_cost = None
                    review_task.nontranslationtask.vendor_minimum = None
                    review_task.nontranslationtask.save()
                    review_task.save()

        # reset cost and pricing
        project.set_rates_and_prices()

        message = u"{0} additional vendors assigned (using preferred vendor lists)".format(new_assignments)
        if new_assignments:
            return SUCCESS, message
        return WARNING, message
    except:
        return ERROR, "Errors occurred during assignments"
