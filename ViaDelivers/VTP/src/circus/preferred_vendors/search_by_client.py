import logging

logger = logging.getLogger('circus.' + __name__)


def search_by_client(queryset, client=None, vertical=None):
    queryset = queryset.order_by('client', 'priority')
    try:

        if client:
            obj = next((c for c in queryset if c.client == client and c.vertical == vertical), None)
            if obj:
                return obj

            obj = next((c for c in queryset if c.client == client), None)
            if obj:
                return obj

        if not obj and client.parent:
            from clients.models import Client
            parent = client.parent.cast(Client)
            obj = next((c for c in queryset if c.client == parent and c.vertical == vertical), None)
            if obj:
                return obj

            obj = next((c for c in queryset if c.client == parent), None)
            if obj:
                return obj

        if not obj:
            obj = next((c for c in queryset if c.vertical == vertical), None)
            if obj:
                return obj

        obj = next((c for c in queryset), None)
        if obj:
            return obj

        return queryset[:1] or None

    except:
        import traceback
        tb = traceback.format_exc()  # NOQA
        logger.error(tb)
        logger.info('search_by_client: ' + unicode(queryset))
        return None
