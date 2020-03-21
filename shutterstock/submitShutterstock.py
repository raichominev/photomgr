import json
import os

import psycopg2
import requests

LOGIN_COOKIES_DB_FILE = "login.txt"

CATEGORY_URL = "https://submit.shutterstock.com/api/content_editor/categories/photo"
NOTES_URL = "https://submit.shutterstock.com/api/content_editor/note_types"

DEFAULT_HEADERS = {'User-Agent' : 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:71.0) Gecko/20100101 Firefox/71.0'}

TO_SUBMIT_URL = "https://submit.shutterstock.com/api/content_editor/photo"
SUBMIT_URL = "https://submit.shutterstock.com/api/content_editor/submit"

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

    ####################################################################
    # get list of waiting files
    response = requests.get(
        TO_SUBMIT_URL,
        params={'status': 'edit', 'xhr_id': '1', 'page_number':'1', 'per_page': '100', 'order':'oldest'},
        cookies=cookie_dict,
        headers=DEFAULT_HEADERS
    )
    print(response.url)
    print(response)
    json_response = response.json()

    ####################################################################
    # get list of waiting files

    for picture in json_response['data']:

        #if picture valid =
        if len(picture['categories']) > 1 and len(picture['keywords']) >= 20 and 'description' in picture and len(picture['description']) > 20:
            print('Submitting picture ' + picture['id'] + ':'+ picture['description'])
            submit_payload = '{"media":[{"media_type":"photo","media_id":"'+picture['id']+'"}],"keywords_not_to_spellcheck":[],"skip_spellcheck":"false"}'
            print(submit_payload)
            response = requests.post(
                SUBMIT_URL,
                json = json.loads(submit_payload),
                cookies=cookie_dict,
                headers=DEFAULT_HEADERS
            )
            print(response)

            response_data = response.json()
            print(response_data)
            for x in response_data["data"]["success"]:
                if x['upload_id'] == picture['id']:
                    # great success
                    cur = db.cursor()
                    cur.execute("update ss_reviewed set state = 2, date_submitted = now(), "
                                "ss_media_id = %s, ss_title = %s, ss_keywords = %s, ss_cat1 = %s, ss_cat2 = %s"
                                " where ss_filename = %s ",
                                (
                                    x["media_id"],
                                    picture['description'],
                                    ','.join(picture['keywords']),
                                    picture['categories'][0] if len(picture['categories']) > 0 else None,
                                    picture['categories'][1] if len(picture['categories']) > 1 else None,
                                    picture['original_filename'],)
                                )
                    db.commit()

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
