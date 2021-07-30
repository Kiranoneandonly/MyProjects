from __future__ import unicode_literals
import logging

import after_response
from django.conf import settings
from django.core.urlresolvers import reverse
from django.utils.translation import ugettext as _

from django.core.mail import EmailMultiAlternatives, EmailMessage, mail_admins
from django.template.loader import get_template
from django.template import Context, TemplateDoesNotExist
from accounts.models import CircusUser
from clients.models import ClientTeamRole, AE_ROLE
from .models import NotificationMute
from people.models import Account
from shared.group_permissions import DEPARTMENT_ADMINISTRATOR_GROUP
from vendors.models import Vendor

logger = logging.getLogger('circus.' + __name__)


@after_response.enable
def send_email(subject, from_email, to_list, template_name, context, cc=None, bcc=None):
    """
    Send email, automatically creating a multi alternative message if an html version of the template exists.
    """
    bcc = list(bcc) if (bcc is not None) else []

    try:

        plaintext = get_template('{0}.txt'.format(template_name))

        try:
            html = get_template('{0}.html'.format(template_name))
        except TemplateDoesNotExist:
            html = None

        context.update({'via_logo_image_url': settings.VIA_LOGO_IMAGE_URL})

        d = Context(context)
        text_content = plaintext.render(d)

        #bcc admins
        bcc.extend(a[1] for a in settings.ADMINS)

        if html:
            html_content = html.render(d)
            msg = EmailMultiAlternatives(subject=subject, body=text_content, from_email=from_email, to=to_list, cc=cc, bcc=bcc)
            msg.attach_alternative(html_content, "text/html")
        else:
            msg = EmailMessage(subject=subject, body=text_content, from_email=from_email, to=to_list, cc=cc, bcc=bcc)

        msg.send()
    except:
        import traceback
        tb = traceback.format_exc()  # NOQA
        mail_admins('[send_email]: notification failed',
                    'Template = {0}. Subject = {1}. Error = {2}.'.format(template_name, subject, tb))


def get_notify_client_email_subject(project=None, subject=None):
    subject_line = "{0} : {1}".format(settings.APP_SLUG_INSTANCE, subject)
    project_reference_name = purchase_order_number = None

    if project:
        if project.payment_details.ca_invoice_number:
            purchase_order_number = project.payment_details.ca_invoice_number[0:50]

        if project.project_reference_name:
            project_reference_name = project.project_reference_name[0:25]

        subject_line = "{0} {1}: {2}".format(settings.APP_SLUG_INSTANCE, project.job_number, subject)

        if purchase_order_number and project_reference_name:
            subject_line = "{0} {1} ({2} | {3}): {4}".format(settings.APP_SLUG_INSTANCE,
                                                             project.job_number,
                                                             purchase_order_number,
                                                             project_reference_name,
                                                             subject)
        elif purchase_order_number:
            subject_line = "{0} {1} ({2}): {3}".format(settings.APP_SLUG_INSTANCE,
                                                       project.job_number,
                                                       purchase_order_number,
                                                       subject)
        elif project_reference_name:
            subject_line = "{0} {1} ({2}): {3}".format(settings.APP_SLUG_INSTANCE,
                                                       project.job_number,
                                                       project_reference_name,
                                                       subject)
    return subject_line


def get_notify_email_subject(project=None, subject=None):
    if project:
        return "{0} {1}: {2}".format(settings.APP_SLUG_INSTANCE, project.job_number, subject)
    return "{0} : {1}".format(settings.APP_SLUG_INSTANCE, subject)


def notify_pm_on_task(task, pm_message):
    if NotificationMute.objects.project_muted(task.project):
        logger.info("notify_pm_on_task %s muted", task)
        return
    team = task.project.get_pm_team()
    if team:
        try:

            email_subject = get_notify_email_subject(project=task.project, subject=_('Notification'))

            context = {
                    'task': task,
                    'vtp_url': settings.BASE_URL + reverse('via_job_detail_tasks', args=(task.project_id,)),
                    'pm_message': pm_message
                }

            send_email.after_response(
                email_subject,
                settings.FROM_EMAIL_ADDRESS,
                team,
                'notifications/pm_on_task',
                context,
            )
            return
        except:
            import traceback
            tb = traceback.format_exc()  # NOQA
            mail_admins('[notify_pm_on_task]: notification failed',
                        'Project id = {0}. Job Number = {1}. Error = {2}.'.format(task.project.id, task.project.job_number, tb))


