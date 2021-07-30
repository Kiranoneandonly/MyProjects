import logging

logger = logging.getLogger('circus.' + __name__)

SCORE_ORDER = [
    'client',
    'locale',
    'basis',
    'scheme'
]

VENDOR_RATE_SCORE_ORDER = [
    'client',
    'locale',
    'vertical'
]


def _common_client_price_scores(client_price, client, task, pricing_scheme):
    """
    :type client_price: prices.models.ClientPrice
    """
    scores = {
        'client': 0,
        'locale': 0,
        'basis': 0,
        'scheme': 0
    }

    # lower is better
    if client_price.client == client:
        scores['client'] = -2
    elif client.parent and client_price.client == client.parent:
        scores['client'] = -1

    if client_price.pricing_scheme == pricing_scheme:
        scores['scheme'] = -1

    scores['locale'] = task.service_match_score(client_price.service)

    return scores


def _client_translation_price_scores(client_price, pricing_basis):
    """
    :type client_price: prices.models.ClientTranslationPrice
    """
    scores_basis = 0
    try:
        scores_basis = -1 if (client_price.basis == pricing_basis) else 0
    except:
        pass
    scores = {'basis': scores_basis}
    return scores


def _client_price_scores(client_price, client, task):
    if client:
        pricing_scheme = client.manifest.pricing_scheme
        pricing_basis = client.manifest.pricing_basis
    else:
        pricing_scheme = None
        pricing_basis = None

    scores = _common_client_price_scores(client_price, client,
                                         task, pricing_scheme)

    if task.is_translation():
        scores.update(_client_translation_price_scores(client_price, pricing_basis))

    return scores


def search_by_basis_client(queryset, client=None, task=None):
    """
    :type queryset: django.db.models.query.QuerySet[prices.models.ClientPrice]
    :type client: clients.models.Client
    :type task: tasks.models.Task
    :return: prices.models.ClientPrice
    """

    def sort_key(client_price):
        # score this entry for how well it matches our criteria
        scores = _client_price_scores(client_price, client, task)
        # rank according to which sorts of matches are most important
        return [scores[category] for category in SCORE_ORDER]

    client_prices = list(queryset)
    client_prices.sort(key=sort_key)

    if not client_prices:
        return None
    else:
        return client_prices[0]


def _vendor_rate_scores(rate, client, task):
    """
    :type rate: prices.models.VendorRate
    :type client: clients.models.Client
    :type task: tasks.models.Task
    """
    scores = {
        'client': 0,
        'locale': 0,
        'vertical': 0
    }

    # lower is better
    if rate.client == client:
        scores['client'] = -2
    elif client.parent and rate.client == client.parent:
        scores['client'] = -1

    scores['locale'] = task.service_match_score(rate.service)

    if rate.vertical == client.manifest.vertical:
        scores['vertical'] = -1

    return scores


def search_by_basis_vendor(queryset, client, task):
    """
    :type queryset: django.db.models.query.QuerySet[prices.models.VendorRate]
    :type client: clients.models.Client
    :type task: tasks.models.Task
    """

    def sort_key(rate):
        # score this entry for how well it matches our criteria
        scores = _vendor_rate_scores(rate, client, task)
        # rank according to which sorts of matches are most important
        return [scores[category] for category in VENDOR_RATE_SCORE_ORDER]

    rates = list(queryset)
    rates.sort(key=sort_key)

    if not rates:
        return None
    else:
        return rates[0]
