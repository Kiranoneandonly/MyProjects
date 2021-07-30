# -*- coding: utf-8 -*-
"""Authorization rules for vendor_portal."""

from shared.protection import Protector
from tasks.models import Task, TaskLocaleTranslationKit


def task_owns_tltk(task, tltk_id):
    try:
        return task.trans_kit.id == int(tltk_id)
    except TaskLocaleTranslationKit.DoesNotExist:
        return False


def task_owns_tla(task, tla_id):
    return task.localized_assets.filter(id=tla_id).exists()


constraints = {
    'tltk_id': task_owns_tltk,
    'tla_id': task_owns_tla
}
protected_task = Protector(Task, condition=Task.is_assignee,
                           constraints=constraints)
