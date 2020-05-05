import json
import sys
import traceback
import urllib.parse
from datetime import datetime

import requests

from shutterstock import ssCommon
from shutterstock.adobe import adobeCommon

REVIEWED_URL = 'https://contributor.stock.adobe.com/bg/portfolio'
REJECTED_URL = 'https://contributor.stock.adobe.com/bg/uploads/rejected'

#'https://contributor.stock.adobe.com/bg/uploads/review'


def loadAdbodeImages(LOG, url):

    response = requests.get(
        url,
        params={'limit': '100', 'page':'1', "sort_by":'create_desc'},
        cookies=adobeCommon.cookie_dict,
        headers=adobeCommon.DEFAULT_HEADERS
    )
    print(response.url)
    #   print(response.content)

    content_data = str(response.content)
    idx = content_data.index(">window.__react_context__ =")
    if idx == -1:
        raise Exception('Login unsuccessful')

    endidx = content_data.index('";</script><script nonce="',idx)

    url_encoded_data = content_data[idx+29: endidx]
    x = urllib.parse.unquote(url_encoded_data)
    #print(x)
    x = x.replace("\\'", "'")
    json_data = json.loads(x)
    #print(json.dumps(json_data,indent=3))

    print( str(len(json_data["reduxState"]["content"])) + ' pictures pending. ')
    countProcessed = 0

    for picture in json_data["reduxState"]["content"]:
        cur = db.cursor()
        filename = ssCommon.get_stripped_file_name(picture['original_name'])
        cur.execute("select adobe_status, adobe_upload_date, adobe_review_date, adobe_id, adobe_keywords, adobe_title, adobe_cat "
                    "from ss_reviewed where ss_filename = %s", (filename,))

        db_data = cur.fetchone()
        if not db_data:
            log = "MISSING from DB:" + filename+":" + picture['title']
            print(log)
            LOG = LOG + log + '\n'
            cur.close()
            continue

        cur.close()

        if db_data[0] in ("state_online","state_refused"):
            continue

        countProcessed += 1
        if picture['status'] == 'state_online':
            print("APPROVED:" + filename+":" + picture['title'])

            LOG = LOG + "APPROVED:" + filename+":" + picture['title'] + '\n'
        else:
            print("REJECTED:" + filename+":" + picture['title'])
            #print(str(picture))
            reason = picture['moderationHistory']["causeLabel"] if "moderationHistory" in picture else "Unknown"
            print(reason)

            LOG = LOG + "REJECTED:" + filename+":" + picture['title'] + '\n'
            LOG = LOG + reason + '\n'

        # fix submit related fields if auto submit did not do it (for example if the picture was submitted manually)
        adobe_upload_date = db_data[1] if db_data[1] else datetime.fromtimestamp(int(picture['creationDate'])/1000)
        media_id = db_data[3] if db_data[3] else picture['id']
        keywords = db_data[4] if db_data[4] else ','.join(picture['keywords'])
        title = db_data[5] if db_data[5] else picture['title']
        cat = db_data[6] if db_data[6] else picture['category_hierarchy'][0]['name'] if len(picture["category_hierarchy"]) else None

        cur = db.cursor()
        cur.execute("update ss_reviewed set adobe_status = %s, adobe_upload_date = %s, adobe_review_date = now(), adobe_id = %s, adobe_keywords = %s,"
                    " adobe_title = %s, adobe_cat = %s "
                    " where ss_filename  = %s", (
                        picture['status'],
                        adobe_upload_date ,
                        media_id,
                        keywords,
                        title,
                        cat,
                        filename,
                    ))
        cur.close()

    return countProcessed

if __name__ == "__main__":

    try:
        db = ssCommon.connect_database()
        adobeCommon.adobe_login()
        LOG = ''

        countApproved = loadAdbodeImages(LOG, REVIEWED_URL)
        countRejected = loadAdbodeImages(LOG, REJECTED_URL)

        db.commit()
        db.close()

        # if (countApproved + countRejected) > 0:
        #     ssCommon.send_notification_email('Adobe reviewed', LOG)

    except SystemExit:
        raise
    except:
        exception_data = ''.join(traceback.format_exception(*sys.exc_info()))
        print(exception_data)
#        ssCommon.handleException(exception_data,"synchAdobeReviewed")
        raise


