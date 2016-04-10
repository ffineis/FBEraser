#!/usr/bin/env python
from __future__ import print_function
from selenium import webdriver
from bs4 import BeautifulSoup
from argparse import ArgumentParser
from time import sleep
import getpass
import sys
import time; import datetime
import re
if sys.version[0] == '3': raw_input=input   # for python 2/3 cross compatibility

class Eraser(object):
    """
    Eraser class to remove Facebook content
    Set up, log in, go to activity page, then repeat delete
    If having trouble, use scroll down method or increase wait time
    Don't forget to quit in the end
    """

    def __init__(self, email, password, erase_date, wait=1):
        """
        Set up the eraser
        :return: Null
        """
        self.driver = webdriver.Firefox()
        self.email = email
        self.password = password
        self.erase_date = erase_date        # date on/after which all posts will be removed (date is inclusive)
        self.profile_name = None            # this will end up being the facebook user name
        self.count = 0                      # counter of number of elements deleted
        self.wait = wait

    def quit(self):
        """
        Quit the program (close out the browser)
        :return: Null
        """
        self.driver.quit()

    def login(self):
        """
        Log in to Facebook, set profile name
        :return: Null
        """
        self.driver.get('https://www.facebook.com/login/')
        email_element = self.driver.find_element_by_id('email')
        email_element.send_keys(self.email)
        password_element = self.driver.find_element_by_id('pass')
        password_element.send_keys(self.password)
        password_element.submit()

        soup = BeautifulSoup(self.driver.page_source)
        profile_link = soup.find('a', {'title': 'Profile'})
        self.profile_name = profile_link.get('href')[25:]    # link appears as http://www.facebook.com/PROFILE

    def go_to_activity_page(self):
        """
        Go to the activity page and prepare to start deleting
        :return: Null
        """
        if not self.profile_name:
            # the user hasn't logged in properly
            sys.exit(-2)
        # go to the activity page (filter by 'Your Posts')
        activity_link = 'https://www.facebook.com/' + self.profile_name + '/allactivity?privacy_source=activity_log&log_filter=cluster_11'
        self.driver.get(activity_link)
        sleep(self.wait)

    def scroll_down(self):
        """
        Executes JS to scroll down on page.
        Use if having trouble seeing elements
        :return:
        """
        self.driver.execute_script('window.scrollTo(0, document.body.scrollHeight);')
        sleep(self.wait)


    def determine_post_erasing(self):
        now = datetime.datetime(*time.localtime()[:3])
        this_year = now.year
        soup = BeautifulSoup(self.driver.page_source)
        time_elt = soup.find('span', {'class': 'timestampContent'})
        post_ts = time_elt.string
        d = None

        # Case 1: posts are fresh and are labeled e.g. '10 hrs' so the date is either today or yesterday.
        #         Either way, just treat this as today.
        for t in post_ts.split():
            if(t in ["secs", "mins", "hrs", "Now"]):
                d = now

        # Case 2: datetime timestamp pretty fresh, but no year, e.g. 'March 21 at 10:54pm'
        if len(re.findall('at', post_ts))==1:
            post_ts = re.sub("at ", "", post_ts)
            d = datetime.datetime.strptime(post_ts, "%B %d %H:%M%p")
            d.replace(year = this_year)

        # Case 3: datetime timestamp has no time associated with it, but is this year e.g. 'February 13' (2016 implied)
        if d is None and len(re.findall(',', post_ts))==0:
            d = datetime.datetime.strptime(post_ts, "%B %d")
            d.replace(year = this_year)

        # Case 4: datetime timestamp is old, e.g. 'February 13, 2012'
        if d is None and len(re.findall(',', post_ts))==1:
            d = datetime.datetime.strptime(post_ts, "%B %d, %Y")

        if d is None:
            print("\t...Date of post not found.")
            return(-1)

        if(d <= self.erase_date):
            print ("\t... Date of post: {:%B %d %Y}. It will be deleted.".format(d.date()))
            return(1)
        else:
            print ("\t... Date of post: {:%B %d %Y}. It will NOT be deleted.".format(d.date()))
            return(-1)


    def delete_element(self):
        """
        Find the first available element and delete it
        :return: Null
        """

        # click hidden from timeline so the delete button shows up
        soup = BeautifulSoup(self.driver.page_source)
        # Priority: highlights, allowed, hidden
        menu_button = soup.find('a', {'aria-label': 'Highlighted on Timeline'})
        if menu_button is None:
            menu_button = soup.find('a', {'aria-label': 'Allowed on Timeline'})
        if menu_button is None:
            menu_button = soup.find('a', {'aria-label': 'Hidden from Timeline'})
        if menu_button is None:
            menu_button = soup.find('a', {'aria-label': 'Shown on Timeline'})
        if menu_button is None:
            menu_button = soup.find('a', {'aria-label': 'Story options'})

        menu_element = self.driver.find_element_by_id(menu_button.get('id'))
        menu_element.click()
        sleep(self.wait)

        # now that the delete button comes up, find the delete link and click
        # sometimes it takes more than one click to get the delete button to pop up
        if menu_button is not None:
            i = 0
            while i < 3:
                try:
                    self.driver.find_element_by_link_text('Delete').click()
                    break
                except:
                    print ('[*] Clicking menu again')
                    menu_element.click()
                    i += 1
        sleep(self.wait)

        # click the confirm button, increment counter and display success
        self.driver.find_element_by_class_name('layerConfirm').click()
        self.count += 1
        print ('[+] Element Deleted ({count} in total)'.format(count=self.count))
        sleep(self.wait)


if __name__ == '__main__':
    """
    Main section of script
    """
    # set up the command line argument parser
    parser = ArgumentParser(description='Delete your Facebook activity.  Requires Firefox')
    parser.add_argument('--wait', type=float, default=1, help='Explicit wait time between page loads (default 1 second)')
    args = parser.parse_args()

    # execute the script
    email = raw_input("Please enter Facebook login email: ")
    password = getpass.getpass()
    # Get erase_date
    input_date = raw_input("Please enter the date marking first day of post removal (later posts will be removed too): ")
    erase_date = None
    while erase_date is None:
        try:
            erase_date = datetime.datetime.strptime(input_date, "%m/%d/%Y")
        except ValueError as e:
            print ("Error in date input. Date must be formatted mm/dd/yyyy")
            input_date = raw_input()
    eraser = Eraser(email=email, password=password, wait=args.wait, erase_date = erase_date)
    eraser.login()
    eraser.go_to_activity_page()
    # track failures
    fail_count = 0
    while True:
        if fail_count >= 4:
            print ('[*] Scrolling down')
            eraser.scroll_down()
            fail_count = 0
            sleep(5)
        try:
            print ('[*] Determining post date')
            del_me = eraser.determine_post_erasing()
            sleep(1)

            if del_me == 1:
                print ('[*] Trying to delete element')
                eraser.delete_element()
                fail_count = 0
            # If the post's date couldn't be determined or is too recent, increase fail_count.
            else:
                print ('[-] Post is later than erase_date or could not be determined.')
                fail_count += 1

        except (Exception, ) as e:
            print ('[-] Problem finding element')
            fail_count += 1
            sleep(2)