def notify_pm_task_ready(task):
    if NotificationMute.objects.project_muted(task.project):
        logger.info("notify_pm_task_ready %s muted", task)
        return
    team = task.project.get_pm_team()
    if team:
        try:
            email_subject = get_notify_email_subject(project=task.project, subject=_("Task ready.  {0}").format(task.assigned_to))

            context = {
                'task': task,
                'vtp_url': settings.BASE_URL
            }

            send_email.after_response(
                email_subject,
                settings.FROM_EMAIL_ADDRESS,
                team,
                'notifications/pm_task_ready',
                context,
            )
            return
        except:
            import traceback
            tb = traceback.format_exc()  # NOQA
            mail_admins('[notify_pm_task_ready]: notification failed',
                        'Project id = {0}. Job Number = {1}. Error = {2}.'.format(task.project.id, task.project.job_number, tb))


def notify_final_approval_needed(task):
    if NotificationMute.objects.project_muted(task.project):
        logger.info("notify_final_approval_needed %s muted", task)
        return
    team = task.project.get_pm_team()
    if team:
        if task.assigned_to:
            try:
                email_subject = get_notify_email_subject(project=task.project, subject=_("Needs Final Approval"))

                context = {
                    'approver': task.assigned_to,
                    'task': task,
                    'vtp_url': settings.BASE_URL
                }

                send_email.after_response(
                    email_subject,
                    settings.FROM_EMAIL_ADDRESS,
                    [task.assigned_to.email],
                    'notifications/final_approval_needed',
                    context,
                    team
                )
                return
            except:
                # pass
                import traceback
                tb = traceback.format_exc()  # NOQA
                mail_admins('[notify_final_approval_needed]: notification failed',
                            'Project id = {0}, Task id = {1}. (Is assigned_to set?). {2}'.format(task.project.id, task.id, tb))


def via_rejected_task(user, task):
    if NotificationMute.objects.project_muted(task.project):
        logger.info("via_rejected_task %s muted", task)
        return
    team = task.project.get_pm_tsg_team()
    if team:
        try:
            email_subject = get_notify_email_subject(project=task.project, subject=_("Rejected task by {0}").format(user.name))

            context = {
                'user': user,
                'project': task.project,
                'task': task,
                'vtp_url': settings.BASE_URL + reverse('via_job_detail_overview', args=(task.project.id,))
            }

            send_email.after_response(
                email_subject,
                settings.FROM_EMAIL_ADDRESS,
                team,
                'notifications/via_rejected_task',
                context
            )
            return
        except:
            import traceback
            tb = traceback.format_exc()  # NOQA
            mail_admins('[via_rejected_task]: notification failed',
                        'Project id = {0}. Job Number = {1}. Error = {2}.'.format(task.project.id, task.project.job_number, tb))


def notify_assigned_to_task_assigned(task):
    if NotificationMute.objects.project_muted(task.project):
        logger.info("notify_assigned_to_task %s muted", task)
        return
    team = task.project.get_pm_team()
    if team:
        assignee = task.assigned_to
        try:
            if isinstance(assignee, CircusUser):
                to_list = [assignee.email]
            elif isinstance(assignee, Account):
                to_list = assignee.cast(Vendor).get_job_contacts()
            else:
                to_list = []

            if to_list:
                try:

                    email_subject = get_notify_email_subject(project=task.project, subject=_("New task assigned"))
                    wordcount = 0
                    if not task.is_translation():
                        for asset in task.project.kit.source_files():
                            wordcount += asset.analysis_for_target(task.service.target).total_wordcount()

                    context = {
                        'vendor': assignee,
                        'task': task,
                        'wordcount': wordcount,
                        'vtp_url': settings.VENDOR_URL
                    }

                    send_email.after_response(
                        email_subject,
                        settings.FROM_EMAIL_ADDRESS,
                        to_list,
                        'notifications/vendor_assigned_task',
                        context,
                        team
                    )
                    return
                except:
                    import traceback
                    tb = traceback.format_exc()  # NOQA
                    mail_admins('[notify_assigned_to_task_assigned]: notification failed',
                                '(Is vendor set, with a jobs_email set?) Project id = {0}. Job Number = {1}. Error = {2}. '.format(task.project.id, task.project.job_number, tb))

        except:
            import traceback
            tb = traceback.format_exc()  # NOQA
            mail_admins('[notify_assigned_to_task_assigned]: notification failed',
                        '(Is vendor set, with a jobs_email set?) Project id = {0}. Job Number = {1}. Error = {2}. '.format(task.project.id, task.project.job_number, tb))


