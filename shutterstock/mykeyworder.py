import base64
import ftplib
import os
from datetime import datetime

import psycopg2
import requests
from google.cloud import storage
import PIL
from PIL import Image
import re
import exiftool

titleMatch = r'T#.*#T'
catMatch = r'C#[0-9]{1,2}'

AUTO_SUBMIT = True
TEMP_NAME = 'pic.keyworder.tmp'
EXIF_TOOL = 'exiftool'

def resize_img(name, basewidth):
    img = Image.open(name)
    wpercent = (basewidth / float(img.size[0]))
    hsize = int((float(img.size[1]) * float(wpercent)))
    img = img.resize((basewidth, hsize), PIL.Image.ANTIALIAS)
    img.save(name+'.resized.jpg', "JPEG",  quality = 80)

def modify_exif_title(filename, title):

    modification_list = (
            (
                b'-overwrite_original',
                b'-makernotes=.',
                b'-description=' + bytes(title,encoding='latin1'),
                b'-caption=' + bytes(title,'latin1'),
                b'-title=' + bytes(title,'latin1'),
            )
    )

    with exiftool.ExifTool(EXIF_TOOL) as et:
        # print (str(( modification_list + (bytes(jpg_name, encoding='latin1'),))))
        outcome =  et.execute( * ( modification_list + (bytes(filename, encoding='latin1'),)) )
        print(outcome)
        if b'1 image files updated' not in outcome:
            return False
        outcome = et.execute( * ( modification_list + (bytes(filename, encoding='latin1'),)) )
        print(outcome)
        if b'1 image files updated' not in outcome:
            return False

    return True


def modify_exif_keywords(filename, keywords):

    modification_list = (
        (
            b'-overwrite_original',
            b'-makernotes=.',
            b'-keywords=',
        ) +
        tuple(b'-keywords=' + bytes(kwd,encoding='latin1') for kwd in keywords)
    )

    with exiftool.ExifTool(EXIF_TOOL) as et:
        # print (str(( modification_list + (bytes(jpg_name, encoding='latin1'),))))
        outcome =  et.execute( * ( modification_list + (bytes(filename, encoding='latin1'),)) )
        print(outcome)
        if b'1 image files updated' not in outcome:
            return False
        outcome = et.execute( * ( modification_list + (bytes(filename, encoding='latin1'),)) )
        print(outcome)
        if b'1 image files updated' not in outcome:
            return False

    return True

# create table ss_reviewed (
# ID SERIAL primary KEY,
# original_filename VARCHAR(500),
# title VARCHAR(2000),
# kw_mykeyworder VARCHAR(2000),
# kw_keywordsready VARCHAR(2000),
# ss_media_id   int,
# ss_filename VARCHAR(300),
# ss_title VARCHAR(2000),
# ss_keywords VARCHAR(2000),
# ss_cat1 int,
# ss_cat2 int,
# ss_data JSON,
#    status int4 default 0,
#    date_loaded timestamp default 'now',
#    date_submitted timestamp
# );


def connect_database():
    return psycopg2.connect(os.environ["DATABASE_URL"])


def extract_data_from_file_name(filename):

    m = re.search(titleMatch, filename)
    title = filename[m.start()+2:m.end()-2] if m else None

    catList = re.findall(catMatch, filename)
    cat1 = str(int(catList[0][2:])) if len(catList) > 0 else None
    cat2 = str(int(catList[1][2:])) if len(catList) > 1 else None

    return {'title': title, 'cat1': cat1, 'cat2': cat2}


def get_stripped_file_name(filename):
    m = re.search(titleMatch, filename)
    if m:
        filename = filename [:m.start()] + filename[m.end():]

    while True:
        m = re.search(catMatch, filename)
        if not m: break
        filename = filename [:m.start()] + filename[m.end():]

    return filename.replace("..",".")


def check_existence(db, filename):

    data = extract_data_from_file_name(filename)

    print('Extracted data:'+str(data))

    cur = db.cursor()
    cur.execute("select state, title, ss_cat1, ss_cat2 from ss_reviewed where ss_filename = %s ", (get_stripped_file_name(filename),))

    db_data = cur.fetchone()
    if not db_data:
        return "new"

    if db_data[0] == 0 and (str(data['title']) != str(db_data[1]) or str(data['cat1']) != str(db_data[2]) or str(data['cat2']) != str(db_data[3])):
        return "pending"

    cur.close()
    return "duplicate"


