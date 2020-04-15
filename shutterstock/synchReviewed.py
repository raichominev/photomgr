import json
import sys
import traceback

import requests

from shutterstock import ssCommon

REVIEWED_URL = "https://submit.shutterstock.com/api/content_editor/photo"
REASONS_URL = "https://submit.shutterstock.com/api/content_editor/reasons"

if __name__ == "__main__":

    LOG = ''
    try:
        db = ssCommon.connect_database()
        ssCommon.ss_login()

        response = requests.get(
            REVIEWED_URL,
            params={'xhr_id': '1', 'status': 'reviewed', 'page_number':'1', 'per_page': '100', 'order':'newest'},
            cookies=ssCommon.cookie_dict,
            headers=ssCommon.DEFAULT_HEADERS
        )
        print(response.url)
        print(response)
        json_response = response.json()

        # cur = db.cursor()
        # cur.execute('delete from ss_category')
        # for k,v in zip(ssCommon.categories.keys(), ssCommon.categories.values()) :
        #     cur.execute('insert into ss_Category (category, category_name) values (%s,%s)', (k, v['name']))
        # db.commit()

        ####################################################################
        # get list of waiting files
        print( str(len(json_response['data'])) + ' pictures pending. ')
        countApproved = 0
        countRejected= 0
        for picture in json_response['data']:

            cur = db.cursor()
            cur.execute("select state, ss_title, ss_keywords, ss_media_id, ss_cat1, ss_cat2 from ss_reviewed where ss_filename = %s", (picture['original_filename'],))

            db_data = cur.fetchone()
            if not db_data:
                log = "MISSING from DB:" + picture['original_filename']+":" + picture['description']
                print(log)
                LOG = LOG + log + '\n'
                cur.close()
                continue

            if db_data[0] not in (10,20):
                cur.close()
                continue

            cur.close()

            reason = ''

            if picture['status'] == 'approved':
                print("APPROVED:" + picture['original_filename']+":" + picture['description'])
                status = '30'
                countApproved += 1

                LOG = LOG + "APPROVED:" + picture['original_filename']+":" + picture['description'] + '\n'
            else:
                print("REJECTED:" + picture['original_filename']+":" + picture['description'])
                status = '40'
                countRejected += 1

                reason_list = ['"' + ctg['reason'] + '"' for ctg in picture['reasons']]
                submit_payload = '{"id":['+ ','.join(reason_list) + '],"language":"en"}'
                # print(submit_payload)
                response = requests.post(
                    REASONS_URL,
                    json = json.loads(submit_payload),
                    cookies=ssCommon.cookie_dict,
                    headers=ssCommon.DEFAULT_HEADERS
                )
                #print(response)
                reason_json = response.json()
                reasons = [ rsn["description"] for rsn in reason_json["reasons"]]

                reason = '|'.join(reasons)
                print(reason)

                LOG = LOG + "REJECTED:" + picture['original_filename']+":" + picture['description'] + '\n'
                LOG = LOG + reason + '\n'

            # fix submit related fields if auto submit did not do it (for example if the picture was submitted manually)
            title = db_data[1] if db_data[1] else picture['description']
            keywords = db_data[2] if db_data[2] else ','.join(picture['keywords'])
            media_id = db_data[3] if db_data[3] else picture['media_id']
            cat1 = db_data[4] if db_data[4] else picture['categories'][0] if len(picture['categories']) > 0 else None
            cat2 = db_data[5] if db_data[5] else picture['categories'][1] if len(picture['categories']) > 1 else None

            cur = db.cursor()
            cur.execute("update ss_reviewed set ss_status = %s, state = %s, date_reviewed = now(), ss_reason = %s, ss_location = %s,"
                        " ss_title = %s, ss_keywords = %s, ss_media_id = %s, ss_cat1 = %s, ss_cat2 = %s "
                        " where ss_filename  = %s", (
                picture['status'],
                status,
                reason,
                json.dumps(picture['location']),
                title,
                keywords,
                media_id,
                cat1,
                cat2,
                picture['original_filename'],
            ))
            cur.close()

        print(str(countApproved) + ' approved. ' + str(countRejected) + ' rejected.')
        LOG = LOG + str(countApproved) + ' approved. ' + str(countRejected) + ' rejected.' + '\n'

        db.commit()
        db.close()

        if countRejected + countRejected > 0:
            ssCommon.send_notification_email('Shutterstock reviewed', LOG)

    except SystemExit:
        raise
    except:
        exception_data = ''.join(traceback.format_exception(*sys.exc_info()))
        ssCommon.handleException(exception_data,"synchReviewed")
        raise
