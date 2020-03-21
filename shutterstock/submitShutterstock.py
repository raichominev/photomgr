
#
# {"data":
#     {"item_errors":
#         [
#             {"upload_id": "U2003656102",
#              "validation_errors":
#                  {
#                      "status": "incomplete",
#                      "summary": [{"TITLE_ERROR": true}],
#                      "details": {
#                          "keywords":
#                              {"approved": ["animal", "beach", "brown", "calm", "canine", "closeup", "cute", "dirty",
#                                            "dog", "funny", "fur", "ground", "homeless", "lie", "little", "mammal",
#                                            "nature", "no person", "one", "outdoor", "outdoors", "pet", "portrait",
#                                            "puppy", "rest", "sand", "shade", "sleep", "summer", "sunny", "vacation",
#                                            "white"],
#                               "errors": {"COMMON_WORD": [], "ALTERNATE_TENSE": [], "CONTAINS_TOO_SHORT_KEYWORDS": [],
#                                          "REPEATED_WORDS_IN_PHRASES": [], "EMAIL_ADDRESS": [],
#                                          "KEYWORD_PHRASE_TOO_LONG": [], "CONTAINS_SUSPICIOUS_KEYWORDS": [],
#                                          "CONTAINS_INAPPROPRIATE_KEYWORDS": [],
#                                          "CONTAINS_SPAM_KEYWORDS": ["beach", "dog", "nature", "summer"],
#                                          "CONTAINS_FLAGGED_KEYWORDS": [], "SPELL_CHECK": []}, "ignoredErrors": {},
#                               "type": "keywordValidation", "hard_validation_failure": false},
#                          "title": {"original": "", "errors": {"EMPTY_TITLE": true}, "type": "titleValidation",
#                                    "hard_validation_failure": true, "message": "Please include a description."}}}}],
#         "success": [],
#         "first_submit_check": {"code": "SUBMIT_ALLOWED", "message": "code: SUBMIT_ALLOWED", "original_code": ""}
#     }
# }
#
# {"data":
#     {
#         "item_errors": [],
#         "success":
#             [{"upload_id": "U2003656102", "media_id": 1678515331, "media_type": "photo"}],
#         "first_submit_check": {"code": "SUBMIT_ALLOWED", "message": "code: SUBMIT_ALLOWED", "original_code": ""}
#     }
# }
#
import json
import os

import psycopg2
import requests

LOGIN_COOKIES_DB_FILE = "login.txt"

CATEGORY_URL = "https://submit.shutterstock.com/api/content_editor/categories/photo"
NOTES_URL = "https://submit.shutterstock.com/api/content_editor/note_types"

DEFAULT_HEADERS = {'User-Agent' : 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:71.0) Gecko/20100101 Firefox/71.0'}

cookie_dict = {}
categories = None
reasons = None

def connect_database():
    return psycopg2.connect(os.environ["DATABASE_URL"])

def ini():
    global categories
    global reasons

    with open(LOGIN_COOKIES_DB_FILE) as f:
        cookies = f.readline()
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



if __name__ == "__main__":
    db = connect_database()
    ini()

    for x in resp["data"]["success"]:
        x["media_id"]