def notify_assigned_to_task_ready(task):
    if NotificationMute.objects.project_muted(task.project):
        logger.info("notify_assigned_to_task_ready %s muted", task)
        return
    team = task.project.get_pm_team()
    if team:
        assignee = task.assigned_to
        try:
            if isinstance(assignee, CircusUser):
                to_list = [assignee.email]
            elif isinstance(assignee, Account):
                to_list = assignee.cast(Vendor).get_job_contacts()
            else:
                to_list = []

            if to_list:
                try:
                    email_subject = get_notify_email_subject(project=task.project, subject=_("Task ready to start"))

                    context = {
                        'vendor': assignee,
                        'task': task,
                        'vtp_url': settings.VENDOR_URL
                    }

                    send_email.after_response(
                        email_subject,
                        settings.FROM_EMAIL_ADDRESS,
                        to_list,
                        'notifications/vendor_task_ready',
                        context,
                        team
                    )
                    return
                except:
                    # pass
                    # mail_admins('[notify_assigned_to_task_ready]: notification failed',
                    # 'Project id = {0}. (Is vendor set, with a jobs_email set?)'.format(task.project.id))
                    import traceback
                    tb = traceback.format_exc()  # NOQA
                    mail_admins('[notify_assigned_to_task_ready]: notification failed',
                                '(Is vendor set, with a jobs_email set?) Project id = {0}. Job Number = {1}. Error = {2}. '.format(task.project.id, task.project.job_number, tb))
        except:
            import traceback
            tb = traceback.format_exc()  # NOQA
            mail_admins('[notify_assigned_to_task_ready]: notification failed',
                        '(Is vendor set, with a jobs_email set?) Project id = {0}. Job Number = {1}. Error = {2}. '.format(task.project.id, task.project.job_number, tb))


def vendor_rejected_task(vendor, task):
    if NotificationMute.objects.project_muted(task.project):
        logger.info("vendor_rejected_task %s muted", task)
        return
    team = task.project.get_pm_team()
    if settings.VIA_SUPPLIER_MANAGEMENT_EMAIL_ALIAS:
        team.append(settings.VIA_SUPPLIER_MANAGEMENT_EMAIL_ALIAS)
    if team:
        try:
            email_subject = get_notify_email_subject(project=task.project, subject=_("Rejected task by {0}").format(vendor.name))

            context = {
                'vendor': vendor,
                'project': task.project,
                'task': task,
                'vtp_url': settings.BASE_URL + reverse('via_job_detail_overview', args=(task.project.id,))
            }

            send_email.after_response(
                email_subject,
                settings.FROM_EMAIL_ADDRESS,
                team,
                'notifications/vendor_rejected_task',
                context,
                vendor.get_job_contacts()
            )
            return
        except:
            import traceback
            tb = traceback.format_exc()  # NOQA
            mail_admins('[vendor_rejected_task]: notification failed',
                        '(Is there a team assigned?) Project id = {0}. Job Number = {1}. Error = {2}. '.format(task.project.id, task.project.job_number, tb))


def vendor_did_not_respond_to_project(assigned_to, project):
    if NotificationMute.objects.project_muted(project):
        logger.info("vendor_did_not_respond_to_project %s muted", project)
        return

    team = project.get_pm_team()

    if team:
        try:
            email_subject = get_notify_email_subject(project=project, subject=_("No response by {0}.").format(assigned_to))

            context = {
                'vendor': assigned_to,
                'project': project,
                'vtp_url': settings.BASE_URL + reverse('via_job_detail_overview', args=(project.id,))
            }

            send_email.after_response(
                email_subject,
                settings.FROM_EMAIL_ADDRESS,
                team,
                'notifications/vendor_did_not_respond_to_project',
                context
            )
            return
        except:
            import traceback
            tb = traceback.format_exc()  # NOQA
            mail_admins('[vendor_did_not_respond_to_project]: notification failed',
                        '(Is there a team assigned?) Project id = {0}. Job Number = {1}. Error = {2}. '.format(project.id, project.job_number, tb))


