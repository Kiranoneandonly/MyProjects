from collections import OrderedDict
from django.utils.translation import ugettext_lazy as _

OVERDUE_STATUS = 'overdue'
IMPORTANT_STATUS = 'important'
WARNING_STATUS = 'warning'
INFO_STATUS = 'info'
COMPLETED_STATUS = 'completed'

TASK_STATUS_UNASSIGNED = 'unassigned'
TASK_STATUS_PENDING = 'pending'
TASK_STATUS_ACTIVE = 'active'
TASK_STATUS_UPCOMING = 'upcoming'
TASK_STATUS_OVERDUE = 'overdue'
TASK_STATUS_FINAL_APPROVAL = 'final_approval'
TASK_STATUS_COMPLETE = 'complete'
TASK_STATUS_UNRATED = 'unrated'
TASK_STATUS_POSTPROCESS = 'post_process'
TASK_STATUS_UNAPPROVED = 'unapproved_po'

VIA_STATUS_DETAILS = OrderedDict((
    (TASK_STATUS_UNASSIGNED, {
        'description': 'Waiting for You to be assigned',
        'name': 'Unassigned',
        'icon': 'fa fa-bell-slash-o'
    }),
    (TASK_STATUS_PENDING, {
        'description': 'Waiting for You to Accept',
        'name': 'Pending',
        'icon': 'fa fa-bell'
    }),
    (TASK_STATUS_ACTIVE, {
        'description': 'Ready for Translation and Localization',
        'name': 'Active',
        'icon': 'fa fa-bolt'
    }),
    (TASK_STATUS_POSTPROCESS, {
        'description': 'Ready for Manual process of Job Files',
        'name': 'Post Process',
        'icon': 'fa fa-file-o'
    }),
    (TASK_STATUS_UPCOMING, {
        'description': 'Waiting on Other Work to Begin Task',
        'name': 'Upcoming',
        'icon': 'fa fa-clock-o'
    }),
    (TASK_STATUS_OVERDUE, {
        'description': 'Tasks Past Due',
        'name': 'Overdue',
        'icon': 'fa fa-frown-o'
    }),
    (TASK_STATUS_FINAL_APPROVAL, {
        'description': 'Tasks ready for Delivery Approval',
        'name': 'Final Approval',
        'icon': 'fa fa-check-square'
    }),
    (TASK_STATUS_COMPLETE, {
        'description': 'Work Delivered to VIA',
        'name': 'Completed',
        'icon': 'fa fa-flag-checkered'
    }),
    (TASK_STATUS_UNRATED, {
        'description': 'Work Delivered to VIA but not rated',
        'name': 'Unrated',
        'icon': 'fa fa-star-o'
    }),
    (TASK_STATUS_UNAPPROVED, {
        'description': 'Unapproved Po',
        'name': 'Unapproved Po',
        'icon': 'fa fa-star-o'
    })
))

temp = OrderedDict(VIA_STATUS_DETAILS)
for _ in [TASK_STATUS_UNASSIGNED, TASK_STATUS_OVERDUE, TASK_STATUS_FINAL_APPROVAL, TASK_STATUS_UNRATED, TASK_STATUS_POSTPROCESS]:
    del temp[_]

VENDOR_STATUS_DETAILS = temp

