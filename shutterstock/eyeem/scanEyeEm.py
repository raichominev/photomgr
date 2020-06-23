import json
import os

import requests

from shutterstock import ssCommon
from shutterstock.eyeem import eeCommon

PROFILE_SCAN_URL = 'https://www.eyeem.com/graphql'
#PHOTO_SCAN_URL = 'https://www.eyeem.com/p/'
PHOTO_SCAN_URL = 'https://www.eyeem.com/graphql'

if __name__ == "__main__":

    # if not 'SS_AUTO_UPLOAD_FIX_WAIT_TIME' in os.environ:
    #     os.environ['SS_AUTO_UPLOAD_FIX_WAIT_TIME'] = "15"

    if not "DATABASE_URL" in os.environ:
        os.environ["DATABASE_URL"] = "postgres://uhztcmpnkqyhop:c203bc824367be7762e38d1838b54448fe503f16fe34bb783d45a4a8bb370c00@ec2-34-200-116-132.compute-1.amazonaws.com:5432/d42v6sfcnns36v"

    db = ssCommon.connect_database()

    eeCommon.ee_login()

    resp = requests.get(PROFILE_SCAN_URL, {
        'operationName':'getUserPhotos',
        'variables':'{"nickname":"raicho","offset":0,"limit":300,"paginatableName":"photos","isBuyer":false}',
        'extensions':'{"persistedQuery":{"version":1,"sha256Hash":"b840124fa912be0e46c85bbde6db91cbeada1cf0576659ec65d474b0500d6ba4"}}'
    }, headers=eeCommon.DEFAULT_HEADERS, cookies=eeCommon.cookie_dict, )
    print(resp)
    # print(resp.json())

    print("Loaded most recent photos for review.")

    reviewCount = 0
    count = 0
    photoList = resp.json()
    print("Loaded:" + str(len(photoList['data']['user']['photos']['items'])))
    for photo in photoList['data']['user']['photos']['items']:

        cur = db.cursor()
        cur.execute("select ee_status, ee_title, ss_filename, ee_onsale from ss_reviewed where ee_id = %s ",(photo['id'],))
        db_record = cur.fetchone()

        if db_record is None:
            raise Exception('Eyeem image with id:' + photo['id'] + ' not found in database!')

        if db_record[0] in ('accepted', 'rejected', ):
            continue

        # resp = requests.get(PHOTO_SCAN_URL + photo['id'], headers=eeCommon.DEFAULT_HEADERS, cookies=eeCommon.cookie_dict, )
        # print(resp)
        #
        # content_data = str(resp.content)
        # idx = content_data.index("window.__APOLLO_STATE__ = ")
        # if idx == -1:
        #     raise Exception('Login unsuccessful')
        #
        # endidx = content_data.index('window.eyeconfig = ',idx)
        #
        # #url_encoded_data = content_data[idx+29: endidx]
        # #x = urllib.parse.unquote(url_encoded_data)
        # x = content_data[idx+26: endidx].strip()[:-1]
        # print(x)
        # #x = x.replace("\\'", "'")
        # json_data = json.loads(x)
        #
        # eeTitle = json_data['$Photo:'+photo['id']+'.eyevision']['headline']
        # eeKeywords = ','.join(json_data['$Photo:'+photo['id']+'.eyevision']['tags']['json'])

        resp = requests.get(PHOTO_SCAN_URL, {
            'operationName':'getPhoto',
            'variables':'{"photoId":"'+photo['id']+'","isPhotographer":true}',
            'extensions':'{"persistedQuery":{"version":1,"sha256Hash":"0462347aa1ff3e3cb6e892f7993cf10f4a8c48188da335e46b94246ae6907af0"}}'
        }, headers=eeCommon.DEFAULT_HEADERS, cookies=eeCommon.cookie_dict, )
        print(resp)
        photo_data = resp.json()
        photo_data = photo_data['data']['photo']

        # not selected: market status : 5, ['market']['reviewStatus']: 2
        # market: ['marketStatus'] : 3, ['partnerStatus'] : null
        # partner: ['marketStatus'] : 3, ['partnerStatus']['premium' : SELECTED

        status = db_record[0]
        onsale = db_record[3]
        if photo_data['market']['reviewStatus'] == 2:
            status = 'accepted'

            # todo: track status for permanently editorial

            if photo_data['market']['status'] == 5:
                status = 'rejected'
            if photo_data['market']['status'] == 2:
                status = 'releaseWait'
                onsale = 'editorial'
            elif photo_data['market']['status'] == 3 and photo_data['partnerStatus'] is None:
                onsale = 'market'
            elif photo_data['market']['status'] == 3 and photo_data['partnerStatus']['premium'] == 'SELECTED':
                onsale = 'partner'
            else:
                onsale = 'undefined'

            if status != db_record[0] or onsale != db_record[3]:
                print("Photo reviewed! [" + status.upper() + "] Id:" + photo['id'] + "-"+str(db_record[1])+ ":"+ str(db_record[2]))
                reviewCount +=1

        eeTitle = photo_data['eyevision']['headline']
        eeKeywords = ','.join(photo_data['eyevision']['tags'])

        if len(eeTitle.split()) >= 5:
            ee_level = 'good'
        else:
            ee_level = 'attn'

        cur = db.cursor()
        cur.execute("update ss_reviewed set ee_review_date = now(),"
                    " ee_ai_title = %s, ee_ai_keywords = %s, ee_status = %s, ee_onsale = %s, ee_level = %s where ee_id = %s " , (
                        eeTitle,
                        eeKeywords,
                        status,
                        onsale,
                        ee_level,
                        photo['id'],
                    ))

        db.commit()
        count += 1

    print(str(count-reviewCount) + ' photos in review. ' + str(reviewCount) + ' photos reviewed.')