# handle duplicates BEFORE going ot cloud?
# lookup location if shortcut present/sslat/sslong/gps

# upload to google drive
# register in database as EE only, possibly ss_filename, original filename

# get keywords, embed into application
# todo: extract from ss code

# upload to EE from google drive with embedded keywords

#todo: review process to indicate ee path and forward to SS pending
import json
import os
import re
import shutil
import sys
import traceback
from datetime import datetime
from os.path import join

import exiftool
from shutterstock import ssCommon, kwCommon
from shutterstock.eyeem import uploadEyeEm, eeCommon

TEMP_NAME = 'ee.pic.keyworder.tmp'

def handle_new_picture(db, filename, kw, location):

    cur = db.cursor()
    cur.execute("insert into ss_reviewed " +
                " (original_filename, kw_mykeyworder, ss_filename, ss_location, initial_filename) " +
                " values(%s,%s,%s,%s,%s)", (
                    filename,
                    kw,
                    ssCommon.get_stripped_file_name(filename),
                    location if location else None,
                    filename
                ))
    cur.close()

    cur = db.cursor()
    cur.execute("select id from ss_reviewed where ss_filename = %s", (ssCommon.get_stripped_file_name(filename),))
    id_rec = cur.fetchone()
    cur.close()

    return id_rec[0]

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


if __name__ == "__main__":

    try:
        # if 'EXIF_TOOL' not in os.environ:
        #     os.environ['EXIF_TOOL'] = 'exiftool'

        try:
            import localParams
            print("Using *LOCAL* params")
        except ImportError:
            print("Using standard params")

        db = ssCommon.connect_database()
        storage_client = ssCommon.get_storage_client()
        bucket = storage_client.get_bucket('myphotomgr')
        eeCommon.ee_login()

        # fix files in location folders, by appeindingf the locatiion to the file name and moving to the base folder
        for filename in os.listdir(ssCommon.FOLDER_PENDING_EE):

            if os.path.isdir(ssCommon.FOLDER_PENDING_EE + "\\" + filename):

                if re.match(ssCommon.locationMatch, filename):
                    m = re.search(ssCommon.locationMatch, filename)
                    location = filename[m.start():m.end()]

                    for loc_file in os.listdir(ssCommon.FOLDER_PENDING_EE + "\\" + filename):
                        if not loc_file.endswith('.jpg'):
                            continue
                        newName = loc_file[:-4] + location + ".jpg"
                        os.rename(ssCommon.FOLDER_PENDING_EE + "\\" + filename + "\\" + loc_file, ssCommon.FOLDER_PENDING_EE + "\\" + newName)


        count = 0
        for filename in os.listdir(ssCommon.FOLDER_PENDING_EE):

            if os.path.isdir(ssCommon.FOLDER_PENDING_EE + "\\" + filename):
                continue

            if not filename.endswith('.jpg'):
                continue

            new_name = filename
            if ssCommon.check_existence(db, filename) == 'duplicate':
                print("Duplicate and processed file: " + filename)

                count = 1
                body, ext = os.path.splitext(filename)
                while True:
                    if ssCommon.is_rework(filename):
                        orig_name = os.path.splitext(ssCommon.get_stripped_file_name(filename, True))[0]
                    else:
                        orig_name = os.path.splitext(ssCommon.get_stripped_file_name(filename))[0]
                    print('orig_name:' + orig_name)
                    new_name=body.replace(orig_name, orig_name+str(count)) + ext
                    action = ssCommon.check_existence(db, new_name)
                    if action != "duplicate":
                        break
                    count += 1

                os.rename(join(ssCommon.FOLDER_PENDING_EE, filename), join(ssCommon.FOLDER_PENDING_EE, new_name))
                os.rename(join(ssCommon.FOLDER_PENDING_EE + "\\dng", ssCommon.get_stripped_file_name(filename).replace('.jpg','.dng')),
                  join(ssCommon.FOLDER_PENDING_EE + "\\dng", ssCommon.get_stripped_file_name(new_name).replace('.jpg','.dng')))

            print ('Uploading ' + new_name)

            # upload to cloud storage
           # d = bucket.blob("ee/"+filename)
           # with open(ssCommon.FOLDER_PENDING_EE + "\\" + new_name, "rb") as pic:
           #     d.upload_from_file(pic) # predefined_acl='publicRead'

            ########### get keyworder keywords
            shutil.copy(ssCommon.FOLDER_PENDING_EE + "\\" + new_name, TEMP_NAME)
            kw = kwCommon.get_keywords(storage_client,TEMP_NAME, None)
            os.remove(TEMP_NAME)

            data = ssCommon.extract_data_from_file_name(new_name)
            if data['locationShort']:
                data['location'] = ssCommon.lookup_location_by_code(db, data['locationShort'])

            ss_id = handle_new_picture(db, new_name,kw,data['location'])

            modify_exif_data(ssCommon.FOLDER_PENDING_EE + "\\" + new_name, json.loads(data['location']) if data['location'] else None, kw, data['title'])

            uploadEyeEm.uploadEE(db, ss_id, ssCommon.FOLDER_PENDING_EE + "\\" + new_name)

            db.commit()

            jpg_name = join(ssCommon.FOLDER_PENDING_EE, new_name)
            dng_name = join(ssCommon.FOLDER_PENDING_EE + "\\dng", ssCommon.get_stripped_file_name(new_name).replace('.jpg','.dng'))

            shutil.move(jpg_name, ssCommon.FOLDER_UNDER_REVIEW_EE)
            shutil.move(dng_name, ssCommon.FOLDER_UNDER_REVIEW_EE + "\\dng")

            count += 1

        print('Complete ' + str(count) + '.')
        db.close()
        print('Processing finished.')

    except SystemExit:
        raise
    except:
        exception_data = ''.join(traceback.format_exception(*sys.exc_info()))
        ssCommon.handleException(exception_data, "processNewPics")
        raise