def vendor_delivery_overdue(assigned_to, project):
    if NotificationMute.objects.project_muted(project):
        logger.info("vendor_delivery_overdue %s muted", project)
        return

    tasks = project.get_overdue_tasks(assigned_to.cast(Account))
    team = project.get_pm_team()

    if assigned_to.account_type.code == settings.VENDOR_USER_TYPE:
        vendor_contacts = assigned_to.cast(Vendor).get_job_contacts()
    else:
        vendor_contacts = assigned_to.email

    if team:
        try:
            email_subject = get_notify_email_subject(project=project, subject=_("Delivery overdue for {0}").format(assigned_to))

            context = {
                'for_vendor': False,
                'vendor': assigned_to,
                'project': project,
                'tasks': tasks,
                'vtp_url': settings.BASE_URL + reverse('via_job_detail_overview', args=(project.id,))
            }

            # email via team
            send_email.after_response(
                email_subject,
                settings.FROM_EMAIL_ADDRESS,
                team,
                'notifications/vendor_delivery_overdue',
                context
            )

            email_subject = get_notify_email_subject(project=project, subject=_("Delivery overdue"))

            context2 = {
                'for_vendor': True,
                'vendor': assigned_to,
                'project': project,
                'tasks': tasks,
                'vtp_url': settings.VENDOR_URL + reverse('vendor_dashboard')
            }

            # email to vendor
            send_email.after_response(
                email_subject,
                settings.FROM_EMAIL_ADDRESS,
                vendor_contacts,
                'notifications/vendor_delivery_overdue',
                context2
            )
            return
        except:
            # pass
            import traceback
            tb = traceback.format_exc()  # NOQA
            mail_admins('[vendor_delivery_overdue]: notification failed',
                        '(Is there a team assigned and vendor contact email set?) Project id = {0}. Job Number = {1}. Error = {2}. '.format(project.id, project.job_number, tb))


def project_manual_quote_needed_via(project):
    if NotificationMute.objects.project_muted(project):
        logger.info("project_manual_quote_needed_via %s muted", project)
        return

    # AE is not included on this one because they get cc'd on the one to the client.
    team = project.get_estimates_team()

    if team:
        try:
            to_list = team
            email_subject = get_notify_email_subject(project=project, subject=_("Needs manual estimate"))

            context = {
                'project': project,
                'vtp_url': settings.BASE_URL
            }

            send_email.after_response(
                email_subject,
                settings.FROM_EMAIL_ADDRESS,
                to_list,
                'notifications/project_manual_quote_needed_via',
                context,
            )
            return
        except:
            import traceback
            tb = traceback.format_exc()  # NOQA
            mail_admins('[project_manual_quote_needed]: notification failed',
                        'Project id = {0}. Job Number = {1}. Error = {2}.'.format(project.id, project.job_number, tb))


def project_manual_quote_needed(project):
    if NotificationMute.objects.project_muted(project):
        logger.info("project_manual_quote_needed %s muted", project)
        return

    client_poc = project.client_poc
    team = project.get_ae_team()
    if project.client.manifest.client_notification_group:
        team = team + project.get_client_notification_team()

    if client_poc and team:
        try:
            to_list = [client_poc.email]
            email_subject = get_notify_client_email_subject(project=project, subject=_('Needs manual estimate'))

            context = {
                'project': project,
                'vtp_url': settings.BASE_URL
            }

            send_email.after_response(
                email_subject,
                settings.FROM_EMAIL_ADDRESS,
                to_list,
                'notifications/project_manual_quote_needed',
                context,
                cc=team,
            )
            return
        except:
            import traceback
            tb = traceback.format_exc()  # NOQA
            mail_admins('[project_manual_quote_needed]: notification failed',
                        'Project id = {0}. Job Number = {1}. Error = {2}.'.format(project.id, project.job_number, tb))


def notify_new_content_added(project):
    if NotificationMute.objects.project_muted(project):
        logger.info("New Reference File added %s muted", project)
        return

    team = project.get_ae_pm_team()

    if team:
        try:
            email_subject = get_notify_email_subject(project=project, subject=_('New Reference File Added'))

            context = {
                'project': project,
                'vtp_url': settings.BASE_URL + reverse('client_project_detail', args=(project.id,))
            }

            send_email.after_response(
                email_subject,
                settings.FROM_EMAIL_ADDRESS,
                team,
                'notifications/new_reference_file_added',
                context,
            )
            return
        except:
            import traceback
            tb = traceback.format_exc()  # NOQA
            mail_admins('[New Reference File Added]: notification failed',
                        'Project id = {0}. Job Number = {1}. Error = {2}.'.format(project.id, project.job_number, tb))


