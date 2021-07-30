import os
from django.test import TestCase
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
# create a new Firefox session
#driver = webdriver.Firefox(executable_path=r'your\path\geckodriver.exe')


dir = os.path.dirname(__file__)
chrome_driver_path = dir + "\chromedriver.exe"
# firefox_driver_path = dir + "\geckodriver.exe"

# create a new Chrome session
# driver = webdriver.Chrome(chrome_driver_path)
driver = webdriver.Firefox()
driver.implicitly_wait(30)
driver.maximize_window()
driver.get("http://127.0.0.1:8000/accounts/login?next=/")
user_name = driver.find_element_by_name("username")
password = driver.find_element_by_name("password")
user_name.send_keys("ksai2@swiggy.com")
password.send_keys("test")
# self.driver.find_element_by_id("submit").click()
driver.find_element_by_class_name("btn-block").click()
driver.find_element_by_xpath("//a[@class='dropdown-toggle']").click()
driver.find_element_by_xpath("//a[@href='/accounts/profile/']").click()


driver.find_element_by_name("update_profile").click()
try:
    print "This is kiran"
    WebDriverWait(driver, 1).until(EC.alert_is_present(),
                                   'Timed out waiting for PA creation ' +
                                   'confirmation popup to appear.')
    print "This is kiran2"
    alert = driver.switch_to.alert
    alert.accept()
    print("alert accepted")
except TimeoutException:
    print("no alert")


# alert = driver.switch_to.alert
# wait = WebDriverWait(driver, 10)
# element = wait.until(EC.alert_is_present())
# print("Alert is: %s" % alert.accept())


# class TestSearchText(TestCase):
#     @classmethod
#     def setUpClass(inst):
#         # create a new Firefox session
#         dir = os.path.dirname(__file__)
#         chrome_driver_path = dir + "\chromedriver.exe"
#
#         # create a new Chrome session
#         inst.driver = webdriver.Chrome(chrome_driver_path)
#         inst.driver.implicitly_wait(30)
#         inst.driver.maximize_window()
#         # navigate to the application home page
#         # inst.driver.get("http://127.0.0.1:8000/accounts/login?next=/")
#
#     def test_login(self):
#         self.driver.get("http://127.0.0.1:8000/accounts/login?next=/")
#         user_name = self.driver.find_element_by_name("username")
#         password = self.driver.find_element_by_name("password")
#         user_name.send_keys("ksai2@swiggy.com")
#         password.send_keys("test")
#         # self.driver.find_element_by_id("submit").click()
#         self.driver.find_element_by_class_name("btn-block").click()
#         self.driver.find_element_by_xpath("//a[@class='dropdown-toggle']").click()
#         self.driver.find_element_by_xpath("//a[@href='/accounts/profile/']").click()
#
#         print "This is kiran"        self.driver.find_element_by_name("update_profile").click()
#
#         wait = WebDriverWait(self.driver, 10)
#         element = wait.until(EC.alert_is_present())
#         alert = self.driver.switch_to.alert()
#
#         print("Alert is: %s" % alert.accept())
#
#
#     @classmethod
#     def tearDownClass(inst):
#         # close the browser window
#         inst.driver.quit()
#         pass
#
#     def is_element_present(self, how, what):
#         """
#         Helper method to confirm the presence of an element on page
#         :params how: By locator type
#         :params what: locator value
#         """
#         try:
#             self.driver.find_element(by=how, value=what)
#         except NoSuchElementException:
#             return False
#         return True