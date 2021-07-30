#!/usr/bin/python
# -*- coding: utf-8 -*-
import logging
from django.core.management.base import BaseCommand

import datetime
from decimal import *
import math
from django.db.models import Q
from dwh_reports.management.commands.populate_clientsreporting import populate_clientreporting
from dwh_reports.management.commands.populate_eqdreporting import populate_eqdreporting
from dwh_reports.management.commands.populate_taskrating import populate_taskrating
from dwh_reports.management.commands.populate_vendorsreporting import populate_vendorreporting
from dwh_reports.management.commands.populate_viareporting import populate_viareporting
from dwh_reports.management.commands.populate_clientreportsaccess import populate_clientreportaccess
from dwh_reports.models import TasksReporting, ClientsReporting, ProjectsReporting, RefreshTracking, ClientManager
from projects.models import Project
from projects.states import QUEUED_STATUS, CANCELED_STATUS
from shared.utils import remove_html_tags

logger = logging.getLogger('circus.' + __name__)


def populate_dwh_reports_data():
    try:
        logger.info(u'populate_dwh_reports_data started')

        # make sure we have all the latest users added to the system
        populate_viareporting()
        populate_vendorreporting()
        populate_clientreporting()
        populate_clientreportaccess()

        last_modified = None
        refresh_track_obj = RefreshTracking.objects.all()
        if refresh_track_obj:
            last_modified = refresh_track_obj.order_by("-pk")[0].last_refreshed_timestamp
            report_filter = ~Q(status=QUEUED_STATUS)
        else:
            report_filter = ~Q(status__in=[QUEUED_STATUS, CANCELED_STATUS])

        if last_modified:
            report_filter &= Q(modified__gte=last_modified)
            # Filtering the modified tasks
            report_filter |= Q(task__modified__gte=last_modified)

        # refresh EQD's
        populate_eqdreporting(last_modified)
        populate_taskrating(last_modified)

        projects = Project.objects.filter(report_filter).distinct().select_related()

        last_refreshed_timestamp_track = datetime.datetime.now()

        projects_count = projects.count()
        # for project in projects:
        for indexp, project in enumerate(projects, start=1):
            print(indexp, projects_count)

            logger.info(u'populate_dwh_reports_data : project : {0}'.format(project))

            if project.is_canceled_status():
                # Deleting the projects and their tasks whose status is canceled after they are loaded
                ProjectsReporting.objects.filter(pk=project.id).delete()
                TasksReporting.objects.filter(project_id=project.id).delete()
                continue
            else:
                gross_margin = None

                pricequote = project.project_pricequote()
                if pricequote:
                    gross_margin = pricequote.express_gm if project.is_express_speed() else pricequote.gm
                    if gross_margin and not math.isnan(gross_margin):
                        gross_margin += gross_margin * Decimal(100)
                    else:
                        gross_margin = Decimal(0)

                due = project.due
                delivery = project.delivered

                otd = None
                if delivery is not None and due is not None:
                    if due > delivery:
                        otd = 'Yes'
                    else:
                        otd = 'No'
                on_time_delivery = otd

                clients_reporting, created = ClientsReporting.objects.get_or_create(
                    client_id=project.client_id
                )
                clients_reporting.name = project.client.name
                clients_reporting.parent_id = project.client.parent_id
                clients_reporting.account_type = project.client.account_type_id
                clients_reporting.save()

                client_managers, created = ClientManager.objects.get_or_create(
                    id=project.client_poc_id
                )
                client_managers.department = project.client_poc.account.name
                client_managers.account_id = project.client_id
                client_managers.user_type = project.client_poc.user_type
                client_managers.first_name = project.client_poc.first_name
                client_managers.last_name = project.client_poc.last_name
                client_managers.email = project.client_poc.email
                client_managers.reports_to_id = project.client_poc.reports_to_id
                client_managers.save()

                # Inserting new projects or updating existing projects
                projects_reporting = ProjectsReporting(
                    project_id=project.id,
                    customer=clients_reporting,
                    name=project.name,
                    price=project.price(),
                    payment_method=project.payment_details.get_payment_method_display(),
                    gross_margin=gross_margin,
                    on_time_delivery=on_time_delivery,
                    project_status=project.status,
                    approved=project.approved,
                    source_locale=project.source_locale.description,
                    client_po=project.payment_details.ca_invoice_number,
                    job_number=project.job_number,
                    client_poc_id=project.client_poc_id,
                    account_executive=project.account_executive.first_name + ' ' + project.account_executive.last_name if project.account_executive is not None else '',
                    project_manager_id=project.project_manager_id,
                    project_manager=project.project_manager.first_name + ' ' + project.project_manager.last_name if project.project_manager is not None else '',
                    estimator_id=project.estimator_id,
                    estimator=project.estimator.first_name + ' ' + project.estimator.last_name if project.estimator is not None else '',
                    industry=project.industry.description if project.industry is not None else '',
                    start_date=project.started_timestamp,
                    due_date=project.due,
                    completed=project.completed,
                    delivered_date=project.delivered,
                    quoted=project.quoted,
                    priority=project.get_project_speed_display(),
                    estimate_type=project.get_estimate_type_display(),
                    instructions=remove_html_tags(project.instructions) if project.instructions is not None else '',
                    instructions_via=remove_html_tags(project.instructions_via) if project.instructions_via is not None else '',
                    instructions_vendor=remove_html_tags(project.instructions_vendor) if project.instructions_vendor is not None else '',
                    created=project.created,
                    modified=project.modified,
                    project_reference_name=project.project_reference_name,
                    is_secure_job=project.is_secure_job,
                )
                projects_reporting.save()
                logger.info(u'populate_dwh_reports_data : projects_reporting : {0}'.format(projects_reporting))

                logger.info(u'populate_dwh_reports_data : TasksReporting')
                # since we are updating project, remove all the current tasks and rebuild
                TasksReporting.objects.filter(project=projects_reporting).delete()

                tasks = project.billable_tasks()
                tasks_count = tasks.count()
                # for task in tasks:
                for indext, task in enumerate(tasks, start=1):
                    print(indext, tasks_count)

                    task_quotes = None
                    item_price = None
                    task_word_count = None
                    task_total_price = None

                    task_is_minimum = task.is_minimum_client() if task.is_translation() else None
                    if task_is_minimum:
                        logger.info(u'populate_dwh_reports_data : task_is_minimum')
                        task_quote = task.get_taskquote()
                        task_word_count = task_quote.wordcount
                        task_total_price = task_quote.express_net_price if project.is_express_speed() else task_quote.net_price

                    task_asset_quotes = task.get_taskassetquotes()
                    task_asset_quotes_count = task_asset_quotes.count()
                    # for task_asset_quote in task_asset_quotes:
                    for indextaq, task_asset_quote in enumerate(task_asset_quotes, start=1):
                        print(indextaq, task_asset_quotes_count)

                        if task_is_minimum:
                            if task_asset_quote.asset_is_minimum_price:
                                # do not track the Minimum Fee here as it will be added to the full Task Asset Quote
                                continue
                            else:
                                logger.info(u'populate_dwh_reports_data : task_asset_quote : calc asset_is_minimum_price')

                                task_asset_quote_words = task_asset_quote.asset_wordcount
                                target_task_wc_percent = Decimal(task_asset_quote_words) / Decimal(task_word_count) if Decimal(task_word_count) > 0 else Decimal(0)
                                target_task_price = target_task_wc_percent * Decimal(task_total_price)
                                item_price = target_task_price
                        else:
                            logger.info(u'populate_dwh_reports_data : task_asset_quote : asset price')
                            item_price = task_asset_quote.asset_express_net_price if project.is_express_speed() else task_asset_quote.asset_net_price

                        memory_bank_discount = task_asset_quote.asset_express_mbd if project.is_express_speed() else task_asset_quote.asset_mbd
                        memory_bank_discount = memory_bank_discount * Decimal(100) if memory_bank_discount and not math.isnan(memory_bank_discount) else Decimal(0)
                        gross_margin = task_asset_quote.asset_express_gm if project.is_express_speed() else task_asset_quote.asset_gm
                        source_file = task_asset_quote.asset.orig_name if task_asset_quote.asset else ''

                        tr_keywords = {
                            'project': projects_reporting,
                            'task_id': task.id,
                            'target_id': task_asset_quote.target.id,
                            'target': task_asset_quote.target.description,
                            'source_file': source_file,
                            'status': task.status,
                            'assignee_object_id': task.assignee_object_id,
                            'memory_bank_discount': round(memory_bank_discount, 1) if memory_bank_discount else Decimal(0),
                            'gross_margin': round(gross_margin, 1) if gross_margin else Decimal(0),
                            'price': item_price if item_price else Decimal(0),
                            'service_id': task.service.service_type.id,
                            'service_code': task.service.service_type.code,
                            'service_type': task.service.service_type.description,
                            'word_count': task_asset_quote.asset_wordcount,
                            'due': task.due,
                            'started': task.started_timestamp,
                            'completed': task.completed_timestamp,
                            'accepted': task.accepted_timestamp,
                            'created': task.created,
                            'modified': task.modified
                        }
                        tr = create_tasksreporting(**tr_keywords)
                    else:
                        logger.info(u'populate_dwh_reports_data : No task_asset_quote!!!')
                else:
                    logger.info(u'populate_dwh_reports_data : No billable_tasks!!!')
        else:
            logger.info(u'populate_dwh_reports_data : No projects!!!')

        refresh_table = RefreshTracking(
            last_refreshed_timestamp=last_refreshed_timestamp_track
        )
        refresh_table.save()

        logger.info(u'populate_dwh_reports_data completed')

    except Exception, exc:
        import pprint
        msg = [
            u'Exception:',
            pprint.pformat(exc),
        ]
        logger.error(msg)
        raise


