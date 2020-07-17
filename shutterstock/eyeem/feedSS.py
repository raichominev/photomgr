import json
import os
import shutil
from os.path import join

import exiftool
from shutterstock import ssCommon, kwCommon
from shutterstock.eyeem import eeCommon

BATCH_SIZE = 10
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
    return title[0] + title[1:].lower() + "." if title else ''

def prepare_kw(keyworder_kw, ee_keywords):
    x = set()
    x.update(keyworder_kw.split(","))
    x.update(ee_keywords.split(","))

    for junk in kwCommon.JUNK_KEYWORDS:
        if junk in x:
            x.remove(junk)

    return ",".join(list(x)[0:50])


if __name__ == "__main__":

    try:
        import localParams
        print("Using *LOCAL* params")
    except ImportError:
        print("Using standard params")

    db = ssCommon.connect_database()

    eeCommon.ee_login()
    storage_client = ssCommon.get_storage_client()
    bucket = storage_client.get_bucket('myphotomgr')

    cur = db.cursor()
    cur.execute("select original_filename, kw_mykeyworder, ee_ai_title, ee_ai_keywords, id from ss_reviewed where state = 0 and ee_level in ('good','attn')")
    db_records = cur.fetchall()

    print ('Pending records ' + str(len(db_records)))

    count = 0
    for i in range(BATCH_SIZE):
        if i>= len(db_records):
            break
        db_data = db_records[i]
        if db_data is None:
            break

        # get data from my_keyworder if not present
        filename = db_data[0]
        keyworder_kw = db_data[1]
        ee_title = prepare_title(db_data[2])
        ee_keywords = db_data[3]
        id = db_data[4]

        print ('Uploading ' + filename)
        # upload to cloud storage
        d = bucket.blob(filename)
        with open(ssCommon.FOLDER_UNDER_REVIEW_EE + "\\" + filename, "rb") as pic:
            d.upload_from_file(pic) # predefined_acl='publicRead'

        if not keyworder_kw:
            keyworder_kw = kwCommon.get_keywords(storage_client, ssCommon.FOLDER_UNDER_REVIEW_EE + "\\" + filename, ee_title)

        kw = prepare_kw(keyworder_kw,ee_keywords)

        data = ssCommon.extract_data_from_file_name(filename)
        if data['locationShort']:
            data['location'] = ssCommon.lookup_location_by_code(db, data['locationShort'])

        # modify_exif_data(ssCommon.FOLDER_UNDER_REVIEW_EE + "\\" + filename, json.loads(data['location']) if data['location'] else None, kw, ee_title)



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

        # update databse, ss_keywords, ss_title, ss_location, so process new finds them

        # move to ss reviewed
        jpg_name = join(ssCommon.FOLDER_UNDER_REVIEW_EE, filename)
        dng_name = join(ssCommon.FOLDER_UNDER_REVIEW_EE + "\\dng", ssCommon.get_stripped_file_name(filename).replace('.jpg','.dng'))

        shutil.move(jpg_name, ssCommon.FOLDER_UNDER_REVIEW)
        shutil.move(dng_name, ssCommon.FOLDER_UNDER_REVIEW + "\\dng")

        count += 1

    print('Complete ' + str(count) + '.')