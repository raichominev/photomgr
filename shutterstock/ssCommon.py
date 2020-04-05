import json
import os
import re

import psycopg2
import requests

CATEGORY_URL = "https://submit.shutterstock.com/api/content_editor/categories/photo"
NOTES_URL = "https://submit.shutterstock.com/api/content_editor/note_types"

DEFAULT_HEADERS = {'User-Agent' : 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:71.0) Gecko/20100101 Firefox/71.0'}

BASE_FOLDER = "C:\\Users\\user-pc2\\Desktop\\shutterstock"

FOLDER_PENDING = BASE_FOLDER + "\\" + "pending"
FOLDER_UNDER_REVIEW = BASE_FOLDER + "\\" + "underReview"
FOLDER_REVIEWED = BASE_FOLDER + "\\" + "submitted"
FOLDER_REJECTED = BASE_FOLDER + "\\" + "rejected"


cookie_dict = {}
categories = None
reasons = None


def ss_login():
    global categories
    global reasons

    cookies = os.environ['SS_AUTO_LOGIN_COOKIES']
    for c in cookies.split(';'):
        name,val = c.split('=',1)
        cookie_dict[name.strip()] = val.strip()

    ##############################
    # GET AUXILIARY  DATA LIST
    response = requests.get(CATEGORY_URL, cookies=cookie_dict, headers=DEFAULT_HEADERS)
    print('Login response:' + str(response))
    print(str(response.content))
    category_json = response.json()
    categories = dict((ct['cat_id'],ct) for ct in category_json['data'])

    # print(json.dumps(categories))

    response = requests.get(NOTES_URL, cookies=cookie_dict, headers=DEFAULT_HEADERS)
    reasons_json = response.json()
    reasons = dict((ct['id'],ct['name']) for ct in reasons_json['data'])

    # print(json.dumps(reasons))


def connect_database():
    return psycopg2.connect(os.environ["DATABASE_URL"])

titleMatch = r'T#.*#T'
catMatch = r'C#[0-9]{1,2}'
reworkMatch = r'[-]?R[!][0-9]{1,2}'

def get_stripped_file_name(filename):
    m = re.search(titleMatch, filename)
    if m:
        filename = filename [:m.start()] + filename[m.end():]

    while True:
        m = re.search(catMatch, filename)
        if not m: break
        filename = filename [:m.start()] + filename[m.end():]

    return filename.replace("..",".").replace("!","")

def is_rework(filename):
    m = re.search(reworkMatch, filename)
    if m:
        return True

    return False

def get_rework_original_file_name(filename):
    m = re.search(reworkMatch, filename)
    if m:
        filename = filename [:m.start()] + filename[m.end():]

    return get_stripped_file_name(filename)

def extract_data_from_file_name(filename):

    m = re.search(titleMatch, filename)
    title = filename[m.start()+2:m.end()-2] if m else None

    catList = re.findall(catMatch, filename)
    cat1 = str(int(catList[0][2:])) if len(catList) > 0 else None
    cat2 = str(int(catList[1][2:])) if len(catList) > 1 else None

    return {'title': title, 'cat1': cat1, 'cat2': cat2, 'location':None}
