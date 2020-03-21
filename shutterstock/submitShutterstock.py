{"data":
    {"item_errors":
        [
            {"upload_id": "U2003656102",
             "validation_errors":
                 {
                     "status": "incomplete",
                     "summary": [{"TITLE_ERROR": true}],
                     "details": {
                         "keywords":
                             {"approved": ["animal", "beach", "brown", "calm", "canine", "closeup", "cute", "dirty",
                                           "dog", "funny", "fur", "ground", "homeless", "lie", "little", "mammal",
                                           "nature", "no person", "one", "outdoor", "outdoors", "pet", "portrait",
                                           "puppy", "rest", "sand", "shade", "sleep", "summer", "sunny", "vacation",
                                           "white"],
                              "errors": {"COMMON_WORD": [], "ALTERNATE_TENSE": [], "CONTAINS_TOO_SHORT_KEYWORDS": [],
                                         "REPEATED_WORDS_IN_PHRASES": [], "EMAIL_ADDRESS": [],
                                         "KEYWORD_PHRASE_TOO_LONG": [], "CONTAINS_SUSPICIOUS_KEYWORDS": [],
                                         "CONTAINS_INAPPROPRIATE_KEYWORDS": [],
                                         "CONTAINS_SPAM_KEYWORDS": ["beach", "dog", "nature", "summer"],
                                         "CONTAINS_FLAGGED_KEYWORDS": [], "SPELL_CHECK": []}, "ignoredErrors": {},
                              "type": "keywordValidation", "hard_validation_failure": false},
                         "title": {"original": "", "errors": {"EMPTY_TITLE": true}, "type": "titleValidation",
                                   "hard_validation_failure": true, "message": "Please include a description."}}}}],
        "success": [],
        "first_submit_check": {"code": "SUBMIT_ALLOWED", "message": "code: SUBMIT_ALLOWED", "original_code": ""}
    }
}

{"data":
    {
        "item_errors": [],
        "success":
            [{"upload_id": "U2003656102", "media_id": 1678515331, "media_type": "photo"}],
        "first_submit_check": {"code": "SUBMIT_ALLOWED", "message": "code: SUBMIT_ALLOWED", "original_code": ""}
    }
}

for x in resp["data"]["success"]:
    x["media_id"]