def project_quote_ready(project):
    if NotificationMute.objects.project_muted(project):
        logger.info("project_quote_ready %s muted", project)
        return

    client_poc = project.client_poc
    team = project.get_estimate_team_full()
    if project.client.manifest.client_notification_group:
        team = team + project.get_client_notification_team()

    if client_poc and team:
        show_subtotals = project.billable_tasks_per_locale_count() > 1

        from shared.viewmodels import ProjectTargetSetViewModel
        project_targets = ProjectTargetSetViewModel(project)

        from tasks.make_tasks import _verify_client_discount_task
        client_discount_flag = _verify_client_discount_task(project)
        original_price_standard = original_price_express = 0
        if client_discount_flag:
            original_price_standard, original_price_express = project.project_original_price()

        context = {
            'project': project,
            'project_target_tasks': project_targets,
            'show_subtotals': show_subtotals,
            'client_discount_flag': client_discount_flag,
            'original_price_standard': original_price_standard,
            'original_price_express':  original_price_express,
            'vtp_url': settings.BASE_URL,
        }

        try:
            to_list = [client_poc.email] + project.get_client_notification_team()
            to_list = list(set(to_list))
            email_subject = get_notify_client_email_subject(project=project, subject=_('Estimate ready'))

            send_email.after_response(
                email_subject,
                settings.FROM_EMAIL_ADDRESS,
                to_list,
                'notifications/project_quote_ready',
                context,
                team
            )
            return
        except:
            import traceback
            tb = traceback.format_exc()  # NOQA
            mail_admins('[project_quote_ready]: notification failed',
                        'Project id = {0}. Job Number = {1}. Error = {2}.'.format(project.id, project.job_number, tb))


def notify_new_job_ordered(project, auto_approved=False):
    if NotificationMute.objects.project_muted(project):
        logger.info("notify_new_job_ordered %s muted", project)
        return

    client_poc = project.client_poc
    team = project.get_ae_pm_team()
    if project.client.manifest.client_notification_group:
        team = team + project.get_client_notification_team()

    try:
        if client_poc and team:
            show_subtotals = project.billable_tasks_per_locale_count() > 1

            from tasks.make_tasks import _verify_client_discount_task
            client_discount_flag = _verify_client_discount_task(project)
            original_price_standard = original_price_express = 0
            if client_discount_flag:
                original_price_standard, original_price_express = project.project_original_price()

            context = {
                'project': project,
                'quote': project.quote_summary_no_costs(),
                'show_subtotals': show_subtotals,
                'client_discount_flag': client_discount_flag,
                'original_price_standard': original_price_standard,
                'original_price_express': original_price_express,
                'vtp_url': settings.BASE_URL,
                'auto_approved': auto_approved
            }

            try:
                to_list = [client_poc.email]
                email_subject = get_notify_client_email_subject(project=project, subject=_('Order Confirmation'))

                send_email.after_response(
                    email_subject,
                    settings.FROM_EMAIL_ADDRESS,
                    to_list,
                    'notifications/client_new_job_ordered',
                    context,
                    cc=team,
                    bcc=[settings.VIA_SALES_GROUP_EMAIL_ALIAS],
                )
                return
            except:
                import traceback
                tb = traceback.format_exc()  # NOQA
                mail_admins('[notify_new_job_ordered]: notification failed',
                            'Project id = {0}. Job Number = {1}. Error = {2}.'.format(project.id, project.job_number, tb))
    except:
        import traceback
        tb = traceback.format_exc()  # NOQA
        mail_admins('[notify_new_job_ordered]: notification failed',
                    'Project id = {0}. Job Number = {1}. Error = {2}.'.format(project.id, project.job_number, tb))


def notify_client_job_canceled(project):
    if NotificationMute.objects.project_muted(project):
        logger.info("notify_client_job_canceled %s muted", project)
        return

    client_poc = project.client_poc
    team = project.get_ae_pm_team()
    if project.client.manifest.client_notification_group:
        team = team + project.get_client_notification_team()

    try:
        if client_poc and team:
            try:
                to_list = [client_poc.email]
                email_subject = get_notify_client_email_subject(project=project, subject=_('Canceled'))

                context = {
                    'project': project,
                    'vtp_url': settings.BASE_URL
                }

                send_email.after_response(
                    email_subject,
                    settings.FROM_EMAIL_ADDRESS,
                    to_list,
                    'notifications/client_job_canceled',
                    context,
                    team
                )
                return
            except:
                # pass
                mail_admins('[notify_client_job_canceled]: notification failed',
                            'Project id = {0}. Job Number = {1}.'.format(project.id, project.job_number))
    except:
        # pass
        mail_admins('[notify_client_job_canceled]: notification failed',
                    'Project id = {0}. Job Number = {1}.'.format(project.id, project.job_number))


