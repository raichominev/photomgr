import json
import os

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
    category_json = response.json()
    categories = dict((ct['cat_id'],ct) for ct in category_json['data'])

    print(json.dumps(categories))

    response = requests.get(NOTES_URL, cookies=cookie_dict, headers=DEFAULT_HEADERS)
    reasons_json = response.json()
    reasons = dict((ct['id'],ct['name']) for ct in reasons_json['data'])

    print(json.dumps(reasons))


def connect_database():
    return psycopg2.connect(os.environ["DATABASE_URL"])
