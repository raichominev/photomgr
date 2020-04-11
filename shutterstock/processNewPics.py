import base64
import ftplib
import json
import os
from datetime import datetime
import requests
from google.cloud import storage
import PIL
from PIL import Image
import time
import exiftool
from shutterstock import ssCommon

TO_SUBMIT_URL = "https://submit.shutterstock.com/api/content_editor/photo"
UPDATE_DETAILS_URL = 'https://submit.shutterstock.com/api/content_editor'

TEMP_NAME = 'pic.keyworder.tmp'

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
    print(EXIF_TOOL)
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


def check_existence(db, filename):

    data = ssCommon.extract_data_from_file_name(filename)

    print('Extracted data:'+str(data))

    cur = db.cursor()
    cur.execute("select state, title, ss_cat1, ss_cat2 from ss_reviewed where ss_filename = %s ", (ssCommon.get_stripped_file_name(filename),))

    db_data = cur.fetchone()
    if not db_data:
        return "new"

    if db_data[0] in (0,1) or (db_data[0] == 10 and (str(data['title']) != str(db_data[1]) or str(data['cat1']) != str(db_data[2]) or str(data['cat2']) != str(db_data[3]))):
        return "pending"

    cur.close()
    return "duplicate"


def handle_new_picture(db, data, filename):

    #data = ssCommon.extract_data_from_file_name(filename)

    cur = db.cursor()
    cur.execute("insert into ss_reviewed " +
                " (original_filename, title, kw_mykeyworder, ss_filename, ss_cat1, ss_cat2, ss_location) " +
                " values(%s,%s,%s,%s,%s,%s,%s)", (
                    filename,
                    data['title'],
                    data['keywords'],
                    ssCommon.get_stripped_file_name(filename),
                    data['cat1'],
                    data['cat2'],
                    data['location'] if 'location' in data else None
                ))
    cur.close()


