import base64
import os
import psycopg2
import requests
from google.cloud import storage
import PIL
from PIL import Image
import re
import exif

titleMatch = r'T#.*#T'
catMatch = r'C#[0-9]{1,2}'

TEMP_NAME = 'pic.keyworder.tmp'

def resize_img(name, basewidth):
    img = Image.open(name)
    wpercent = (basewidth / float(img.size[0]))
    hsize = int((float(img.size[1]) * float(wpercent)))
    img = img.resize((basewidth, hsize), PIL.Image.ANTIALIAS)
    img.save(name+'.resized.jpg', "JPEG",  quality = 80)

def set_title_in_exif(name, title):

    image_file = open(name, 'rb')
    my_image = exif.Image(image_file)
    my_image.title = title
    my_image.caption = title
    my_image.description = title
    image_file.close()

    with open(name, 'wb') as new_image_file:
        new_image_file.write(my_image.get_file())

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
# ss_data JSON
# );


def connect_database():
    # return psycopg2.connect(host="ec2-34-200-116-132.compute-1.amazonaws.com",
    #                         database="d42v6sfcnns36v",
    #                         user="uhztcmpnkqyhop",
    #                         password="c203bc824367be7762e38d1838b54448fe503f16fe34bb783d45a4a8bb370c00")

    return psycopg2.connect(os.environ["DATABASE_URL"])


def extract_data_from_file_name(filename):

    m = re.search(titleMatch, filename)
    title = filename[m.start()+2:m.end()-2] if m else None

    catList = re.findall(catMatch, filename)
    cat1 = catList[0][2:] if len(catList) > 0 else None
    cat2 = catList[1][2:] if len(catList) > 1 else None

    return {'title': title, 'cat1': cat1, 'cat2': cat2}


def get_stripped_file_name(filename):
    m = re.search(titleMatch, filename)
    filename = filename [:m.start()] + filename[m.end():]

    while True:
        m = re.search(catMatch, filename)
        if not m: break
        filename = filename [:m.start()] + filename[m.end():]

    return filename


def check_existence(db, filename):

    data = extract_data_from_file_name(filename)

    print('Extracted data:'+str(data))

    cur = db.cursor()
    cur.execute("select state, title, ss_cat1, ss_cat2 from ss_reviewed where ss_filename = %s ", (get_stripped_file_name(filename),))

    db_data = cur.fetchone()
    if not db_data:
        return "new"

    if db_data[0] == 0 and (data['title'] != db_data[1] or data['cat1'] != db_data[2] or data['cat2'] != db_data[3]):
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
    cur.execute("update ss_reviewed original_filename = %s, title = %s, kw_mykeyworder = %s, ss_cat1 = %s, ss_cat2 = %s where ss_filename  = %s)", (
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
        set_title_in_exif(temp_name + '.resized.jpg', title)

    d = bucket.blob(temp_name + '.jpg')
    with open(temp_name + '.resized.jpg', "rb") as pic:
        d.upload_from_file(pic, predefined_acl='publicRead')

    image_url = 'http://storage.googleapis.com/myphotomgr/'+temp_name+'.jpg'
    auth = bytes(os.environ['MYKEYWORDER_USER'], 'latin1') + b':' + bytes(os.environ['MYKEYWORDER_KEY'], 'latin1')
    headers = {'Authorization': b'Basic ' + base64.b64encode(auth)}

    response = requests.get('http://mykeyworder.com/api/v1/analyze', {'url': image_url}, headers=headers)

    data = response.json()

    print(str(data))

    keywords = ",".join(data['keywords'])

    print('kw:'+keywords)

#    d.delete()

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

    bucket = storage_client.get_bucket('myphotomgr')
    count = 0
    for x in storage_client.list_blobs('myphotomgr'):

        if TEMP_NAME + '.jpg' in x.name: continue

        action = check_existence(db, x.name)
        print('Action:' + action)

        if action == "duplicate":
            pass
            # todo: issue error
            print("Duplicate and processed file: " + x.name)
            continue

        x.download_to_filename(TEMP_NAME, raw_download=True)

        data = extract_data_from_file_name(x.name)
        keywords = get_keywords(TEMP_NAME, data['title'])

        if action == "new":
            handle_new_picture(db, x.name, keywords)
        elif action == "pending":
            handle_modified_picture(db, x.name, keywords)
        else:
            raise Exception("unknown action type")

        count += 1

    print('' + str(count) + ' file processed.')
