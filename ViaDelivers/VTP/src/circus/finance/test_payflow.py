# -*- coding: utf-8 -*-
import os
from unittest import TestCase
from finance.payflow import _parse_response_page, APPROVED


def sibpath(filename, *sibling):
    dirname = os.path.dirname(filename)
    return os.path.join(dirname, *sibling)


def testdata(filename):
    return sibpath(__file__, 'testdata', filename)



class TestParseResponsePage(TestCase):

    approved_filename = testdata('payflow_response.html')
    fail_filename = testdata('payflow_invalid_number.html')

    def test_parse_payflow_response_page(self):
        with open(self.approved_filename) as response_file:
            content = response_file.read()

            response = _parse_response_page(content)

        self.assertEqual(response.result, APPROVED)
        self.assertEqual(response.authcode, "009966")
        self.assertEqual(response.respmsg, "Approved")
        self.assertEqual(response.avsdata, "YYY")
        self.assertEqual(response.pnref, "EPFEA3A1B49B")
        # There's also a hostcode, but that's only for eChecks, which is out of
        # scope for now.


    def test_parse_payflow_failpage(self):
        with open(self.fail_filename) as response_file:
            content = response_file.read()

            response = _parse_response_page(content)

        self.assertNotEqual(response.result, APPROVED)
        self.assertNotEqual(response.respmsg, "Approved")
        self.assertFalse(response.pnref)
