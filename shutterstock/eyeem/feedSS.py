import json
import os
import shutil
from os.path import join

import exiftool
from shutterstock import ssCommon, kwCommon
from shutterstock.eyeem import eeCommon

BATCH_SIZE = 1
TEMP_NAME = 'pic.ee.keyworder.tmp'

def modify_exif_data(jpg_name, location, kw, title):

    print('=======================================================================')
    print(jpg_name)

    lat = None
    long = None
    if location and location["external_metadata"]:
        loc_data = json.loads(location["external_metadata"])
        lat = loc_data["geometry"]["location"]["lat"]
        long = loc_data["geometry"]["location"]["lng"]

    title = title if title else ''

    modification_list = (
            (
                b'-overwrite_original',
                b'-m',
                b'-description=' + bytes(title,encoding='latin1'),
                b'-caption=' + bytes(title,'latin1'),
                b'-title=' + bytes(title,'latin1'),
                b'-XMP:GPSLatitude=' + bytes(str(lat).replace("-","") if lat else "",'latin1'),
                b'-XMP:GPSLongitude=' + bytes(str(long).replace("-","") if long else "",'latin1'),
                b'-GPSLatitudeRef=' + bytes('S' if '-' in str(lat) else 'N' if lat else "",'latin1'),
                b'-GPSLongitudeRef=' + bytes('W' if '-' in str(lat) else 'E' if long else "",'latin1'),
                b'-keywords=',
            ) +
            tuple(b'-keywords=' + bytes(kwd,encoding='latin1') for kwd in kw.split(','))
    )

    with exiftool.ExifTool(os.environ['EXIF_TOOL'], False) as et:
        outcome =  et.execute( * ( modification_list + (bytes(jpg_name.replace("/",'\\'), encoding='latin1'),)) )
        print(outcome)

        if b'1 image files updated' not in outcome:
            return False

    return True


def prepare_title(title):
    return title[0] + title[1].lower() + "."

def prepare_kw(keyworder_kw, ee_keywords):
    x = set()
    x.update(keyworder_kw.split(","))
    x.update(ee_keywords.split(","))

    for junk in kwCommon.JUNK_KEYWORDS:
        if junk in x:
            x.remove(junk)

    return ",".join(list(x)[0:50])


