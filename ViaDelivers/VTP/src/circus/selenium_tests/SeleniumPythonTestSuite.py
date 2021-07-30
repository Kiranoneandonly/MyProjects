import os
import unittest
import HTMLTestRunner
from test_auto_selenium import TestSearchText

# get and load all tests from SearchText and HomePageTest class
search_text = unittest.TestLoader().loadTestsFromTestCase(TestSearchText)


# create a test suite combining search_text and home_page_test
test_suite = unittest.TestSuite([search_text])

# run the suite
unittest.TextTestRunner(verbosity=2).run(test_suite)

# open the report file
dir = os.path.dirname(__file__)
report_path = dir + "\SeleniumPythonTestSummary.html"
outfile = open(report_path, "w")

# configure HTMLTestRunner options
runner = HTMLTestRunner.HTMLTestRunner(stream=outfile,title='Test Report', description='Acceptance Tests')

# run the suite using HTMLTestRunner
runner.run(test_suite)