def handle_modified_picture(db, data, filename):

    #data = ssCommon.extract_data_from_file_name(filename)

    cur = db.cursor()
    cur.execute("update ss_reviewed set original_filename = %s, title = %s, kw_mykeyworder = %s, ss_cat1 = %s, ss_cat2 = %s, ss_location = %s where ss_filename  = %s", (
        filename,
        data['title'],
        data['keywords'],
        data['cat1'],
        data['cat2'],
        data['location'],
        ssCommon.get_stripped_file_name(filename)
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

    #print('kw:'+keywords)

    d.delete()

    return keywords


def updatePicDescription():
    ####################################################################
    # get list of waiting files
    response = requests.get(
        TO_SUBMIT_URL,
        params={'status': 'edit', 'xhr_id': '1', 'page_number': '1', 'per_page': '100', 'order': 'newest'},
        cookies=ssCommon.cookie_dict,
        headers=ssCommon.DEFAULT_HEADERS
    )

    #print(response.url)
    print(response)

    json_response = response.json()

    cur = db.cursor()
    cur.execute("select title, kw_mykeyworder, ss_cat1, ss_cat2, ss_location, ss_filename from ss_reviewed where state = '1' ")

    fix_list = {}
    for data in cur.fetchall():
        catList=[]
        if data[2]: catList.append('"' + str(data[2])+'"')
        if data[3]: catList.append('"' + str(data[3])+'"')
        kw = ['"' + kw + '"' for kw in data[1].split(',')]
        fix_list[data[5]] = {'title':data[0], 'keywords': kw, 'categories':catList, 'location': data[4] }

    ####################################################################
    # scan for files to fix
    for picture in json_response['data']:

        if picture['original_filename'] in fix_list:

            print('Updating desc ' + picture['original_filename'])
            data = fix_list[picture['original_filename']]
            # update_json = '{"media":[{"id":"' + picture['id'] + '","media_type":"photo","case_number":"","categories":[' + ','.join(data['categories']) + '],"keywords":[' + ','.join( data['keywords'] ) + '],"submitter_note":"","title":"' + data['title'] + '"}]}'

            location = '{"collected_full_location_string":"","english_full_location":"","external_metadata":""}'
            if 'location' in data and data['location']:
                location = data['location']
            update_json = '[{"categories":[' + ','.join(data['categories']) + '],"description":"' + data['title'] + '","id":"'+ picture['id'] +\
                          '","is_adult":false,"is_editorial":false,"is_illustration":false,"keywords":[' + ','.join( data['keywords'] ) + '],"location":'+location+',"releases":[],"submitter_note":""}]'

            # print(str(json.dumps(update_json)))
            fix_list.pop(picture['original_filename'])
            # print(update_json)
            hdr = {}
            hdr.update(ssCommon.DEFAULT_HEADERS)
            hdr.update({'content-type': 'application/json', 'accept-encoding': 'gzip, deflate, br', 'accept-language':'en-US,en;q=0.5',
                                                   'accept':'application/json', 'connection':'keep-alive', 'origin':'https://submit.shutterstock.com',
                                                   'referer':'https://submit.shutterstock.com/edit?language=en&sort=newest&type=photo'})
            # print(str(hdr))
            response = requests.patch(
                UPDATE_DETAILS_URL,
                data=update_json,
                cookies=ssCommon.cookie_dict,
                headers=hdr
            )
            print(response)
            print(response.json())
            # todo: check result

            cur = db.cursor()
            cur.execute("update ss_reviewed set state = '10' where ss_filename = %s ",
                        (picture['original_filename'],))

            db.commit()

    #return remaining
    return fix_list

if __name__ == "__main__":
    global EXIF_TOOL

    if 'EXIF_TOOL' in os.environ:
        EXIF_TOOL = os.environ['EXIF_TOOL']
    else:
        EXIF_TOOL = 'exiftool'

    db = ssCommon.connect_database()

    f = open('cloud_auth.txt','w+')
    f.write(os.environ['CLOUD_STORE_API'])
    f.close()

    storage_client = storage.Client.from_service_account_json('cloud_auth.txt')

    # GOOG1EUAMHFAI7RFWLLCFNT2KMBZ5DZRG2ERNBCUNNJFDIB4UZDWWUWUH7VDI
    #iNAHij6B2KPfrPNmllFUAfibpmFbLnw7NWi6PTsw
    # excelparty@reliable-cacao-259921.iam.gserviceaccount.com

    count = 0
    bucket = storage_client.get_bucket('myphotomgr')
    #fix_list = {}
    for x in storage_client.list_blobs('myphotomgr'):
        #print (x.name)
        if TEMP_NAME in x.name or 'sent/' in x.name: continue

        action = check_existence(db, x.name)
        print('Action:' + action)

        if action == "duplicate":
            print("Duplicate and processed file: " + x.name)
            continue

        x.download_to_filename(TEMP_NAME, raw_download=True)

        data = ssCommon.extract_data_from_file_name(x.name)

        if ssCommon.is_rework(x.name):
            print("Handling reworked picture: " + x.name)
            cur = db.cursor()
            cur.execute("select ss_title, ss_cat1, ss_cat2, ss_keywords, ss_location from ss_reviewed where ss_filename = %s ", (ssCommon.get_rework_original_file_name(x.name),))
            db_data = cur.fetchone()

            if not data['title']:
                data['title'] = db_data[0]

            if not data['cat1']:
                data['cat1'] = db_data[1]
            if not data['cat2']:
                data['cat2'] = db_data[2]

            data['keywords'] = db_data[3]
            data['location'] = db_data[4]
        else:
            data['keywords'] = get_keywords(TEMP_NAME, data['title'])

        # now setting through ss
        # if data['title']:
        #     print("setting title:" + data['title'])
        #     modify_exif_title(TEMP`_NAME, data['title'])
        # modify_exif_keywords(TEMP_NAME, keywords.split(','))

        if action == "new":
            handle_new_picture(db, data, x.name)
        elif action == "pending":
            handle_modified_picture(db, data, x.name)
        else:
            raise Exception("unknown action type")

        db.commit()

        if os.environ['SS_AUTO_UPLOAD'] == 'True':
            session = ftplib.FTP('ftp.shutterstock.com',os.environ['SHUTTERSTOCK_USER'],os.environ['SHUTTERSTOCK_PASSWORD'])
            file = open(TEMP_NAME,'rb')
            session.storbinary('STOR ' + ssCommon.get_stripped_file_name(x.name), file)
            file.close()
            session.quit()

            cur = db.cursor()
            cur.execute("update ss_reviewed set state = 1 where ss_filename = %s ",
                        (ssCommon.get_stripped_file_name(x.name),))

            db.commit()

            # copy blob to the sent folder
            sent = bucket.blob("sent/"+x.name)
            with open(TEMP_NAME, "rb") as pic:
                sent.upload_from_file(pic)  # , predefined_acl='publicRead'
            x.delete()
            #bucket.rename_blob(x,new_name=get_stripped_file_name(x.name))

            #catList=[]
            #if data['cat1']: catList.append('"' + str(data['cat1'])+'"')
            #if data['cat2']: catList.append('"' + str(data['cat2'])+'"')
            #kw = ['"' + kw + '"' for kw in keywords.split(',')]
            #fix_list[ssCommon.get_stripped_file_name(x.name)] = {'title':data['title'], 'keywords': kw, 'categories':catList, 'location': data['location'] }

        count += 1
    print('' + str(count) + ' files processed.')

    if os.environ['SS_AUTO_UPLOAD'] == 'True':

        print('Sleeping ' + os.environ['SS_AUTO_UPLOAD_FIX_WAIT_TIME'] + ' sec.')
        time.sleep(int(os.environ['SS_AUTO_UPLOAD_FIX_WAIT_TIME']))
        ssCommon.ss_login()
        #print(str(fix_list))
        remainingFiles =  updatePicDescription()

        # try to do that once more if not all files
        if len(remainingFiles):

            print(str(len(remainingFiles)) + ' not found. Sleeping.')
            time.sleep(int(os.environ['SS_AUTO_UPLOAD_FIX_WAIT_TIME']))
            remainingCount = updatePicDescription()
            if remainingCount:
                print("WARNING. Some files not found.")
                for file, data in remainingFiles:
                    print(file)

        print('' + str(count - len(remainingFiles)) + ' files post-processed.')
    db.close()
