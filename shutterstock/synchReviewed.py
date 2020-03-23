import json
import requests

from shutterstock import ssCommon

REVIEWED_URL = "https://submit.shutterstock.com/api/content_editor/photo"

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

    ####################################################################
    # get list of waiting files
    print( str(len(json_response['data'])) + 'pictures pending. ')
    countApproved = 0
    countRejected= 0
    for picture in json_response['data']:

        cur = db.cursor()
        cur.execute("select state from ss_reviewed where ss_filename = %s and state = 2", (picture['original_filename'],))

        db_data = cur.fetchone()
        if not db_data:
            continue
        cur.close()

        reason = ";".join(ssCommon.reasons[ctg['reason']] for ctg in picture['reasons']) if 'reasons' in picture else ''

        if picture['status'] == 'approved':
            print("APPROVED" + picture['original_filename'])
            status = '3'
            countApproved += 1
        else:
            print("APPROVED" + picture['original_filename'])
            status = '4'
            countRejected += 1

        cur = db.cursor()
        cur.execute("update ss_reviewed set ss_status = %s, state = %s, date_reviewed = now(), ss_reason = %s where ss_filename  = %s", (
            picture['status'],
            status,
            reason,
            picture['original_filename']
        ))
        cur.close()

    print(str(countApproved) + ' approved. ' + str(countRejected) + ' rejected.')

    db.close()