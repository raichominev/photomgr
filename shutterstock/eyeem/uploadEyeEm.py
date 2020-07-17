import json
import os
import time
import uuid

import requests

from shutterstock import ssCommon
from shutterstock.eyeem import eeCommon

BATCH_SIZE = 10

UPLOAD_URL = 'https://www.eyeem.com/data/upload'
METADATA_URL = 'https://www.eyeem.com/data/upload/metadata'
SUBMIT_URL = 'https://www.eyeem.com/data/upload/post'


def uploadEE(db, db_id, full_file_name):
    files = {'photo': (ssCommon.get_stripped_file_name(os.path.basename(full_file_name)), open(full_file_name,"rb+"),'image/jpeg')}
    resp = requests.post(UPLOAD_URL, files=files, headers=eeCommon.DEFAULT_HEADERS, cookies=eeCommon.cookie_dict, )
    print(resp)
    #print(str(resp.content))
    #print(resp.json())

    uploaded_file_json = resp.json()

    internal_file_name = uploaded_file_json["filename"]

    print(internal_file_name)

    print('Sleeping ' + os.environ['SS_AUTO_UPLOAD_FIX_WAIT_TIME'] + ' sec.')
    time.sleep(int(os.environ['SS_AUTO_UPLOAD_FIX_WAIT_TIME']))

    # todo: wait for the auto keywords for several cycles
    response = requests.post(METADATA_URL, json={"filenames":[internal_file_name]}, headers=eeCommon.DEFAULT_HEADERS, cookies=eeCommon.cookie_dict, )

    metadata_json = response.json()

    title = metadata_json["iptc"][internal_file_name]["description"] if 'description' in metadata_json["iptc"][internal_file_name] else ''
    kw = metadata_json["iptc"][internal_file_name]["keywords"]
    if metadata_json["closestCity"][internal_file_name]:
        location = metadata_json["closestCity"][internal_file_name]["name"] + ", " + metadata_json["closestCity"][internal_file_name]["countryName"],
    else:
        location = None

    submit_json = {"photoArray": [
        {
            "batchUploadId": str(uuid.uuid4()),
            "uuid": str(uuid.uuid4()),
            "filename": internal_file_name,
            "market": True,
            "description": title,
            "albums": kw,
            "location": {
                "id": metadata_json["closestCity"][internal_file_name]["albumId"],
                "city": metadata_json["closestCity"][internal_file_name]["name"],
                "country": metadata_json["closestCity"][internal_file_name]["countryName"],
                "text": location
            } if metadata_json["closestCity"][internal_file_name] else {},
            "noLocation":True,
            "original_filename":ssCommon.get_stripped_file_name(os.path.basename(full_file_name))
        },
    ]}

    resp = requests.post(SUBMIT_URL, json=submit_json, headers=eeCommon.DEFAULT_HEADERS, cookies=eeCommon.cookie_dict, )
    print(resp)
    #print(resp.json())

    # todo: extrace eye vision tags from metadata

    submit_resp_json = resp.json()

    if submit_resp_json["postedPhotos"]["success"]:
        print("Photo uploaded! Id:" + str(submit_resp_json["postedPhotos"]["success"][0]["photoId"]))

        cur = db.cursor()
        cur.execute("update ss_reviewed set ee_status = 'uploaded', ee_upload_date = now(),"
                    " ee_id = %s,  ee_title = %s, ee_keywords = %s, ee_location = %s where id = %s " , (
                        submit_resp_json["postedPhotos"]["success"][0]["photoId"],
                        title,
                        ",".join(kw),
                        location,
                        db_id,
                    ))

        return 1
    else:
        raise Exception('Photo submission unsuccessful.Id:' + db_id)


if __name__ == "__main__":

    try:
        import localParams
        print("Using *LOCAL* params")
    except ImportError:
        print("Using standard params")

    db = ssCommon.connect_database()

    eeCommon.ee_login()

    #jsn = '{"loadTime":3399,"domReadyTime":1982,"readyStart":345,"redirectTime":344,"appcacheTime":0,"unloadEventTime":1,"lookupDomainTime":0,"connectTime":0,"requestTime":803,"initDomTreeTime":184,"loadEventTime":69,"navigationType":0,"redirectCount":1}'
    #response = requests.post("https://www.eyeem.com/data/perf", json=json.loads(jsn), headers=eeCommon.DEFAULT_HEADERS, cookies=eeCommon.cookie_dict, )
    #print(response)

    cur = db.cursor()
    cur.execute("select original_filename, id, ss_title from ss_reviewed where ss_status = 'approved' and state = 50 and ee_status is null")
    db_records = cur.fetchall()
    print('Database records pending:' + str(len(db_records)))
    count = 0
    for i in range(BATCH_SIZE):
        db_data = db_records[i]
        if db_data is None:
              break

        current_file_name = db_data[0]
        ss_id = db_data[1]

        print('Uploading file ' + current_file_name)
        print(db_data[2])

        count += uploadEE(db, ss_id, ssCommon.FOLDER_REVIEWED + "\\" + current_file_name)

        db.commit()

    print('' + str(count) + ' files uploaded.')