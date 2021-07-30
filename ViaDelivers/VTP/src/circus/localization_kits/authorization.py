# -*- coding: utf-8 -*-
from localization_kits.models import FileAsset
from projects.models import Project
from services.managers import FINAL_APPROVAL_SERVICE_TYPE
from shared.protection import Protector
from tasks.models import TaskLocaleTranslationKit, Task


def is_via_user(model, user):
    """
    :type user: accounts.models.CircusUser or AnonymousUser
    """
    return user.is_authenticated() and user.is_via()

any_via_user = Protector(condition=is_via_user)


def may_view_project_loc_kit(project, user):
    """
    :type project: projects.models.Project
    :type user: accounts.models.CircusUser or AnonymousUser
    """
    if not user.is_authenticated():
        return False

    if user.is_via():
        return True

    if user.account == project.client:
        return True

    # Is this user assigned to any of this project's tasks?
    # (including being on an account that's the assignee.)
    if project.task_set.get_user_tasks(user).exists():
        return True

    return False


def may_edit_project_loc_kit(project, user):
    """
    :type project: projects.models.Project
    :type user: accounts.models.CircusUser or AnonymousUser
    """
    if not user.is_authenticated():
        return False

    if user.is_via():
        return True

    if user.account == project.client:
        return True

    return False


def asset_belongs_to_project(project, asset_id):
    return FileAsset.objects.filter(id=asset_id, kit__project=project).exists()


project_constraints = {
    'asset_id': asset_belongs_to_project
}
project_viewers = Protector(Project, 'proj_id',
                            condition=may_view_project_loc_kit,
                            constraints=project_constraints)


project_owners = Protector(Project, 'proj_id',
                           condition=may_edit_project_loc_kit)


# TODO: These Constraints methods are duplicated between here
#     and vendor_portal. And while the Condition of a protector may vary with
#     context, it seems like the constraints between objects and their
#     descendants is constant, so this should be centralized.
def task_owns_tltk(task, tltk_id):
    try:
        return task.trans_kit.id == int(tltk_id)
    except TaskLocaleTranslationKit.DoesNotExist:
        return False


def task_owns_tla(task, tla_id):
    return task.localized_assets.filter(id=tla_id).exists()


def via_or_assignee_or_client_delivery(task, user):
    if not user.is_authenticated():
        return False

    if user.is_via():
        return True

    if task.is_assignee(user):
        return True

    # Clients may also get their delivery of the final product.
    # This seems like too much logic to put here. :-/
    # These conditions are pulled from ProjectTargetDeliveryViewModel.
    if (user.is_client() and task.is_complete() and
            task.service.service_type.code == FINAL_APPROVAL_SERVICE_TYPE and
            task.project.client == user.account):
        return True

    return False


constraints = {
    'tltk_id': task_owns_tltk,
    'tla_id': task_owns_tla
}
protected_task = Protector(Task, 'task_id',
                           condition=via_or_assignee_or_client_delivery,
                           constraints=constraints)
