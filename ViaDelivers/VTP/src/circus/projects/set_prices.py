from decimal import Decimal

from django.contrib.messages import ERROR, WARNING, SUCCESS

from prices.models import VendorTranslationRate, VendorNonTranslationRate, ClientTranslationPrice, \
    ClientNonTranslationPrice
from projects.states import CREATED_STATUS, QUEUED_STATUS, STARTED_STATUS


def set_rate(task):
    """ set the rate for a task. returns true if the task is updated, otherwise false """
    task.reset_task_vendor_costs()

    if task.assigned_to:

        rate = None

        if task.is_translation():
            rate = VendorTranslationRate.objects.for_task(task)
        else:
            rate = VendorNonTranslationRate.objects.for_task(task)

            if rate is None:
                return task.nontranslationtask.set_from_vendor_rate(rate)

        if rate:
            return task.set_from_vendor_rate(rate)
        else:
            return False
    else:
        if not task.is_translation():
            return task.nontranslationtask.set_from_vendor_rate(None)
        else:
            return False


def set_price(task):
    if task.is_translation():
        price = ClientTranslationPrice.objects.for_task(task)
    else:
        from tasks.make_tasks import _get_client_discount, _get_project_services_global
        if task.is_client_discount():
            cd = _get_client_discount(task.project.client.id, task.project.created)

            save_cd = False
            psg, psg_valid = _get_project_services_global(task.project, task.service.service_type)
            if psg_valid:
                discount_price = psg.quantity
                save_cd = True
            elif cd:
                discount_price = cd.values_list('discount', flat=True)[0]
                save_cd = True

            if save_cd:
                task.nontranslationtask.unit_price = discount_price / Decimal('100.0')
                task.nontranslationtask.price_is_percentage = True
                task.nontranslationtask.save()

        price = ClientNonTranslationPrice.objects.for_task(task)

    return task.set_from_client_price(price)


def set_task_set_rates_and_prices(task):
    set_rate(task)
    set_price(task)
    message = u"Task Costs and Prices updated"
    return SUCCESS, message


def set_project_rates_and_prices(project):
    """
    :type project: projects.models.Project
    """
    try:
        project.clean_pricing()
        rates = set_project_rates(project)
        prices = set_project_prices(project)
        project.quote_summary_recalculate_all()

        if any(ERROR == code for code in rates) or any(ERROR == code for code in prices):
            return ERROR, "Problem setting Job Costs and Prices"
        else:
            return SUCCESS, "Job Costs and Prices set"
    except:
        return ERROR, "Problem setting Job Costs and Prices"


def set_project_prices(project):
    """
    :type project: projects.models.Project
    """

    if project.status not in [QUEUED_STATUS, CREATED_STATUS, STARTED_STATUS]:
        return ERROR, u'Cannot generate job price when in state {0}'.format(project.machine.state.label)

    if not project.pricing_basis:
        project.pricing_basis = project.client.manifest.pricing_basis
        project.save()

    if not project.express_factor == project.client.manifest.express_factor:
        project.express_factor = project.client.manifest.express_factor
        project.save()

    tasks = project.task_set.filter(billable=True)
    if not tasks:
        return ERROR, u"No tasks in project"

    new_prices = 0
    for task in tasks:
        if set_price(task):
            new_prices += 1
    message = u"{0} client rates assigned".format(new_prices)
    if new_prices:
        return SUCCESS, message
    return WARNING, message


def set_project_rates(project):
    """
    :type project: projects.models.Project
    """

    tasks = list(project.task_set.filter(billable=True))
    if not tasks:
        return ERROR, u"No tasks in project"

    new_rates = 0
    for task in tasks:
        if set_rate(task):
            new_rates += 1
    message = u"{0} vendor rates assigned".format(new_rates)
    if new_rates:
        return SUCCESS, message
    return WARNING, message
