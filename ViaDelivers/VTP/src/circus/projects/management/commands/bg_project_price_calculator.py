# -*- coding: utf-8 -*-
import logging
from django.core.management.base import BaseCommand
from projects.models import Project

logger = logging.getLogger('circus.' + __name__)


def run_bg_project_price_calculator(job_number=None):
    logger.info(u'run_bg_project_price_calculator - Started - Calculate the Price of Estimates in the background')
    projects = Project.objects.get_inestimate_projects()

    if job_number:
        logger.info(u'Job: {0}'.format(job_number))
        projects = projects.filter(job_number=job_number)

    for project in projects:
        logger.info(u'Project: {0}!'.format(project.job_number))
        if not project.has_price():
            logger.info(u'No project price...')
            logger.info(u'No project price, so redo assign_project_tasks().')
            project.assign_tasks()
            logger.info(u'No project price, so redo quote().')
            project.quote()
            logger.info(u'Project price: {0}!'.format(project.price()))
    logger.info(u'run_bg_project_price_calculator - All Done')


class Command(BaseCommand):
    args = ''
    help = "Calculate the Price of Estimates in the background"

    def handle(self, *args, **options):

        job_number = None

        if args.__len__() == 1:
            job_number = args[0]

        try:
            run_bg_project_price_calculator(job_number)
        except Exception:
            # unlike django request handling, management commands don't have
            # any top-level exception logger. add one here as this is run
            # unattended by heroku scheduler.
            logger.error("error in run_bg_project_price_calculator", exc_info=True)
            raise