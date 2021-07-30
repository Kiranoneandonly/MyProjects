import unittest
from selenium import webdriver
import requests



username = "archana.mittal77@gmail.com"
authkey = "kirankumar"

api_session = requests.Session()
api_session.auth = (username, authkey)
test_result = None

caps = {}
caps['browserName'] = 'Chrome'
caps['version'] = '60x64'
caps['platform'] = 'Windows 10'
caps['screenResolution'] = '1366x768'

driver = webdriver.Remote(
    desired_capabilities=caps,
    command_executor="http://%s:%s@hub.crossbrowsertesting.com:80/wd/hub" % (username, authkey)
)

driver.implicitly_wait(20)


driver.get('http://crossbrowsertesting.github.io/selenium_example_page.html')
assert "Selenium Test Example Page", driver.title
test_result = 'pass'
driver.quit()


