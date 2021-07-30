"""Credit Card payments with Payflow Link.

OLS uses Payflow Link. Docs at
https://www.paypalobjects.com/webstatic/en_US/developer/docs/pdf/pp_payflowlink_guide.pdf

Payflow API docs are categorized as a "Classic API" (not REST API) on the PayPal
developer site, and we're using the "Legacy" version of Payflow (as of December
2013).
"""
import logging
from pyquery import PyQuery
import requests

from django.conf import settings
from django.core.mail import mail_admins
from shared import har

# How many seconds to wait to get a response from PayPal?
# Note our django app needs to start writing its response within 30 seconds
# or Heroku will think it frozen and kill it, so it need be less than that.
REQUEST_TIMEOUT = 24

# Payflow status codes:
APPROVED = 0
# There are lots more ways for things to go wrong in payment processing than
# just these! But these are ones I imagine might be useful to show to the user.
# Most of the others are probably something they can't be fix (and should be
# reported to us.)
DECLINED = 12
REFERRAL = 13
INVALID_ACCOUNT = 23
INVALID_EXPIRATION = 24
INSUFFICIENT_FUNDS = 50
EXCEEDS_TRANSACTION_LIMIT = 51
FAILED_AVS_CHECK = 112
CSC_MISMATCH = 114
# Sadly, none of that does us any good, because we don't actually get error
# codes with payflow-link.
GENERAL_ERROR = 99


DO_NOT_LOG_FIELDS = ['CARDNUM', 'EXPDATE', 'CSC']


logger = logging.getLogger('circus.' + __name__)


class ParseError(Exception):
    pass


def endpoint():
    if settings.PAYFLOW_LIVE_MODE:
        return 'https://payflowlink.paypal.com'
    else:
        return 'https://pilot-payflowlink.paypal.com'


def _redact(post_data):
    for key in DO_NOT_LOG_FIELDS:
        if key in post_data:
            if post_data[key] is None:
                continue
            post_data[key] = '[%s chars scrubbed]' % (len(post_data[key]),)


def _sale_request_data(amount, cc_data, user, project):
    # See Appendix B, "Submitting Transaction Data to the Payflow Link Server"
    # in the Payflow Link User's Guide.
    params = {
        # Required fields for all transactions:
        'LOGIN': settings.PAYFLOW_LOGIN,
        'PARTNER': settings.PAYFLOW_PARTNER_NAME,
        'TYPE': 'S',  # Sale
        'AMOUNT': amount,

        # API configuration. Show no forms, give us only the receipt.
        'ORDERFORM': 'False',
        'SHOWCONFIRM': 'False',
        'EMAILCUSTOMER': 'False',
        'ECHODATA': 'False',

        # Required fields if we gather payment details through our own form
        # rather than PayPal's:
        'METHOD': 'CC',  # Credit Card
        'ADDRESS': cc_data['street'],
        'CITY': cc_data['city'],
        'ZIP': cc_data['zip'],
        'CARDNUM': cc_data['cardnum'],
        'EXPDATE': cc_data['expdate'],

        # Optional order details for accounting
        'NAME': user.get_full_name(),
        'EMAIL': user.email,
        # Description appears to merchant and customer
        'DESCRIPTION': project.name,
        # Comments are for our reports only.
        'COMMENT1': project.client.name,
        'COMMENT2': u'VTP %s' % (project.job_number,)
    }

    if not settings.PAYFLOW_LIVE_MODE:
        params['DESCRIPTION'] = 'VTP Development Server\n' + params['DESCRIPTION']

    optional_cc_fields = {
        'state': 'STATE',
        'security_code': 'CSC',
    }

    for form_name, api_name in optional_cc_fields.items():
        if cc_data.get(form_name):
            params[api_name] = cc_data[form_name]

    return params