def notify_client_job_ready(project):
    if NotificationMute.objects.project_muted(project):
        logger.info("notify_client_job_ready %s muted", project)
        return

    client_poc = project.client_poc
    team = project.get_ae_pm_team()
    if project.client.manifest.client_notification_group:
        team = team + project.get_client_notification_team()
    try:
        if client_poc and team:
            try:
                to_list = [client_poc.email]
                email_subject = get_notify_client_email_subject(project=project, subject=_('Delivered'))

                context = {
                    'project': project,
                    'vtp_url': settings.BASE_URL
                }

                send_email.after_response(
                    email_subject,
                    settings.FROM_EMAIL_ADDRESS,
                    to_list,
                    'notifications/client_job_delivered',
                    context,
                    team
                )
                return
            except:
                # pass
                mail_admins('[notify_client_job_ready]: notification failed',
                            'Project id = {0}. Job Number = {1}.'.format(project.id, project.job_number))
    except:
        # pass
        mail_admins('[notify_client_job_ready]: notification failed',
                    'Project id = {0}. Job Number = {1}.'.format(project.id, project.job_number))


def notify_via_client_asset_pickup(tla, project):
    if NotificationMute.objects.project_muted(project):
        logger.info("notify_via_client_asset_pickup %s muted", project)
        return

    team = project.get_ae_team()

    if team:
        try:
            email_subject = get_notify_email_subject(project=project, subject=_("File {0} has been picked up").format(tla.name))

            context = {
                'project': project,
                'tla': tla,
                'vtp_url': settings.BASE_URL + reverse('via_job_detail_overview', args=(project.id,))
            }

            send_email.after_response(
                email_subject,
                settings.FROM_EMAIL_ADDRESS,
                team,
                'notifications/client_job_delivered_pickup',
                context,
            )
            return
        except:
            import traceback
            tb = traceback.format_exc()  # NOQA
            mail_admins('[notify_via_client_asset_pickup]: notification failed',
                        'Project id = {0}. Job Number = {1}. Error = {2}.'.format(project.id, project.job_number, tb))


def notify_via_job_completed(project):
    if NotificationMute.objects.project_muted(project):
        logger.info("notify_via_job_completed %s muted", project)
        return

    team = project.get_ae_pm_team()

    if team:
        try:
            email_subject = get_notify_email_subject(project=project, subject=_('Completed'))

            context = {
                'project': project,
                'vtp_url': settings.BASE_URL + reverse('via_job_detail_overview', args=(project.id,))
            }

            send_email.after_response(
                email_subject,
                settings.FROM_EMAIL_ADDRESS,
                team,
                'notifications/client_job_completed',
                context
            )
            return
        except:
            import traceback
            tb = traceback.format_exc()  # NOQA
            mail_admins('[notify_via_client_asset_pickup]: notification failed',
                        'Project id = {0}. Job Number = {1}. Error = {2}.'.format(project.id, project.job_number, tb))


def notify_via_analysis_complete(project):
    if NotificationMute.objects.project_muted(project):
        logger.info("notify_via_analysis_complete %s muted", project)
        return

    team = project.get_ae_pm_team()

    if team:
        try:
            email_subject = get_notify_client_email_subject(project=project, subject=_('Analysis Complete'))

            context = {
                'project': project,
                'vtp_url': settings.BASE_URL
            }

            send_email.after_response(
                email_subject,
                settings.FROM_EMAIL_ADDRESS,
                team,
                'notifications/client_analysis_complete',
                context,
                team
            )
            return
        except:
            import traceback
            tb = traceback.format_exc()  # NOQA
            mail_admins('[notify_via_analysis_complete]: notification failed',
                        'Project id = {0}. Job Number = {1}. Error = {2}.'.format(project.id, project.job_number, tb))


def notify_no_task_active(project):
    if NotificationMute.objects.project_muted(project):
        logger.info("notify_no_task_active %s muted", project)
        return

    team = project.get_pm_team()

    if team:
        try:
            email_subject = get_notify_client_email_subject(project=project, subject=_('No Task is Active'))

            context = {
                'project': project,
                'vtp_url': settings.BASE_URL
            }

            send_email(
                email_subject,
                settings.FROM_EMAIL_ADDRESS,
                team,
                'notifications/client_analysis_complete',
                context,
                team
            )
            return
        except:
            import traceback
            tb = traceback.format_exc()  # NOQA
            mail_admins('[notify_no_task_active]: notification failed',
                        'Project id = {0}. Job Number = {1}. Error = {2}.'.format(project.id, project.job_number, tb))


