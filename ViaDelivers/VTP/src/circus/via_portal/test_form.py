# -*- coding: utf-8 -*-
from django.test import TestCase
from via_portal.forms import EstimateForm


class TestEstimateForm(TestCase):
    def test_no_categories(self):
        # This is the boring case, where ServiceTypes don't have categories
        # assigned yet, but it should still work.
        form = EstimateForm()
        field = form.fields['services']
        choices = field.widget.choices

        # choices should not be a flat list of tuples, but into named groups
        # of choices. ServiceType.category = None group is named "Uncategorized"
        group_0 = choices[0]
        self.assertEqual("Setup Tasks", group_0[0])
        self.assertIsInstance(group_0[1], list)
        self.assertIsInstance(group_0[1][0], tuple)
