from collections import OrderedDict
from django.conf import settings

from django.utils.translation import ugettext_lazy as _
from shared.state_machine import State


QUEUED_STATUS = 'queued'  # Job pending (order has not been placed)
CREATED_STATUS = 'created'
QUOTED_STATUS = 'quoted'
STARTED_STATUS = 'started'
COMPLETED_STATUS = 'completed'
CLOSED_STATUS = 'closed'
CANCELED_STATUS = 'canceled'
INAPPROVAL_STATUS = 'inapproval' # jobs that are waiting to be approved by client owner

OVERDUE_STATUS = 'overdue'
DELIVERED_STATUS = 'delivered'
HOLD_STATUS = 'hold'

# dummy statuses, not actually stored on models
ALL_STATUS = 'all'
MYJOBS_STATUS = 'myjobs'
UPDATE_TM_STATUS = 'updatetm'
UNASSIGNED_STATUS = 'unassigned'
WARNING_STATUS = 'warning'

###################
MY_ESTIMATES_STATUS = 'myestimates'
UNASSIGNED_ESTIMATES_STATUS = 'unassignedestimates'
HOTLIST_STATUS = 'hotlist'

####################
# NORMALIZE STATUSES
####################
INESTIMATE_STATUS = 'inestimate'
ESTIMATED_STATUS = 'estimated'
ACTIVE_STATUS = 'active'
UNAPPROVED_PO = 'unapproved_pos'

STATUS_MAPPING = {
    ESTIMATED_STATUS: QUOTED_STATUS,
    ACTIVE_STATUS: STARTED_STATUS,
    INESTIMATE_STATUS: CREATED_STATUS,
}


def _normalize_project_status(status):
    if status in STATUS_MAPPING:
        return STATUS_MAPPING[status]
    return status


def _reverse_normalize_project_status(status):
    try:
        status = list(STATUS_MAPPING)[STATUS_MAPPING.values().index(status)]
    except:
        pass
    return status


def get_reversed_status(status):
    try:
        reversed_status = _reverse_normalize_project_status(status.get('url_status_parameter'))
    except:
        try:
            reversed_status = _reverse_normalize_project_status(status)
        except:
            reversed_status = status
    return reversed_status


VIA_STATUS_DETAIL = OrderedDict([
    (MYJOBS_STATUS, {
        'text': 'My Jobs',
        'icon': 'fa fa-heart',
        'url_status_parameter': 'myjobs'
    }),
    (QUEUED_STATUS, {
        'text': 'Queued',
        'icon': 'fa fa-plus-circle',
        'url_status_parameter': 'queued'
    }),
    (MY_ESTIMATES_STATUS, {
        'text': 'My Estimates',
        'icon': 'fa  fa-heartbeat',
        'url_status_parameter': 'myestimates'
    }),
    (HOTLIST_STATUS, {
        'text': 'HotList',
        'icon': 'fa fa-fire',
        'url_status_parameter': 'hotlist'
    }),
    (UNASSIGNED_ESTIMATES_STATUS, {
        'text': 'Unassigned',
        'icon': 'fa fa-circle-o',
        'url_status_parameter': 'unassignedestimates'
    }),
    (INESTIMATE_STATUS, {
        'text': 'In Estimate',
        'icon': 'fa fa-circle',
        'url_status_parameter': 'inestimate'
    }),
    (ESTIMATED_STATUS, {
        'text': 'Estimated',
        'icon': 'fa fa-check-circle',
        'url_status_parameter': 'estimated'
    }),
    (UNASSIGNED_STATUS, {
        'text': 'Unassigned',
        'icon': 'fa fa-square-o',
        'url_status_parameter': 'unassigned'
    }),
    (ACTIVE_STATUS, {
        'text': "Active",
        'icon': 'fa fa-check-square-o',
        'url_status_parameter': 'active'
    }),
    (HOLD_STATUS, {
        'text': 'Hold',
        'icon': 'fa fa-pause',
        'url_status_parameter': 'hold'
    }),
    (WARNING_STATUS, {
        'text': 'Warnings',
        'icon': 'fa fa-exclamation-triangle',
        'url_status_parameter': 'warning'
    }),
    (OVERDUE_STATUS, {
        'text': 'Overdue',
        'icon': 'fa fa-exclamation-circle',
        'url_status_parameter': 'overdue'
    }),
    (UNAPPROVED_PO, {
        'text': 'PO Approvals',
        'icon': 'fa fa-check-circle',
        'url_status_parameter': 'unapproved_pos'
    }),
    (DELIVERED_STATUS, {
        'text': 'Delivered',
        'icon': 'fa fa-square',
        'url_status_parameter': 'delivered'
    }),
    (COMPLETED_STATUS, {
        'text': 'Completed',
        'icon': 'fa fa-check-square',
        'url_status_parameter': 'completed'
    }),
    (UPDATE_TM_STATUS, {
        'text': 'TM',
        'icon': 'fa fa-language',
        'url_status_parameter': 'updatetm'
    }),
    (CANCELED_STATUS, {
        'text': 'Canceled',
        'icon': 'fa fa-trash-o',
        'url_status_parameter': 'canceled'
    }),
    (ALL_STATUS, {
        'text': 'All',
        'icon': 'fa fa-th',
        'url_status_parameter': 'all'
    }),
])

