import os
import shutil
from os.path import join

import exiftool

from shutterstock import ssCommon
categories = {}

def modify_exif_data(picture, jpg_name ,dng_name):

    subject = ";".join(categories[int(ctg)] for ctg in picture['categories'])

    print('=======================================================================')
    print(jpg_name)
    print(picture['title'])
    print(subject)


    modification_list = (
            (
                b'-overwrite_original',
                b'-makernotes=.',
                b'-description=' + bytes(picture['title'],encoding='latin1'),
                b'-caption=' + bytes(picture['title'],'latin1'),
                b'-title=' + bytes(picture['title'],'latin1'),
                b'-imagedescription=' + bytes(subject,'latin1'),
                b'-ImageUniqueID=' + bytes(str(picture['id']),'latin1'),
                b'-ImageID=' + bytes(str(picture['id']),'latin1'),
                b'-copyright=' + bytes(picture['location'],'latin1'),
                b'-keywords=',
            ) +
            tuple(b'-keywords=' + bytes(kwd,encoding='latin1') for kwd in picture['keywords'])
    )

    with exiftool.ExifTool(EXIF_TOOL) as et:
        # print (str(( modification_list + (bytes(jpg_name, encoding='latin1'),))))
        outcome =  et.execute( * ( modification_list + (bytes(jpg_name, encoding='latin1'),)) )
        print(outcome)
        if b'1 image files updated' not in outcome:
            return False
        outcome = et.execute( * ( modification_list + (bytes(dng_name, encoding='latin1'),)) )
        print(outcome)
        if b'1 image files updated' not in outcome:
            return False

    return True

if __name__ == "__main__":
    from google.cloud import storage

    global EXIF_TOOL

    if 'EXIF_TOOL' in os.environ:
        EXIF_TOOL = os.environ['EXIF_TOOL']
    else:
        EXIF_TOOL = 'exiftool'

    f = open('cloud_auth.txt','w+')
    f.write(os.environ['CLOUD_STORE_API'])
    f.close()

    storage_client = storage.Client.from_service_account_json('cloud_auth.txt')
    bucket = storage_client.get_bucket('myphotomgr')

    db = ssCommon.connect_database()

    cur = db.cursor()
    cur.execute("select category, category_name from ss_category")
    for data in cur.fetchall():
        categories[data[0]] = data[1]

    cur = db.cursor()
    cur.execute("select original_filename, state, title, ss_keywords, ss_cat1, ss_cat2, ss_media_id, ss_location from ss_reviewed where state in (30,40) ")

    countAccepted = 0
    countRejected = 0
    for data in cur.fetchall():
        print ('Synching ' + 'ACCEPTED ' if data[1] == 30 else 'REJECTED ' + data[0])

        jpg_name = join(ssCommon.FOLDER_UNDER_REVIEW, data[0])
        dng_name = join(ssCommon.FOLDER_UNDER_REVIEW+ "\\dng", ssCommon.get_stripped_file_name(data[0]).replace('.jpg','.dng'))

        if data[1] == 30:
            shutil.move(jpg_name, ssCommon.FOLDER_REVIEWED )
            shutil.move(dng_name, ssCommon.FOLDER_REVIEWED + "\\dng")

            fix_list = {}
            catList=[]
            if data[4]: catList.append(data[4])
            if data[5]: catList.append(data[5])
            fix_list= {'original_filename':data[0],
                       'title':data['2'],
                       'keywords': data[3].split(','),
                       'categories':catList,
                       'location': data[7],
                       'id': data[6]}

            modify_exif_data(fix_list, jpg_name ,dng_name)

            countAccepted += 1
        if data[1] == 40:
            shutil.move(jpg_name, ssCommon.FOLDER_REJECTED )
            shutil.move(dng_name, ssCommon.FOLDER_REJECTED + "\\dng")
            countRejected += 1

            # todo: import DNG in lightroom?

        # release cloud bucket
        d = bucket.blob("sent\\" + data[0])
        d.delete()

        cur = db.cursor()
        cur.execute("select state from ss_reviewed where ss_filename = %s and state = 50", (data[0],))
        db.commit()

        break

    print('Complete. Accepted:' + str(countAccepted) + '. Rejected:' + str(countRejected))