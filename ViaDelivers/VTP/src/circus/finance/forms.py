# -*- coding: utf-8 -*-
from django import forms
from django.utils.translation import ugettext_lazy as _


class CreditCardForm(forms.Form):
    cardnum = forms.CharField(60, required=True, label=_("Card Number"))  # cc-number
    expdate = forms.CharField(7, required=True, label=_("Expiration Date"))  # cc-exp
    security_code = forms.CharField(4, required=False, label=_("Security Code"))  # cc-csc

    street = forms.CharField(60, required=True, label=_("Street Address"))  # street-address
    city = forms.CharField(32, required=True, label=_("City"))  # locality
    state = forms.CharField(20, required=False, label=_("State"))  # region
    zip = forms.CharField(10, required=True, label=_("Zip"))  # postal-code

    @classmethod
    def for_account(cls, account, *args, **kwargs):
        """
        :type account: people.models.Account
        """
        initial = {
            'street': account.billing_street,
            'city': account.billing_city,
            'zip': account.billing_postal_code,
            'state': account.billing_state
        }
        return cls(initial=initial, *args, **kwargs)

    # def add_error(self, field=None, message=None):
    #     """Add a (non-field-specific) error.
    #
    #     e.g. the transaction failed.
    #     """
    #     # Traditionally these are set by raising an exception from Form.clean,
    #     # but I'm not willing to have "charge the credit card" be a side-effect
    #     # of Form.clean.
    #     #
    #     # This is actually resetting the ALL_FIELDS errors, not adding to it,
    #     # but there's not anything else that sets it now.
    #     self.errors[forms.ALL_FIELDS] = self.error_class([message])