def confirm_account(user):
    try:
        email_subject = get_notify_email_subject(subject=_('Confirm your {0} account').format(settings.APP_FULL_NAME))

        context = {
            'user': user,
            'confirm_url': settings.BASE_URL + reverse('activate_account', args=(user.id, user.activation_code)),
            'app_name': settings.APP_NAME,
            'app_full_name': settings.APP_FULL_NAME
        }

        send_email.after_response(
            email_subject,
            settings.FROM_EMAIL_ADDRESS,
            [user.email],
            'notifications/confirm_account',
            context,
        )
        return
    except:
        import traceback
        tb = traceback.format_exc()  # NOQA
        mail_admins('[confirm_account]: notification failed',
                    'User id = {0}. Error = {1}.'.format(user.id, tb))


def join_account_request(join_request):
    email_subject = get_notify_email_subject(
        subject=_('{0} has joined {1} on the {2}').format(
            join_request.user,
            join_request.account.name,
            settings.APP_FULL_NAME)
    )

    account_admins = join_request.account.contacts.filter(
        groups__name=DEPARTMENT_ADMINISTRATOR_GROUP).values_list('email', flat=True)

    if not account_admins:
        mail_admins(
            '[join_account_request]: notification failed',
            ('Request id = {0}.\n'
             'Account = {1} {2}\n'
             'No admins found for account.'.format(
                 join_request.id,
                 join_request.account.id, join_request.account)))
        return

    context = {
        'join_request': join_request,
        'manage_url': settings.BASE_URL + reverse('client_manage_users'),
        'app_name': settings.APP_NAME,
        'app_full_name': settings.APP_FULL_NAME
    }

    send_email.after_response(
        email_subject,
        settings.FROM_EMAIL_ADDRESS,
        account_admins,
        'notifications/join_request',
        context,
    )


def notify_via_new_client_user(user):
    """
    :type user: clients.models.ClientContact
    """
    if user.account:
        account_name = user.account.name

        if user.account.parent:
            account_name = _('{0} / {1}').format(user.account.parent.name, user.account.name)
    else:
        account_name = user.email.rsplit('@', 1)[1]
    subject = _('New user {0} ({1})').format(user.get_full_name(), account_name)
    subject = get_notify_email_subject(subject=subject)

    to = [settings.VIA_SALES_GROUP_EMAIL_ALIAS]

    if user.account:
        account_execs = ClientTeamRole.objects.filter(
            client=user.account, role=AE_ROLE)
        ae_emails = account_execs.values_list('contact__email', flat=True)
        to.extend(ae_emails)

    context = {
        'user': user,
        'vtp_url': settings.BASE_URL
    }

    send_email.after_response(
        subject,
        settings.FROM_EMAIL_ADDRESS,
        to,
        'notifications/via_new_client_user',
        context,
    )


def notify_via_new_client_account(client):
    """
    :type client: clients.models.Client
    """

    if client.parent:
        subject = _('New {0} department {1}').format(client.parent.name, client.name)
    else:
        subject = _('New client {0}').format(client.name)
    subject = get_notify_email_subject(subject=subject)

    to = [settings.VIA_SALES_GROUP_EMAIL_ALIAS]

    account_execs = ClientTeamRole.objects.filter(client=client, role=AE_ROLE)
    ae_emails = account_execs.values_list('contact__email', flat=True)
    to.extend(ae_emails)

    contacts = client.contacts.all()

    context = {
        'client': client,
        'contacts': contacts,
        'vtp_url': settings.BASE_URL
    }

    send_email.after_response(
        subject,
        settings.FROM_EMAIL_ADDRESS,
        to,
        'notifications/via_new_client_account',
        context,
    )


def notify_job_messages_email(email_comment, mail_to_user, email_count, last_modified):
    try:
        if mail_to_user:
            try:
                to_list = [mail_to_user]
                email_subject = _('{0} : {1} new messages since {2}').format(settings.APP_SLUG_INSTANCE, str(email_count), str(last_modified))

                context = {
                    'comments': email_comment,
                    'vtp_url': settings.BASE_URL,
                }

                send_email.after_response(
                    email_subject,
                    settings.FROM_EMAIL_ADDRESS,
                    to_list,
                    'notifications/job_message_email',
                    context,
                )
                return
            except:
                # pass
                mail_admins('[job_message]: notification failed',
                            '{0}. (Is this correct email id?)'.format(mail_to_user))
    except:
        # pass
        mail_admins('[job_message]: notification failed',
                    '{0}. (Is this correct email id?)'.format(mail_to_user))


