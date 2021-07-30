import os
from django.test import TestCase
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By
# create a new Firefox session
#driver = webdriver.Firefox(executable_path=r'your\path\geckodriver.exe')


class TestSearchText(TestCase):
    @classmethod
    def setUpClass(inst):
        # create a new Firefox session
        dir = os.path.dirname(__file__)
        chrome_driver_path = dir + "\chromedriver.exe"

        # create a new Chrome session
        inst.driver = webdriver.Chrome(chrome_driver_path)
        inst.driver.implicitly_wait(30)
        inst.driver.maximize_window()
        # navigate to the application home page
        inst.driver.get("http://www.google.com/")

    def test_search_box(self):
        # check search box exists on Home page
        self.assertTrue(self.is_element_present(By.NAME, "q"))

    def test_language_settings(self):
        # check language options on Home page
        self.assertTrue(self.is_element_present(By.ID, "_eEe"))

    def test_images_link(self):
        # check images link on Home page
        images_link = self.driver.find_element_by_link_text("Images")
        images_link.click()
        # check search field exists on Images page
        self.assertTrue(self.is_element_present(By.NAME, "q"))
        self.search_field = self.driver.find_element_by_name("q")
        # enter search keyword and submit
        self.search_field.send_keys("Selenium Webdriver framework architecture diagram")
        self.search_field.submit()

    @classmethod
    def tearDownClass(inst):
        # close the browser window
        inst.driver.quit()

    def is_element_present(self, how, what):
        """
        Helper method to confirm the presence of an element on page
        :params how: By locator type
        :params what: locator value
        """
        try:
            self.driver.find_element(by=how, value=what)
        except NoSuchElementException:
            return False
        return True