def process_sale(amount, cc_data, user, project):
    """Make a sale.

    Uses the following settings:
        PAYFLOW_LIVE_MODE
        PAYFLOW_LOGIN
        PAYFLOW_PARTNER_NAME

    :type user: accounts.models.CircusUser
    :type project: projects.models.Project

    :rtype: PayflowResponse
    """
    post_data = _sale_request_data(amount, cc_data, user, project)
    result = _post(post_data, user, project)
    logger.info("payflow payment %(approved)s: project=%(project)s "
                "user=%(user)s amount=%(amount)s result=%(result)r "
                "pnref=%(pnref)r",
                dict(
                approved=result.is_approved() and 'APPROVED' or 'DENIED',
                project=project.job_number,
                user=user.email,
                amount=amount,
                result=result.respmsg,
                pnref=result.pnref))
    return result


def _post(post_data, user, project):
    r = requests.post(endpoint(), data=post_data, verify=True,
                      timeout=REQUEST_TIMEOUT)

    try:
        # If that didn't return 200, something went very wrong.
        r.raise_for_status()
        results = _parse_response_page(r.content)
    except Exception, exc:
        _redact(post_data)
        import pprint
        msg = [
            u'Exception:',
            pprint.pformat(exc),
            '',
            u'Post data:',
            pprint.pformat(post_data),
            u'',
            u'Request/Response HAR:',
            har.request_and_response(r, include_post_body=False)
        ]
        msg = u'\n'.join(msg)
        subj = u'Payment API error: %s %s' % (project.job_number, user.email,)
        mail_admins(subj, msg)
        raise
    else:
        if not settings.PAYFLOW_LIVE_MODE and not results.result == APPROVED:
            logger.debug("payflow fail: %s", results)
            logger.debug(har.request_and_response(r, include_post_body=False))

    return results



class PayflowResponse(object):
    """
    For documentation see "Values Returned When ECHODATA is False" in the
    Payflow Link User's Guide.
    """
    def __init__(self, result, respmsg, pnref, authcode, avsdata):
        self.authcode = authcode
        self.avsdata = avsdata
        self.pnref = pnref
        self.respmsg = respmsg
        self.result = result


    def is_approved(self):
        # Docs say:
        #     Be sure to look at the response message for your transaction. Even
        #     if your result code is 0, your response message might say that the
        #     transaction has failed.
        # That may happen in the case of security code mismatch.
        return self.result == APPROVED and self.respmsg == "Approved"


    def __repr__(self):
        return '<%s.%s %s:%r>' % (
            self.__class__.__module__, self.__class__.__name__,
            self.result, self.respmsg)


def _parse_response_page(content):
    """
    :type content: unicode
    """
    # The intent of Payflow Link is to always have the CC# form submitted to
    # Payflow through the user's browser, even if that's a form we've prefilled
    # with hidden elements. Making sales through the backchannel API is supposed
    # to be only for the upgraded Pro version. We totally cheated, though, and
    # made the post directly. The downside is that now we're getting a response
    # meant for a browser, not a tidy API response.

    # keys are kwargs to PayflowResponse,
    # values are element names as found in HTML response content
    response_fields = {
        'authcode': 'AUTHCODE',
        'avsdata': 'AVSDATA',
        'pnref': 'PNREF',
        'respmsg': 'RESPMSG',
        'result': 'RESULT'
    }

    doc = PyQuery(content)
    args = {}

    # Hooray, we have some kind of structured data.
    if doc('input[name=RESULT]'):
        for arg_name, input_name in response_fields.iteritems():
            input_element = doc('input[name=%s]' % (input_name,))
            if len(input_element) != 1:
                raise ParseError(
                    "Error looking for field %r: Expected exactly 1 match, "
                    "got %s." % (input_name, len(input_element)))

            args[arg_name] = input_element.attr['value']
        else:
            # This one is a signed int, leave everything else as string.
            args['result'] = int(args['result'])

        response = PayflowResponse(**args)
    else:
        # Sadly, because we're cheating, we only get structured data on success
        # cases.  Other errors give us back blobs of HTML in several different
        # templates, making scraping unreliable.
        response = PayflowResponse(GENERAL_ERROR, "Transaction failed",
                                   None, None, 'XXN')

    return response