def create_tasksreporting(**kwargs):
    try:
        task_reporting, created = TasksReporting.objects.get_or_create(project=kwargs['project'],
                                                                       task_id=kwargs['task_id'],
                                                                       target_id=kwargs['target_id'],
                                                                       source_file=kwargs['source_file']
                                                                       )
        task_reporting.status = kwargs['status']
        task_reporting.assignee_object_id = kwargs['assignee_object_id']
        task_reporting.memory_bank_discount = kwargs['memory_bank_discount']
        task_reporting.gross_margin = kwargs['gross_margin']
        task_reporting.price = kwargs['price']
        task_reporting.service_id = kwargs['service_id']
        task_reporting.service_code = kwargs['service_code']
        task_reporting.service_type = kwargs['service_type']
        task_reporting.target = kwargs['target']
        task_reporting.word_count = kwargs['word_count']
        task_reporting.due = kwargs['due']
        task_reporting.started = kwargs['started']
        task_reporting.completed = kwargs['completed']
        task_reporting.accepted = kwargs['accepted']
        task_reporting.created = kwargs['created']
        task_reporting.modified = kwargs['modified']
        task_reporting.save()
        logger.info(u'populate_dwh_reports_data : TasksReporting : {0}'.format(task_reporting))
        return True
    except Exception, exc:
        import pprint
        msg = [
            u'Exception create_tasksreporting:',
            pprint.pformat(exc),
        ]
        logger.error(msg)
        raise


class Command(BaseCommand):
    args = ''
    help = 'Scheduler to sync VTP Reporting Data Warehouse.'

    def handle(self, *args, **options):
        try:
            logger.info("refresh_dwh_reports started")
            populate_dwh_reports_data()
            logger.info("All done!")
        except Exception:
            # unlike django request handling, management commands don't have
            # any top-level exception logger. add one here as this is run
            # unattended by heroku scheduler.
            logger.error("error in refresh_dwh_reports", exc_info=True)
            raise
