# import unittest
# import pytest
#
# class TestStringMethods(unittest.TestCase):
#
#     def test_upper(self):
#         self.assertEqual('foo'.upper(), 'FOO')
#
#     def test_isupper(self):
#         self.assertTrue('FOO'.isupper())
#         self.assertFalse('Foo'.isupper())
#
#     def test_split(self):
#         s = 'hello world'
#         self.assertEqual(s.split(), ['hello', 'world'])
#         # check that s.split fails when the separator is not a string
#         with self.assertRaises(TypeError):
#             s.split(2)

def mul(a,b):
    """
    Testing this function

    >>> mul(3,4)
    12
    >>> mul('b', 4)
    'bbbb'
    >>> mul(2,5)
    10
    """
    return a*b

