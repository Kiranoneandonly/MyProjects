import datetime
from django.db.models import Q
import re
from localization_kits.models import FileAsset, SOURCEFILE_ASSET


class HideSearchMixin(object):
    def get_context_data(self, **kwargs):
        # noinspection PyUnresolvedReferences
        context = super(HideSearchMixin, self).get_context_data(**kwargs)
        context['hide_search'] = True
        return context

job_number_re = re.compile(r'^\d{5,9}T\d\d$', re.IGNORECASE)
job_number_truncated_re = re.compile(r'^\d{5,9}$', re.IGNORECASE)


class ProjectSearchMixin(object):
    def get_matches(self, projects, search_query):
        # short circuit for the common case where people are looking up a
        # specific job by its job number.
        if job_number_re.match(search_query):
            job_number = search_query.upper()
        elif job_number_truncated_re.match(search_query):
            job_number = '%sT%s' % (search_query,
                                    datetime.date.today().strftime('%y'))
        else:
            job_number = None

        if job_number:
            this_job = projects.filter(job_number=job_number)
            if len(this_job) == 1:
                return this_job

        matching_source_files = FileAsset.objects.filter(
            Q(orig_name__icontains=search_query) |
            # match in Prepared File Name
            Q(prepared_name__icontains=search_query),
            asset_type=SOURCEFILE_ASSET
        )

        job_match_criteria = (
            Q(job_number__icontains=search_query) |
            Q(payment_details__ca_invoice_number__icontains=search_query) |
            Q(client__name__icontains=search_query) |
            Q(kit__files__in=matching_source_files) |
            Q(client_poc__email__icontains=search_query)
        )

        matches = projects.filter(job_match_criteria).distinct()

        return matches


class TaskSearchMixin(object):
    def get_matches(self, tasks, search_query):
        search_query = search_query.lower()

        task_match_criteria = (
            # match in job number
            Q(project__job_number__icontains=search_query) |
            # match in source file names orig_name
            Q(project__kit__files__orig_name__icontains=search_query, project__kit__files__asset_type=SOURCEFILE_ASSET) |
            # match in source file names prepared_name
            Q(project__kit__files__prepared_name__icontains=search_query, project__kit__files__asset_type=SOURCEFILE_ASSET) |
            # match in vendor task po number
            Q(po__po_number__icontains=search_query)
        )

        # return list(tasks.filter(task_match_criteria).distinct())
        matches = tasks.filter(task_match_criteria).distinct()

        return matches