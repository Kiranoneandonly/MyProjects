# -*- coding: utf-8 -*-
from localization_kits import authorization as loc_kit_authz
from projects.models import Project
from shared.protection import Protector
import logging

logger = logging.getLogger('circus.' + __name__)

any_via_user = loc_kit_authz.any_via_user
project_viewers = loc_kit_authz.project_viewers


def client_owns_project(project, user):
    try:
        if not user.is_authenticated():
            return False
        return project.client == user.account
    except Exception, error:
        import traceback
        tb = traceback.format_exc()  # NOQA
        print tb
        logger.error("client_owns_project error", exc_info=True)
        return False


constraints = {
    # You may see all LCIDs, they're not project-specific.
    'lcid': lambda project, lcid: True
}

project_clients = Protector(Project, 'proj_id', client_owns_project, constraints)
