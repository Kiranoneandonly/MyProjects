# -*- coding: utf-8 -*-

DEPARTMENT_USER_GROUP = 'Department Users'
CLIENT_CONTRIBUTOR_GROUP = 'Client contributors'
CLIENT_APPROVED_USER_GROUP = 'Client Approved Users'
CLIENT_MANAGER_GROUP = 'Client Managers'
DEPARTMENT_ADMINISTRATOR_GROUP = 'Department Administrators'
CLIENT_PROJECT_APPROVER_GROUP = 'Client Project Approvers'
CLIENT_NOTIFICATION_GROUP = 'Client Notification Users'
CLIENT_DEFAULT_LEVEL_GROUP = 'Client Users default level'
CLIENT_ORGANIZATION_ADMINISTRATOR_GROUP = 'Organization Administrator'
PROTECTED_HEALTH_INFORMATION_GROUP = 'Protected Health Information Users'


VIEW_COLLEAGUE_DATA_CODENAME = 'view_colleague_data'
BILL_TO_COMPANY_CODENAME = 'bill_to_company'
CLIENT_MANAGER_CODENAME = 'client_manager'
CLIENT_USER_CODENAME = 'view_project'
CLIENT_CONTRIBUTOR_CODENAME = 'add_project'
APPROVE_PROJECT_CODENAME = 'approve_project'
REPORTING_DIRECT_REPORTS_CODENAME = 'reporting_direct_reports'
VIEW_CHILD_COMPANY_JOBS_CODENAME = 'view_child_company_jobs'
APPROVE_ACCESS_REQUESTED_JOBS_CODENAME = 'approve_access_requested_jobs'
CLIENT_ADMIN_ACCESS_CHILD_DEPT_CODENAME = 'client_admin_access_child_departments'
MGR_VIEW_TEAM_JOBS_CODENAME = 'manager_can_view_teams_jobs'
SECURE_JOB_PERMISSION = 'secure_job_permission'
MANAGE_USERS_GROUPS_MENU_PERMISSION = 'manage_users_groups_permission'

VIEW_COLLEAGUE_DATA_PERMISSION = 'clients.{0}'.format(VIEW_COLLEAGUE_DATA_CODENAME)
BILL_TO_COMPANY_PERMISSION = 'clients.{0}'.format(BILL_TO_COMPANY_CODENAME)
APPROVE_PROJECT_PERMISSION = 'projects.{0}'.format(APPROVE_PROJECT_CODENAME)


CLIENT_CONTRIBUTOR_PERMISSIONS = [
    {
        'codename': CLIENT_CONTRIBUTOR_CODENAME,
        'app_label': 'projects',
        'model': 'project',
    },
]

CLIENT_USER_PERMISSIONS = [
    {
        'codename': CLIENT_USER_CODENAME,
        'app_label': 'projects',
        'model': 'project',
    },
]

APPROVED_USER_PERMISSIONS = [
    {
        'codename': VIEW_COLLEAGUE_DATA_CODENAME,
        'app_label': 'clients',
        'model': 'client',
    },
    {
        'codename': BILL_TO_COMPANY_CODENAME,
        'app_label': 'clients',
        'model': 'client',
    },
]

CLIENT_PROJECT_APPROVER_PERMISSIONS = [
    {
        'codename': APPROVE_PROJECT_CODENAME,
        'app_label': 'projects',
        'model': 'project',
    },
]
CLIENT_MANAGER_PERMISSIONS = [
    {
        'codename': CLIENT_MANAGER_CODENAME,
        'app_label': 'clients',
        'model': 'client',
    },
    {
        'codename': REPORTING_DIRECT_REPORTS_CODENAME,
        'app_label': 'dwh_reports',
        'model': 'clientmanager',
    },
    {
        'codename': VIEW_CHILD_COMPANY_JOBS_CODENAME,
        'app_label': 'projects',
        'model': 'project',
    },
    {
        'codename': APPROVE_ACCESS_REQUESTED_JOBS_CODENAME,
        'app_label': 'clients',
        'model': 'client',
    },
]

CLIENT_MANAGER_TEAM_PERMISSIONS = [
    {
        'codename': MGR_VIEW_TEAM_JOBS_CODENAME,
        'app_label': 'projects',
        'model': 'project',
    },
]

CLIENT_ADMIN_PERMISSIONS = [
    {
        'codename': 'change_circususer',
        'app_label': 'accounts',
        'model': 'circususer',
    },
    {
        'codename': 'change_account',
        'app_label': 'people',
        'model': 'account',
    },
]

CLIENT_ORGANIZATION_ADMINISTRATOR_PERMISSIONS = [
    {
        'codename': CLIENT_USER_CODENAME,
        'app_label': 'projects',
        'model': 'project',
    },
    {
        'codename': VIEW_COLLEAGUE_DATA_CODENAME,
        'app_label': 'clients',
        'model': 'client',
    },
    {
        'codename': BILL_TO_COMPANY_CODENAME,
        'app_label': 'clients',
        'model': 'client',
    },
    {
        'codename': APPROVE_PROJECT_CODENAME,
        'app_label': 'projects',
        'model': 'project',
    },
    {
        'codename': CLIENT_MANAGER_CODENAME,
        'app_label': 'clients',
        'model': 'client',
    },
    {
        'codename': REPORTING_DIRECT_REPORTS_CODENAME,
        'app_label': 'dwh_reports',
        'model': 'clientmanager',
    },
    {
        'codename': VIEW_CHILD_COMPANY_JOBS_CODENAME,
        'app_label': 'projects',
        'model': 'project',
    },
    {
        'codename': APPROVE_ACCESS_REQUESTED_JOBS_CODENAME,
        'app_label': 'clients',
        'model': 'client',
    },
    {
        'codename': MGR_VIEW_TEAM_JOBS_CODENAME,
        'app_label': 'projects',
        'model': 'project',
    },
    {
        'codename': CLIENT_ADMIN_ACCESS_CHILD_DEPT_CODENAME,
        'app_label': 'clients',
        'model': 'client',
    },
    {
        'codename': 'add_clientmanager',
        'app_label': 'dwh_reports',
        'model': 'clientmanager',
    },
    {
        'codename': 'change_clientmanager',
        'app_label': 'dwh_reports',
        'model': 'clientmanager',
    },
    {
        'codename': 'delete_clientmanager',
        'app_label': 'dwh_reports',
        'model': 'clientmanager',
    },
    {
        'codename': MANAGE_USERS_GROUPS_MENU_PERMISSION,
        'app_label': 'clients',
        'model': 'client',
    },

]
