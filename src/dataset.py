from html.parser import HTMLParser
from bs4 import BeautifulSoup
import re
import time
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
import os
from tqdm.notebook import tqdm
import pickle
import getpass
import requests
import numpy as np

class FacebookFriendData:
    
    def __init__(self, user:str, pwd:str = None, manual_login:bool = False):
        ###----- Selenium Webdriver setting -------------###
        chrome_options = webdriver.ChromeOptions()
        prefs = {"profile.default_content_setting_values.notifications": 2}
        chrome_options.add_experimental_option("prefs", prefs)
        self.driver = webdriver.Chrome(options=chrome_options)
        self.scroll_pause_time = 2
        ### ----------------------------------------------###
        self.user = user
        self.pwd = pwd
        self.manual_login = manual_login
        
    def download(self) -> dict:
        """ Download the friend's network from facebook using Selenium.
        
        Step 1: Stores the url of all friends into 'data/friends_url.pickle'
        Step 2: Open each url and stores facebook_id of all matual friend stores into dict
        Step 3: Save the dictionary into 'data/friends_network.pickle'
        Step 4: Fatch the attributes for all friends and store them into 'data/more_info.pickle' 
        
        Returns
        -------
        friends_network: type is dict
        """
        driver = self.driver
        scroll_pause_time = self.scroll_pause_time 
        manual_login = self.manual_login
        my_url = 'http://www.facebook.com/' + self.user + '/friends'
        
        if manual_login:
            driver = self.driver
            driver.get(my_url)#('http://www.facebook.com/')
            print("Have you logged in to the facebook account? (Y/N)")
            time.sleep(5)
            response = input()
            while response != 'Y':
                response = input()
        else: 
            self.login()
        friends_url = self.getFriendsURL(my_url, path='data/friends_url.pickle') #path to store the data
        friends_network = self.getFriendsNetwork(friends_url, path='data/friends_network.pickle')
        more_info = self.get_more_info(path='data/more_info.pickle')
        return "Data has been Stored in the directory '/data'"
    
    def login(self):
        """Run when manual login is False"""
        user = self.user
        pwd = self.pwd
        driver = self.driver
        try:
            driver.get('http://www.facebook.com/')
            # authenticate to facebook account
            elem = driver.find_element_by_id("email")
            elem.send_keys(user)
            elem = driver.find_element_by_id("pass")
            elem.send_keys(pwd)
            elem.send_keys(Keys.RETURN)
            time.sleep(5)
            print("Successfully logged in Facebook!")
        except Exception as e:
            print(e)
        
    def getFriendsURL(self, my_url, path=None):
        """ Retrieve friend's facebook url """
        if os.path.isfile(path):
            with open(path, 'rb') as f:
                friends_url = pickle.load(f)
            print('Loaded {} friends from existing file..'.format(len(friends_url)))
            return friends_url
        friends_page = self.get_fb_page(my_url)
        parser = MyHTMLParser()
        parser.feed(friends_page)
        friends_url = set(parser.urls)
        print('Found {} friends, saving it...'.format(len(friends_url)))
        with open(path, 'wb') as f:
            pickle.dump(friends_url, f)
        return friends_url
    
    def get_fb_page(self, url):
        """ Fetch the webpage source code """
        driver = self.driver
        scroll_pause_time = self.scroll_pause_time 
        driver.get(url)
        last_height = driver.execute_script("return document.body.scrollHeight") # Get scroll height

        while True:
            # Scroll down to bottom
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            # Wait to load page
            time.sleep(scroll_pause_time)
            # Calculate new scroll height and compare with last scroll height
            new_height = driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height
        html_source = driver.page_source
        return html_source

    def getFriendsNetwork(self, friends_url, path=None):
        """ Retrieve facebook friend's network using friend's facebook page url"""
        username = self.user
        friend_network = {}
        
        if os.path.isfile(path):
            with open(path, 'rb') as f:
                friend_network = pickle.load(f)
            print('Loaded existing network, found {} nodes.'.format(len(friend_network.keys())))

        count = 1
        for url in tqdm(friends_url):
            if count % 100 == 0:
                print ("Too many queries, pause for a while...")
                time.sleep(1800)

            friend_username = self.find_friend_from_url(url)
            if friend_username in friend_network.keys() and len(friend_network[friend_username]) > 1:
                continue

            friend_network[friend_username] = [username]
            
            mutual_url = 'https://www.facebook.com/{}/friends_mutual'.format(friend_username)
            mutual_page = self.get_fb_page(mutual_url)
            parser = MyHTMLParser()
            parser.urls = []
            parser.feed(mutual_page)
            mutual_friends_urls = set(parser.urls)
            
            #print(friend_username, 'No. of matual friends: ', len(mutual_friends_urls))
            
            for mutual_url in mutual_friends_urls:
                mutual_friend = self.find_friend_from_url(mutual_url)
                friend_network[friend_username].append(mutual_friend)
            
            with open(path, 'wb') as f:
                pickle.dump(friend_network, f)

            time.sleep(5)
            count += 1
        print('Nodes added into the network: ',len(friend_network.keys()), ' Pending: ',len(friends_url) - len(friend_network.keys()))
        return friend_network
        
    def find_friend_from_url(self, url):
        """Fetch the friend's facebook id from url"""
        if re.search('com\/profile.php\?id=\d+\&', url) is not None:
            m = re.search('com\/profile.php\?id=(\d+)\&', url)
            friend_id = m.group(1)
        else:
            m = re.search('com\/(.*)\?', url)
            friend_id = m.group(1)
        return friend_id
    
    
    def get_more_info(self, path='data/more_info.pickle'):
        """Fatch the attributes"""
        driver = self.driver
        links_info = {"Work and education":[("pagelet_eduwork","education_and_work")], 
              "Places":[("pagelet_hometown","hometown")], 
              "Contact and basic info":[("pagelet_contact","contact"), ("pagelet_basic","basic_info")], 
              "Family and relationships":[("pagelet_relationships","relationships")], 
              "Details":[("pagelet_bio","bio"),("pagelet_nicknames","nicknames"),("pagelet_quotes","quotes"),("pagelet_blood_donations","blood_donations")]}
        with open('data/friends_url.pickle', 'rb') as f:
            friends_url = pickle.load(f)
            more_info = {}

            if os.path.isfile(path):
                with open(path, 'rb') as f:
                    more_info = pickle.load(f)

            count = 1
            for url in tqdm(friends_url, desc="Fatching attributes......"):
                if count % 11 == 0:
                    print ("Too many queries, pause for a while...")
                    time.sleep(3400) # 45 minutes
                friend_info = {}
                friend_id = self.find_friend_from_url(url)
                if friend_id in more_info.keys():
                    continue
                friend_aboul_url = 'https://www.facebook.com/{}/followers'.format(friend_id)
                driver.get(friend_aboul_url)
                for elem_name in ["Followers", "Following"]:
                    try:
                        element =  driver.find_element_by_name(elem_name)
                        friend_info[elem_name.lower()] = element.text[9:]
                    except:
                        friend_info[elem_name.lower()] = np.NaN
                
                friend_aboul_url = 'https://www.facebook.com/{}/about'.format(friend_id)
                driver.get(friend_aboul_url)
                friend_info['name'] = driver.title
                for link_text, elem_info in links_info.items():
                    try:
                        link = driver.find_element_by_partial_link_text(link_text)
                        driver.get(link.get_attribute('href'))
                    except:
                        pass
                    for elem_id, elem_name in elem_info:
                        try:
                            if elem_id == "pagelet_eduwork" and friend_id == "bilalansari.000":
                                elem_id = "pagelet_edit_eduwork"
                            element = driver.find_element_by_id(elem_id) 
                            friend_info[elem_name] = element.text
                        except Exception as e:
                            friend_info[elem_name] = np.NaN
                try:
                    link = driver.find_element_by_partial_link_text("Life events")
                    driver.get(link.get_attribute('href'))
                    element = driver.find_element_by_class_name('_4qm1')
                    friend_info['life_events'] = element.text
                except Exception as e:
                    friend_info['life_events'] = np.NaN

                more_info[friend_id] = friend_info
                with open(path, 'wb') as f:
                    pickle.dump(more_info, f)
                time.sleep(60)
                count += 1
            return more_info

    
    def get_more_info_v_0(self, file_path = "data/friends_url.pickle"):
        with open(file_path,'rb') as f:
            urls = pickle.load(f)
            res = {}
            for url in tqdm(urls):
                friend_id = self.find_friend_from_url(url)
                if friend_id in res:
                    continue
                url = 'https://www.facebook.com/'+friend_id+'/about'
                html_content = requests.get(url).text
                soup = BeautifulSoup(html_content,'html.parser')
                divs = soup.find_all('div', class_='_4qm1')
                friend_info = {}
                friend_info['name'] = soup.title.text.replace(' | Facebook','')
                for sec_ru, sec_en  in [('Работа','work'), ('Образование','education'), ('Город проживания и родной город','hometown')]:
                    sec = list(filter(lambda div: str(div.findChildren()).find(sec_ru) != -1 ,divs))
                    if sec:
                        lis = sec[0].find_all('li')
                        sec_info = ['$$'.join(map(lambda a: a.text,filter(lambda a: a.text, ls.find_all('a')))) for ls in lis]
                        friend_info[sec_en] = sec_info
                    else:
                        friend_info[sec_en] = 'None'
                res[friend_id] = friend_info
            
            path = "data/more_info.pickle" 
            with open(path, 'wb') as f:
                pickle.dump(res, f)

class MyHTMLParser(HTMLParser):
    urls = []
    def error(self, message):
        print("Error, while parsing the HTML source code..")

    def handle_starttag(self, tag, attrs):
        # Only parse the 'anchor' tag.
        if tag == "a":
            # Check the list of defined attributes.
            for name, value in attrs:
                # If href is defined, print it.
                if name == "href":
                    if re.search('\?href|&href|hc_loca|\?fref', value) is not None:
                        if re.search('.com/pages', value) is None:
                            self.urls.append(value)
                            
                            
                            