CLIENT_STATUS_DETAIL = OrderedDict([
    (MYJOBS_STATUS, {
        'text': 'My Jobs',
        'icon': 'fa fa-heart',
        'url_status_parameter': 'myjobs'
    }),
    (QUEUED_STATUS, {
        'text': 'Queued',
        'icon': 'fa fa-plus-circle',
        'url_status_parameter': 'queued'
    }),
    (INESTIMATE_STATUS, {
        'text': 'In Estimate',
        'icon': 'fa fa-circle',
        'url_status_parameter': 'inestimate'
    }),
    (ESTIMATED_STATUS, {
        'text': 'Estimated',
        'icon': 'fa fa-check-circle',
        'url_status_parameter': 'estimated'
    }),
    (ACTIVE_STATUS, {
        'text': "Active",
        'icon': 'fa fa-check-square-o',
        'url_status_parameter': 'active'
    }),
    (HOLD_STATUS, {
        'text': 'Hold',
        'icon': 'fa fa-pause',
        'url_status_parameter': 'hold'
    }),
    (OVERDUE_STATUS, {
        'text': 'Overdue',
        'icon': 'fa fa-exclamation-circle',
        'url_status_parameter': 'overdue'
    }),
    (DELIVERED_STATUS, {
        'text': 'Delivered',
        'icon': 'fa fa-square',
        'url_status_parameter': 'delivered'
    }),
    (COMPLETED_STATUS, {
        'text': 'Completed',
        'icon': 'fa fa-check-square',
        'url_status_parameter': 'completed'
    }),
    (CANCELED_STATUS, {
        'text': 'Canceled',
        'icon': 'fa fa-trash-o',
        'url_status_parameter': 'canceled'
    }),
    (INAPPROVAL_STATUS, {
        'text': 'In Approval',
        'icon': 'fa fa-thumbs-up',
        'url_status_parameter': 'inapproval'
    }),
    (ALL_STATUS, {
        'icon': 'fa fa-th',
        'text': 'All',
        'url_status_parameter': 'all'
    }),
])

PROJECT_QUEUED = State(QUEUED_STATUS, _('Queued'))
PROJECT_CREATED = State(CREATED_STATUS, _('In Estimate'))
PROJECT_QUOTED = State(QUOTED_STATUS, _('Estimated'))
PROJECT_STARTED = State(STARTED_STATUS, _('Active'))
PROJECT_COMPLETED = State(COMPLETED_STATUS, _('Delivered'))
PROJECT_CLOSED = State(CLOSED_STATUS, _('Closed'))
PROJECT_CANCELED = State(CANCELED_STATUS, _('Canceled'))
PROJECT_HOLD = State(HOLD_STATUS, _('Hold'))

PROJECT_QUEUED.add_transition(PROJECT_CREATED,
                              u'Request Estimate',
                              lambda p: p.can_be_manual_estimated(),
                              u'Manual Estimate requested')
PROJECT_QUEUED.add_transition(PROJECT_QUOTED,
                              u'Quote Complete',
                              lambda p: p.can_be_quote_completed(),
                              u'Analysis must exist for all locale files, valid Customer Pricing per Service and Approvals set (if > $10k).')
PROJECT_QUEUED.add_transition(PROJECT_CANCELED,
                              u'Cancel Job',
                              lambda p: p.can_be_canceled(),
                              u'Job can be canceled.')

PROJECT_QUEUED.add_action(u'Assign Team',
                          'assign_team',
                          lambda p, u: p.assign_team(u),
                          lambda p: p.always_show_action(),
                          u'')
PROJECT_QUEUED.add_action(u'Generate Kit Analysis',
                          'generate_loc_kit_analysis',
                          lambda p, u: p.generate_loc_kit_analysis(u),
                          lambda p: p.always_show_action(),
                          u'')