def handle_new_picture(db, filename, kw):

    data = extract_data_from_file_name(filename)

    cur = db.cursor()
    cur.execute("insert into ss_reviewed " +
                " (original_filename, title, kw_mykeyworder, ss_filename, ss_cat1, ss_cat2) " +
                " values(%s,%s,%s,%s,%s,%s)", (
                    filename,
                    data['title'],
                    kw,
                    get_stripped_file_name(filename),
                    data['cat1'],
                    data['cat2']
                ))
    cur.close()


def handle_modified_picture(db, filename, kw):

    data = extract_data_from_file_name(filename)

    cur = db.cursor()
    cur.execute("update ss_reviewed set original_filename = %s, title = %s, kw_mykeyworder = %s, ss_cat1 = %s, ss_cat2 = %s where ss_filename  = %s", (
        filename,
        data['title'],
        kw,
        data['cat1'],
        data['cat2'],
        get_stripped_file_name(filename)
    ))
    cur.close()


def get_keywords(temp_name, title):

    resize_img(temp_name, 3000)

    if title:
        modify_exif_title(temp_name + '.resized.jpg', title)

    idx = str(round(datetime.now().timestamp() * 1000000))
    d = bucket.blob(temp_name + idx +'.jpg')
    with open(temp_name + '.resized.jpg', "rb") as pic:
        d.upload_from_file(pic, predefined_acl='publicRead')

    image_url = 'http://storage.googleapis.com/myphotomgr/'+temp_name+idx+'.jpg'
    auth = bytes(os.environ['MYKEYWORDER_USER'], 'latin1') + b':' + bytes(os.environ['MYKEYWORDER_KEY'], 'latin1')
    headers = {'Authorization': b'Basic ' + base64.b64encode(auth)}

    response = requests.get('http://mykeyworder.com/api/v1/analyze', {'url': image_url}, headers=headers)

    data = response.json()

    print(str(data))

    keywords = ",".join(data['keywords'])

    print('kw:'+keywords)

    d.delete()

    return keywords


if __name__ == "__main__":

    db = connect_database()

    f = open('cloud_auth.txt','w+')
    f.write(os.environ['CLOUD_STORE_API'])
    f.close()

    storage_client = storage.Client.from_service_account_json('cloud_auth.txt')

    # GOOG1EUAMHFAI7RFWLLCFNT2KMBZ5DZRG2ERNBCUNNJFDIB4UZDWWUWUH7VDI
    #iNAHij6B2KPfrPNmllFUAfibpmFbLnw7NWi6PTsw
    # excelparty@reliable-cacao-259921.iam.gserviceaccount.com

    count = 0
    bucket = storage_client.get_bucket('myphotomgr')
    for x in storage_client.list_blobs('myphotomgr'):

        if TEMP_NAME in x.name: continue

        action = check_existence(db, x.name)
        print('Action:' + action)

        if action == "duplicate":
            print("Duplicate and processed file: " + x.name)
            continue

        x.download_to_filename(TEMP_NAME, raw_download=True)

        data = extract_data_from_file_name(x.name)
        keywords = get_keywords(TEMP_NAME, data['title'])

        if data['title']:
            print("setting title:" + data['title'])
            modify_exif_title(TEMP_NAME, data['title'])
        modify_exif_keywords(TEMP_NAME, keywords.split(','))

        if action == "new":
            handle_new_picture(db, x.name, keywords)
        elif action == "pending":
            handle_modified_picture(db, x.name, keywords)
        else:
            raise Exception("unknown action type")

        db.commit()

        if AUTO_SUBMIT:
            session = ftplib.FTP('ftp.shutterstock.com',os.environ['SHUTTERSTOCK_USER'],os.environ['SHUTTERSTOCK_PASSWORD'])
            file = open(TEMP_NAME,'rb')
            session.storbinary('STOR ' + get_stripped_file_name(x.name), file)
            file.close()
            session.quit()

            cur = db.cursor()
            cur.execute("update ss_reviewed set state = 1, date_submitted = now() where ss_filename = %s ", (get_stripped_file_name(x.name),))

            db.commit()

        with open(TEMP_NAME, "rb") as pic:
            x.upload_from_file(pic)  # , predefined_acl='publicRead'
        #bucket.rename_blob(x,new_name=get_stripped_file_name(x.name))

        count += 1

    print('' + str(count) + ' file processed.')
    db.close()