if __name__ == "__main__":

    if not 'SS_AUTO_UPLOAD_FIX_WAIT_TIME' in os.environ:
        os.environ['SS_AUTO_UPLOAD_FIX_WAIT_TIME'] = "15"

    if not "DATABASE_URL" in os.environ:
        os.environ["DATABASE_URL"] = "postgres://uhztcmpnkqyhop:c203bc824367be7762e38d1838b54448fe503f16fe34bb783d45a4a8bb370c00@ec2-34-200-116-132.compute-1.amazonaws.com:5432/d42v6sfcnns36v"

    if not "CLOUD_STORE_API" in os.environ:
        os.environ["CLOUD_STORE_API"] = os.environ["CLOUD_STORE_API"] = '{"type":"service_account","project_id":"reliable-cacao-259921","private_key_id":"6eff9ee5d7e6a0a3e3fba9909e87dc739c8cc783","private_key":"-----BEGIN PRIVATE KEY-----\\nMIIEvwIBADANBgkqhkiG9w0BAQEFAASCBKkwggSlAgEAAoIBAQC2JWBYThjeEfUH\\nTeSqZ0biIL2sF0d3PExcA7v+Uf+pywzsFl6kYBYJxmkXhZPiZ2R72jWrIjPz9lvv\\nOJ2SaP08yoaaBbXh/m+98utm0iswR6Zy8bV4v3pP5x9rofqD/sNaBIG+KOZO/y+Z\\nmwFCbBpaxl/27yuRd8GI9JTdyody2XbsH9kAE0kYwr9zifBxyK2eY1wVfqz7O2xt\\nrgW723TGZgavsFmygD7SGtXrHz8XlYkJnGmNfYtj+6lRRXJrZlnzoxEJP0W2ondo\\naZ//N+DkgyWAEp75WnmNBVIBTUUpCCvK5To+vi1IKvQbLW6Lc/XKygw9xb0bIb0J\\nWnXoY5e1AgMBAAECggEAU3i+dclYcRB2o2HJbGQG4mMRuPc0G4rpDXPyp6JJUTUJ\\n13mK5rZX8yPXjl17P5KVRILj/GiguWkJiY/++hUeFElVtOjwCMCy0bAsu8KN40K6\\nn0twmATb1xk6V3d0GCBcwvh0wsH4hXRBipmz0o4656WoXcAOTcw9R3eabye8ud7z\\nlu2CHGq3VM9TUNPQttpNTN8aqYzV535uiXwzd2SrnDa6CRx9YYj3p0WROLH67rUH\\nO/pGeB5RyGE4xCcpCBrXMIWG9RuI1d4YRMM3cunu2rZjntN6Tqjt6UFMx23NUJEV\\nvEydQHMNZx7r82ho5aXl2zDxwjHrNaUUQM780wDv8wKBgQDh+l4S0kDWpm133kT2\\n53aUH4od+b1jgHpygj5lX60LlwOSiL9zmL8K/osrZAOsUfK/3MCojAfhXh9UrfJq\\n7Lsgc//u6G+xLnwZtC8DFdcU2Gl6qcYioa88nLJs+i9R1dS2c2D+p9uEpf661rSM\\n/HdJP3As7RmuqonyMha0qXb0QwKBgQDOWEJdNF/D+gfqmYjUB6M/0BXsYXnAVTDV\\ngbNJ8vh+Uzy1SLHyPhjnAfv5WpCWUPqyW19vPe3rQhpJ+uLHD58l6pInb/aMHHO6\\nHb26jVWvGWHvBGuYtEuQ7k1G86KXfZP4kA5oWx45coavs/x3AqcVAu7xBax9716T\\nvViQi4jApwKBgQDCYvM/b3t06a7q2NksJsl6+3J8/JJsoF00WVNBMr8RZDMffuBp\\nmLBlzbZ7ecorFkchwcw8cFBrDeMXnZYVYlRJw18Z7Pn/SQRZvARgvA3LEaoSaS5W\\nJg0ur4BQfBnuZGlZFQEPrecIQR5RLFYdnSMjcB2Xl9FqzapiG7IqcEgyLwKBgQCI\\nO8NNEBguJrT1UfsBqi1BI1xmHZEpx9UfEavSpgUkOkZ5lg5OVmtQkYHQBtgxNjPe\\nb+9ZXbToP1NmBquVK54yhWWLfiN0LBDID3zFXyz0FzkOeoejYV4GyR7iOlbd1/5K\\n/KlWgto4qYF9HcMQvAKeH7qsDMfuuYxi1H9Vp5pZPwKBgQCozznamzBURXq9cCCP\\nzh7eV4xWMdDcW86jGgvsSEO/3dnyNjDEs7sb+nim8eJXT1rAzWf3g1XO37h2Mlhe\\nNOwBmeccDh5Dn4s9lpgTwhESvALuFfAjqnyHsSl6I9wRxlIWSF93gcCyZ6BNh5Ev\\nmJiVPJaBSsi5ar0RVdMX6aV8Pg==\\n-----END PRIVATE KEY-----\\n","client_email":"excelparty@reliable-cacao-259921.iam.gserviceaccount.com","client_id":"112793133808142549758","auth_uri":"https://accounts.google.com/o/oauth2/auth","token_uri":"https://oauth2.googleapis.com/token","auth_provider_x509_cert_url":"https://www.googleapis.com/oauth2/v1/certs","client_x509_cert_url":"https://www.googleapis.com/robot/v1/metadata/x509/excelparty%40reliable-cacao-259921.iam.gserviceaccount.com"}'


    db = ssCommon.connect_database()

    eeCommon.ee_login()
    storage_client = ssCommon.get_storage_client()
    bucket = storage_client.get_bucket('myphotomgr')

    cur = db.cursor()
    cur.execute("select original_filename, kw_mykeyworder, ee_ai_title, ee_ai_keywords, id from ss_reviewed where state = 0 and ee_level = 'good'")
    db_records = cur.fetchall()

    count = 0
    for i in range(BATCH_SIZE):
        db_data = db_records[i]
        if db_data is None:
            break

        # get data from my_keyworder if not present
        filename = db_data[0]
        keyworder_kw = db_data[1]
        ee_title = prepare_title(db_data[2])
        ee_keywords = db_data[3]
        id = db_data[4]

        if not keyworder_kw:
            keyworder_kw = kwCommon.get_keywords(storage_client, TEMP_NAME, ee_title)

        kw = prepare_kw(keyworder_kw,ee_keywords)

        data = ssCommon.extract_data_from_file_name(filename)
        if data['locationShort']:
            data['location'] = ssCommon.lookup_location_by_code(db, data['locationShort'])

        # modify_exif_data(ssCommon.FOLDER_UNDER_REVIEW_EE + "\\" + filename, json.loads(data['location']) if data['location'] else None, kw, ee_title)

        print ('Uploading ' + filename)

        cur = db.cursor()
        cur.execute("update ss_reviewed set ss_title = %s, ss_keywords = %s, kw_mykeyworder = %s, title = %s, ss_location = %s where id = %s " , (
            ee_title,
            kw,
            keyworder_kw,
            ee_title,
            data['location'],
            id,
        ))
        db.commit()

        # upload to cloud storage
        d = bucket.blob(filename)
        with open(ssCommon.FOLDER_UNDER_REVIEW_EE + "\\" + filename, "rb") as pic:
            d.upload_from_file(pic) # predefined_acl='publicRead'

        # update databse, ss_keywords, ss_title, ss_location, so process new finds them

        # move to ss reviewed
        jpg_name = join(ssCommon.FOLDER_UNDER_REVIEW_EE, filename)
        dng_name = join(ssCommon.FOLDER_UNDER_REVIEW_EE + "\\dng", ssCommon.get_stripped_file_name(filename).replace('.jpg','.dng'))

        shutil.move(jpg_name, ssCommon.FOLDER_UNDER_REVIEW)
        shutil.move(dng_name, ssCommon.FOLDER_UNDER_REVIEW + "\\dng")

        count += 1

    print('Complete ' + str(count) + '.')