PROJECT_QUEUED.add_action(u'Re-Generate Tasks',
                          'generate_tasks',
                          lambda p, u: p.generate_tasks(u, False),
                          lambda p: p.always_show_action(),
                          u'')
PROJECT_QUEUED.add_action(u'Auto-assign Tasks',
                          'assign_tasks',
                          lambda p, u: p.assign_tasks(u),
                          lambda p: p.always_show_action(),
                          u'')

PROJECT_CREATED.add_transition(PROJECT_QUOTED,
                               'Quote Complete',
                               lambda p: p.can_be_quote_completed(),
                               u'Analysis must exist for all locale files, valid Customer Pricing per Service and Approvals set (if > $10k).')
PROJECT_CREATED.add_transition(PROJECT_HOLD,
                               u'Hold Job',
                               lambda p: p.can_be_hold(),
                               u'Job can be put on hold.')
PROJECT_CREATED.add_transition(PROJECT_CANCELED,
                               'Cancel Job',
                               lambda p: p.can_be_canceled(),
                               u'Job can be canceled.')

PROJECT_CREATED.add_action(u'Create Manual Estimate',
                           'create_jams_estimate',
                           lambda p, u: p.create_jams_estimate(u),
                           lambda p: p.can_create_jams_estimate(),
                           u'')
PROJECT_CREATED.add_action(u'Re-Generate Tasks',
                           'generate_tasks',
                           lambda p, u: p.generate_tasks(u, False),
                           lambda p: p.always_show_action(),
                           u'')
PROJECT_CREATED.add_action(u'Assign Tasks',
                           'assign_tasks',
                           lambda p, u: p.assign_tasks(u),
                           lambda p: p.always_show_action(),
                           u'')
PROJECT_CREATED.add_action(u'Set Costs and Prices',
                           'set_rates_and_prices',
                           lambda p, u: p.set_rates_and_prices(u),
                           lambda p: p.always_show_action(),
                           u'')
PROJECT_CREATED.add_action(u'Clear Analysis',
                           'clear_analysis',
                           lambda p, u: p.kit.clear_analysis(),
                           lambda p: p.always_show_action(),
                           u'')
PROJECT_CREATED.add_action(u'Create Loc Kit',
                           'pre_translate_and_prep_kit',
                           lambda p, u: p.pre_translate_and_prep_kit(u),
                           lambda p: p.kit.show_pre_translate_and_prep_kit_auto())
PROJECT_CREATED.add_action(u'Reschedule Due Dates',
                           'reschedule_due_dates',
                           lambda p, u: p.reschedule_due_dates(u),
                           lambda p: p.always_show_action(),
                           u'')
PROJECT_CREATED.add_action(u'Assign VIA Team',
                           'assign_team',
                           lambda p, u: p.assign_team(u),
                           lambda p: p.always_show_action(),
                           u'')


PROJECT_QUOTED.add_transition(PROJECT_CREATED,
                              u'Adjust Estimate',
                              lambda p: True)
PROJECT_QUOTED.add_transition(PROJECT_STARTED,
                              u'Start Job',
                              lambda p: p.tasks_are_priced(),
                              u'Analysis must exist for all locale files and valid Customer Pricing per Service.',
                              lambda p: p.start_project(p.client.manifest.auto_start_workflow, settings.VIA_JAMS_INTEGRATION))
PROJECT_QUOTED.add_transition(PROJECT_CANCELED,
                              u'Cancel Job',
                              lambda p: p.can_be_canceled(),
                              u'Jobs can be canceled.')

PROJECT_STARTED.add_transition(PROJECT_CREATED,
                               u'In Estimate Job',
                               lambda p: p.approved,
                               u'Jobs can be estimated.')
PROJECT_STARTED.add_transition(PROJECT_HOLD,
                               u'Hold Job',
                               lambda p: p.can_be_hold(),
                               u'job can only be put on hold.')
PROJECT_STARTED.add_transition(PROJECT_CANCELED,
                               u'Cancel Job',
                               lambda p: p.can_be_canceled(),
                               u'Jobs can be canceled.')
PROJECT_STARTED.add_transition(PROJECT_COMPLETED,
                               u'Complete Job',
                               lambda p: p.all_tasks_complete(),
                               u'All tasks must be completed.')

PROJECT_STARTED.add_action(u'Refresh Loc Kit',
                           'pre_translate_and_prep_kit',
                           lambda p, u: p.pre_translate_and_prep_kit(u),
                           lambda p: p.kit.show_pre_translate_and_prep_kit_auto())
PROJECT_STARTED.add_action(u'Copy Loc Kit',
                           'copy_localization_translation_kit_to_tasks',
                           lambda p, u: p.copy_localization_translation_kit_to_tasks(u),
                           lambda p: p.show_copy_loc_kit())