def notify_due_dates_changed(task):
    if NotificationMute.objects.project_muted(task.project):
        logger.info("notify_assigned_to_task %s muted", task)
        return
    team = task.project.get_pm_team()
    if team:
        assignee = task.assigned_to
        try:
            if isinstance(assignee, CircusUser):
                to_list = [assignee.email]
            elif isinstance(assignee, Account):
                to_list = assignee.cast(Vendor).get_job_contacts()
            else:
                to_list = []

            if to_list:
                try:

                    email_subject = get_notify_email_subject(project=task.project, subject=_("Rescheduled all due dates"))

                    context = {
                        'vendor': assignee,
                        'task': task,
                        'vtp_url': settings.VENDOR_URL
                    }

                    send_email.after_response(
                        email_subject,
                        settings.FROM_EMAIL_ADDRESS,
                        to_list,
                        'notifications/due_dates_notification',
                        context,
                        team
                    )
                    return
                except:
                    import traceback
                    tb = traceback.format_exc()  # NOQA
                    mail_admins('[notify_due_dates_changed]: notification failed',
                                '(Is vendor set, with a jobs_email set?) Project id = {0}. Job Number = {1}. Error = {2}. '.format(task.project.id, task.project.job_number, tb))
        except:
            import traceback
            tb = traceback.format_exc()  # NOQA
            mail_admins('[notify_due_dates_changed]: notification failed',
                        '(Is vendor set, with a jobs_email set?) Project id = {0}. Job Number = {1}. Error = {2}. '.format(task.project.id, task.project.job_number, tb))


def notify_account_welcome_email(user):
    try:
        email_subject = get_notify_email_subject(subject=_('Welcome to the {0}').format(settings.APP_FULL_NAME))

        context = {
            'user': user,
            'app_name': settings.APP_NAME,
            'app_full_name': settings.APP_FULL_NAME
        }

        send_email.after_response(
            email_subject,
            settings.FROM_EMAIL_ADDRESS,
            [user.email],
            'notifications/client_welcome_email',
            context,
        )
        return
    except:
        import traceback
        tb = traceback.format_exc()  # NOQA
        mail_admins('[notify_account_welcome_email]: notification failed', 'User id = {0}. Error = {1}.'.format(user.id, tb))

def notify_client_job_access_rejected(project, requester):
    if NotificationMute.objects.project_muted(project):
        logger.info("notify_client_job_access_rejected %s muted", project)
        return

    client_poc = project.client_poc
    team = project.get_ae_pm_team()
    if project.client.manifest.client_notification_group:
        team = team + project.get_client_notification_team()

    try:
        if client_poc and team:
            try:
                to_list = [client_poc.email, requester.email]
                email_subject = get_notify_client_email_subject(project=project, subject=_('Rejected Access'))

                send_email(
                    email_subject,
                    settings.FROM_EMAIL_ADDRESS,
                    to_list,
                    'notifications/job_access_request_rejected',
                    {
                        'project': project,
                        'requester': requester.get_full_name(),
                        'vtp_url': settings.BASE_URL
                    },
                    team
                )
                return
            except:
                # pass
                mail_admins('[notify_client_job_access_rejected]: notification failed',
                    'Project id = {0}. Job Number = {1}.'.format(project.id, project.job_number))
    except:
        # pass
        mail_admins('[notify_client_job_access_rejected]: notification failed',
                'Project id = {0}. Job Number = {1}.'.format(project.id, project.job_number))


def notify_client_job_access_provided(project, requester):
    if NotificationMute.objects.project_muted(project):
        logger.info("notify_client_job_access_provided %s muted", project)
        return

    client_poc = project.client_poc
    team = project.get_ae_pm_team()
    if project.client.manifest.client_notification_group:
        team = team + project.get_client_notification_team()
    try:
        if client_poc and team:
            try:
                to_list = [client_poc.email, requester.email]
                email_subject = get_notify_client_email_subject(project=project, subject=_('Provided Access'))

                send_email(
                    email_subject,
                    settings.FROM_EMAIL_ADDRESS,
                    to_list,
                    'notifications/job_access_request_provided',
                    {
                        'project': project,
                        'requester': requester.get_full_name(),
                        'vtp_url': settings.BASE_URL
                    },
                    team
                )
                return
            except:
                # pass
                mail_admins('[notify_client_job_access_provided]: notification failed',
                    'Project id = {0}. Job Number = {1}.'.format(project.id, project.job_number))
    except:
        # pass
        mail_admins('[notify_client_job_access_provided]: notification failed',
                'Project id = {0}. Job Number = {1}.'.format(project.id, project.job_number))


