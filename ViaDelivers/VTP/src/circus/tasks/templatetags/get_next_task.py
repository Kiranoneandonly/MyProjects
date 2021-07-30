from django import template
from tasks.models import Task

register = template.Library()


@register.simple_tag
def get_next_task(key):
    predecessor = Task.objects.filter(predecessor_id=key)
    next_task = None
    for pred in predecessor:
        next_task = pred.id
    return next_task

@register.assignment_tag
def get_task_view(task, state):
    service_tasks = task.project.all_workflow_tasks().filter(service__service_type_id=task.service.service_type.id)
    for index,service_task in enumerate(list(service_tasks)):
        if service_task.id == task.id:
            task_index = index

    if state == 'previous':
        if task_index >= 1:
            task_index -= 1
        else:
            task_index = None
    else:
        if task_index < len(list(service_tasks))-1:
            task_index += 1
        else:
            task_index = None

    if task_index >= 0:
        return service_tasks[task_index]