PROJECT_STARTED.add_action(u'Start Workflow',
                           'start_workflow',
                           lambda p, u: p.start_workflow(u),
                           lambda p: p.show_start_workflow(),
                           u'Workflow is not automatic, so please Start Workflow.')
PROJECT_STARTED.add_action(u'Reschedule Due Dates',
                           'reschedule_due_dates',
                           lambda p, u: p.reschedule_due_dates(u),
                           lambda p: p.show_reschedule_due_dates(),
                           u'')
PROJECT_STARTED.add_action(u'Pickup Post Process',
                           'pickup_post_process',
                           lambda p, u: p.pickup_post_process_tasks(u),
                           lambda p: p.show_pickup_post_process_tasks(),
                           u'Pickup unassigned Post Process Tasks')
PROJECT_STARTED.add_action(u'Pickup Final Approval',
                           'pickup_final_approval',
                           lambda p, u: p.pickup_final_approval_tasks(u),
                           lambda p: p.show_pickup_final_approval_tasks(),
                           u'Pickup unassigned Final Approval Tasks.')
PROJECT_STARTED.add_action(u'Completed Job Offline',
                           'set_job_status_completed_offline',
                           lambda p, u: p.set_job_status_completed_offline(u),
                           lambda p: p.show_set_job_status_completed_offline(),
                           u'Job was completed offline so close online.')


PROJECT_HOLD.add_transition(PROJECT_CREATED,
                            u'In Estimate Job',
                            lambda p: p.can_be_estimated(),
                            u'Jobs can be estimated.')
PROJECT_HOLD.add_transition(PROJECT_STARTED,
                            u'Activate Job',
                            lambda p: p.approved,
                            u'Jobs can be started.')
PROJECT_HOLD.add_transition(PROJECT_CANCELED,
                            u'Cancel Job',
                            lambda p: p.can_be_canceled(),
                            u'Job can be canceled.')

PROJECT_CANCELED.add_transition(PROJECT_CREATED,
                                u'In Estimate Job',
                                lambda p: p.can_be_estimated())
PROJECT_CANCELED.add_transition(PROJECT_CANCELED,
                                u'Cancel Again?',
                                lambda p: p.can_be_canceled(),
                                u'Job can be canceled.')

PROJECT_COMPLETED.add_transition(PROJECT_STARTED,
                                 u'Activate Job',
                                 lambda p: p.can_be_reactivated(),
                                 u'Jobs can be activated.')
PROJECT_COMPLETED.add_transition(PROJECT_CLOSED,
                                 u'Close Job',
                                 lambda p: p.is_invoiced(),
                                 u'All POs and invoices must be issued.')

PROJECT_STARTED.add_action(u'Approve all Task Hours',
                           'approve_all_task_hours',
                           lambda p, u: p.set_create_po_needed(True),
                           lambda p: p.is_delay_job_po(),
                           u'')

# invoicing probably calendar month
# report: on time delivery, late, etc

PROJECT_CLOSED.add_transition(PROJECT_COMPLETED,
                              u'Reopen Job',
                              lambda p: p.can_be_reopened(),
                              u'Jobs can be reopened.')


PROJECT_STATES = {state.name: state for state in
                  [
                      PROJECT_QUEUED, PROJECT_CREATED, PROJECT_QUOTED, PROJECT_STARTED, PROJECT_HOLD,
                      PROJECT_COMPLETED, PROJECT_CLOSED, PROJECT_CANCELED
                  ]
}

PROJECT_STATUS_CHOICES = [(state.name, state.label) for state in PROJECT_STATES.values()]  # NOQA

TASK_CREATED_STATUS = 'created'
TASK_ACTIVE_STATUS = 'active'
TASK_COMPLETED_STATUS = 'completed'
TASK_CANCELED_STATUS = 'canceled'

TASK_STATUS = (
    (TASK_CREATED_STATUS, 'Created'),
    (TASK_ACTIVE_STATUS, 'Active'),
    (TASK_COMPLETED_STATUS, 'Completed'),
    (TASK_CANCELED_STATUS, 'Canceled'),
)

PO_NEW_STATUS = 'new'
PO_OPEN_STATUS = 'open'
PO_CLOSED_STATUS = 'closed'
PO_CANCELED_STATUS = 'canceled'

PO_STATUS = (
    (PO_NEW_STATUS, 'New'),
    (PO_OPEN_STATUS, 'Open'),
    (PO_CLOSED_STATUS, 'Closed'),
    (PO_CANCELED_STATUS, 'Canceled'),
)
