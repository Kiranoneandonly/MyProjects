from django.conf.urls import url
import dwh_reports.views as v

urlpatterns = [

    url(r'^jobs_per_pm/?$', v.jobs_per_pm, name='jobs_per_pm'),
    url(r'^jobs_otd/?$', v.jobs_otd, name='jobs_otd'),
    url(r'^jobs_gross_margin_report/(?P<client_id>\d+)/?$', v.jobs_gross_margin_report, name='jobs_gross_margin_report'),
    url(r'^task_completion_velocity/?$', v.task_completion_velocity, name='task_completion_velocity_via'),
    url(r'^estimation_completion_velocity/?$', v.estimation_completion_velocity, name='estimation_completion_velocity'),
    url(r'^estimates_summary/?$', v.report_estimates_total, name='via_estimates_summary'),

]
