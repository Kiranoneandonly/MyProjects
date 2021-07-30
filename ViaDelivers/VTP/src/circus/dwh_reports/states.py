from collections import OrderedDict
from projects.states import CREATED_STATUS, QUOTED_STATUS, STARTED_STATUS, COMPLETED_STATUS, \
                            CANCELED_STATUS, ALL_STATUS, QUEUED_STATUS


def client_report_via_normalize_status(status):
    STATUS_MAPPING = {
        # CREATED_STATUS: QUEUED_STATUS
    }

    if status in STATUS_MAPPING:
        return STATUS_MAPPING[status]
    return status


CLIENT_REPORT_VIA_STATUS_DETAIL_VIA_PORTAL = OrderedDict([
    (QUOTED_STATUS, {
        'text': 'Estimated',
        'icon': 'fa fa-check-circle',
        'named_url_pattern': 'client_activity_report_view'
    }),
    (STARTED_STATUS, {
        'text': "Active",
        'icon': 'fa fa-check-square-o',
        'named_url_pattern': 'client_activity_report_view'
    }),
    (COMPLETED_STATUS, {
        'text': 'Completed',
        'icon': 'fa fa-check-square',
        'named_url_pattern': 'client_activity_report_view'
    }),
    (ALL_STATUS, {
        'icon': 'fa fa-th',
        'text': 'All',
        'named_url_pattern': 'client_activity_report_view'
    }),
])


CLIENT_REPORT_VIA_STATUS_DETAIL_CLIENT_PORTAL = OrderedDict([
    (QUOTED_STATUS, {
        'text': 'Estimated',
        'icon': 'fa fa-check-circle',
        'named_url_pattern': 'client_activity_report_view_client_portal'
    }),
    (STARTED_STATUS, {
        'text': "Active",
        'icon': 'fa fa-check-square-o',
        'named_url_pattern': 'client_activity_report_view_client_portal'
    }),
    (COMPLETED_STATUS, {
        'text': 'Completed',
        'icon': 'fa fa-check-square',
        'named_url_pattern': 'client_activity_report_view_client_portal'
    }),
    (ALL_STATUS, {
        'icon': 'fa fa-th',
        'text': 'All',
        'named_url_pattern': 'client_activity_report_view_client_portal'
    }),
])
