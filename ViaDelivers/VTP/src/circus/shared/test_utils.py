# coding=utf-8
"""Test shared.utils."""
from django.test import TestCase

from shared.utils import remove_html_tags


class TestSharedUtils(TestCase):
    def setUp(self):
        pass

    def test_remove_html_tags_none(self):
        expected_string = None
        html_string = None
        remove_html_string = remove_html_tags(html_string)
        self.assertEqual(expected_string, remove_html_string)

    def test_remove_html_tags_html(self):
        expected_string = 'test'
        html_string = '<b>test</b>'
        remove_html_string = remove_html_tags(html_string)
        self.assertEqual(expected_string, remove_html_string)

    def test_remove_html_tags_html_multiple(self):
        expected_string = 'test this is a  test'
        html_string = '<b>test this is a <i>test</i></b>'
        remove_html_string = remove_html_tags(html_string)
        self.assertEqual(expected_string, remove_html_string)
