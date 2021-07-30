# -*- coding: utf-8 -*-
from shared.protection import Protector


def is_via_user(model, user):
    """
    :type user: accounts.models.CircusUser or AnonymousUser
    """
    return user.is_authenticated() and user.is_via()

any_via_user = Protector(condition=is_via_user)
