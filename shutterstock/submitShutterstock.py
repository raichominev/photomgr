import json
import os
import sys
import traceback
from datetime import datetime
import random
import requests
import time
from shutterstock import ssCommon

TO_SUBMIT_URL = "https://submit.shutterstock.com/api/content_editor/photo"
SUBMIT_URL = "https://submit.shutterstock.com/api/content_editor/submit"


if __name__ == "__main__":

    try:
        # allow submit every fourth hour
        if datetime.now().hour % int(os.environ['SUBMIT_EVERY_HOURS']) != 0:
            print('Not the time - sleeping')
            exit(0)

        min = random.randint(0,int(os.environ['SUBMIT_RANDOM_DELAY_MIN']))
        print('Sleeping '+ str(min) + ' min...')
        time.sleep(min * 60)
        print('Waking...')

        db = ssCommon.connect_database()
        ssCommon.ss_login()

        ####################################################################
        # get list of waiting files
        response = requests.get(
            TO_SUBMIT_URL,
            params={'status': 'edit', 'xhr_id': '1', 'page_number':'1', 'per_page': '100', 'order':'oldest'},
            cookies=ssCommon.cookie_dict,
            headers=ssCommon.DEFAULT_HEADERS
        )
        print(response.url)
        print(response)
        json_response = response.json()

        ####################################################################
        # get list of waiting files

        for picture in json_response['data']:

            #if picture valid =

            print("Evaluating " + picture['original_filename'] +  ":" + str(len(picture['categories'])) + ":" + str(len(picture['keywords'])) +':' + (str(len(picture['description'])) if 'description' in picture else 'NoDesc'))
            if len(picture['categories']) >= 1 and len(picture['keywords']) > 20 and 'description' in picture and len(picture['description']) > 20:
                print('Submitting picture ' + picture['original_filename'] + ':'+ picture['description'])
                submit_payload = '{"media":[{"media_type":"photo","media_id":"'+picture['id']+'"}],"keywords_not_to_spellcheck":[],"skip_spellcheck":"false"}'
                # print(submit_payload)
                response = requests.post(
                    SUBMIT_URL,
                    json = json.loads(submit_payload),
                    cookies=ssCommon.cookie_dict,
                    headers=ssCommon.DEFAULT_HEADERS
                )
                print(response)

                response_data = response.json()
                print(response_data)
                success = False
                for x in response_data["data"]["success"]:
                    if x['upload_id'] == picture['id']:
                        # great success
                        cur = db.cursor()
                        cur.execute("update ss_reviewed set state = 20, date_submitted = now(), "
                                    "ss_media_id = %s, ss_title = %s, ss_keywords = %s, ss_cat1 = %s, ss_cat2 = %s, ss_location = %s"
                                    " where ss_filename = %s ",
                                    (
                                        x["media_id"],
                                        picture['description'],
                                        ','.join(picture['keywords']),
                                        picture['categories'][0] if len(picture['categories']) > 0 else None,
                                        picture['categories'][1] if len(picture['categories']) > 1 else None,
                                        json.dumps(picture['location']),
                                        picture['original_filename'],)
                                    )
                        db.commit()
                        success = True

                #todo: record last error

                # Allow only one successful picture submit per run
                if success:
                    break
    except:
        exception_data = ''.join(traceback.format_exception(*sys.exc_info()))
        ssCommon.handleException(exception_data,"submitShutterstock")
        raise

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
