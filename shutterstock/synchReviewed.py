import json
import requests

from shutterstock import ssCommon

REVIEWED_URL = "https://submit.shutterstock.com/api/content_editor/photo"
REASONS_URL = "https://submit.shutterstock.com/api/content_editor/reasons"

if __name__ == "__main__":

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

    cur = db.cursor()
    cur.execute('delete from ss_category')
    for k,v in zip(ssCommon.categories.keys(), ssCommon.categories.values()) :
        cur.execute('insert into ss_Category (category, category_name) values (%s,%s)', (k, v))
    db.commit()

    ####################################################################
    # get list of waiting files
    print( str(len(json_response['data'])) + ' pictures pending. ')
    countApproved = 0
    countRejected= 0
    for picture in json_response['data']:

        cur = db.cursor()
        cur.execute("select state from ss_reviewed where ss_filename = %s and state = 20", (picture['original_filename'],))

        db_data = cur.fetchone()
        if not db_data:
            continue
        cur.close()

        reason = ''

        if picture['status'] == 'approved':
            print("APPROVED:" + picture['original_filename']+":" + picture['description'])
            status = '30'
            countApproved += 1
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

        cur = db.cursor()
        cur.execute("update ss_reviewed set ss_status = %s, state = %s, date_reviewed = now(), ss_reason = %s, ss_location = %s where ss_filename  = %s", (
            picture['status'],
            status,
            reason,
            json.dumps(picture['location']),
            picture['original_filename'],
        ))
        cur.close()

    print(str(countApproved) + ' approved. ' + str(countRejected) + ' rejected.')

    db.commit()
    db.close()