from shared.protection import Protector
from tasks.models import Task


def is_via_or_assignee(task, user):
    if user.is_authenticated():
        if user.is_via():
            return True
        if task.is_assignee(user):
            return True
    return False

via_or_assignee = Protector(Task, condition=is_via_or_assignee)
