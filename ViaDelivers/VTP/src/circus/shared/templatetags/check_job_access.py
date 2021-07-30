from django import template
from projects.models import ProjectAccess

register = template.Library()


@register.simple_tag
def check_job_access(user_id, project_id):
    project_access = None
    try:
        project_access = ProjectAccess.objects.get(project_id=project_id, contact_id=user_id, is_access_given=True)
    except:
        return False
    if project_access:
        return True
    return False
