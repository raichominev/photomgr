import ftplib
import json
import os
import requests
from google.cloud import storage
import time
from shutterstock import ssCommon, kwCommon
import traceback
import sys

TO_SUBMIT_URL = "https://submit.shutterstock.com/api/content_editor/photo"
UPDATE_DETAILS_URL = 'https://submit.shutterstock.com/api/content_editor'

TEMP_NAME = 'pic.keyworder.tmp'

def handle_new_picture(db, data, filename, initial_filename):

    #data = ssCommon.extract_data_from_file_name(filename)

    cur = db.cursor()
    cur.execute("insert into ss_reviewed " +
                " (original_filename, title, kw_mykeyworder, ss_keywords, ss_filename, ss_cat1, ss_cat2, ss_location, initial_filename) " +
                " values(%s,%s,%s,%s,%s,%s,%s,%s, %s)", (
                    filename,
                    data['title'],
                    data['keywords'],
                    data['keywords'],
                    ssCommon.get_stripped_file_name(filename),
                    data['cat1'],
                    data['cat2'],
                    data['location'] if 'location' in data else None,
                    initial_filename
                ))
    cur.close()


def handle_modified_picture(db, data, filename):

    #data = ssCommon.extract_data_from_file_name(filename)

    cur = db.cursor()
    cur.execute("update ss_reviewed set original_filename = %s, title = %s, ss_keywords = %s, ss_cat1 = %s, ss_cat2 = %s, ss_location = %s where ss_filename  = %s", (
        filename,
        data['title'],
        data['keywords'],
        data['cat1'],
        data['cat2'],
        data['location'],
        ssCommon.get_stripped_file_name(filename)
    ))
    cur.close()




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
    cur.execute("select title, ss_keywords, ss_cat1, ss_cat2, ss_location, ss_filename from ss_reviewed where state = '1' ")

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
            update_json = '[{"categories":[' + ','.join(data['categories']) + '],"description":"' + data['title'].replace('"','\\"') + '","id":"'+ picture['id'] +\
                          '","is_adult":false,"is_editorial":false,"is_illustration":false,"keywords":[' + ','.join( ['"' + x + '"' for x in kwCommon.fix_keywords(data['keywords']) ] ) + '],"location":'+location+',"releases":[],"submitter_note":""}]'

            #print(str(json.dumps(update_json)))
            fix_list.pop(picture['original_filename'])
            print(update_json)
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

            if response.status_code != 200:
                raise Exception("Error updating data of file:"+picture['original_filename'])

            cur = db.cursor()
            cur.execute("update ss_reviewed set state = '10',  ss_title = %s,  "
                        "ss_cat1 = %s, ss_cat2 = %s, ss_location = %s where ss_filename = %s ",
                        (
                            data['title'],
                            data['categories'][0].replace('"','') if len(data['categories']) > 0 else None,
                            data['categories'][1].replace('"','') if len(data['categories']) > 1 else None,
                            json.dumps(data['location']) if data['location'] else None,
                            picture['original_filename'],))

            db.commit()

    #return remaining
    return fix_list


if __name__ == "__main__":

    try:
        if 'EXIF_TOOL' not in os.environ:
            os.environ['EXIF_TOOL'] = 'exiftool'

        db = ssCommon.connect_database()
        storage_client = ssCommon.get_storage_client()

        # GOOG1EUAMHFAI7RFWLLCFNT2KMBZ5DZRG2ERNBCUNNJFDIB4UZDWWUWUH7VDI
        #iNAHij6B2KPfrPNmllFUAfibpmFbLnw7NWi6PTsw
        # excelparty@reliable-cacao-259921.iam.gserviceaccount.com

        count = 0
        bucket = storage_client.get_bucket('myphotomgr')
        #fix_list = {}
        for x in storage_client.list_blobs('myphotomgr'):
            #print (x.name)
            if TEMP_NAME in x.name or 'sent/' in x.name: continue

            action = ssCommon.check_existence(db, x.name)
            print('Action:' + action)

            initial_filename = x.name
            if action == "duplicate":
                print("Duplicate and processed file: " + x.name)

                count = 1
                body, ext = os.path.splitext(initial_filename)
                while True:
                    if ssCommon.is_rework(initial_filename):
                        orig_name = os.path.splitext(ssCommon.get_stripped_file_name(initial_filename, True))[0]
                    else:
                        orig_name = os.path.splitext(ssCommon.get_stripped_file_name(initial_filename))[0]
                    print('orig_name:' + orig_name)
                    x = bucket.rename_blob(x,new_name=body.replace(orig_name, orig_name+str(count)) + ext)
                    print('Expected:'+body.replace(orig_name, orig_name+str(count)) + ext)
                    print('New name:' + x.name)
                    action = ssCommon.check_existence(db, x.name)
                    if action != "duplicate":
                         break
                    count += 1

            x.download_to_filename(TEMP_NAME, raw_download=True)

            data = ssCommon.extract_data_from_file_name(x.name)

            if ssCommon.is_rework(x.name):
                print("Handling reworked picture: " + x.name + " Original:" + ssCommon.get_rework_original_file_name(x.name))
                cur = db.cursor()
                cur.execute("select ss_title, ss_cat1, ss_cat2, ss_keywords, ss_location from ss_reviewed where ss_filename = %s ", (ssCommon.get_rework_original_file_name(x.name),))
                db_data = cur.fetchone()
                if not db_data:
                    raise Exception('Original not found for:' + x.name + ' Searching it as:' + ssCommon.get_rework_original_file_name(x.name))

                if not data['title']:
                    data['title'] = db_data[0]

                if not data['cat1']:
                    data['cat1'] = db_data[1]
                if not data['cat2']:
                    data['cat2'] = db_data[2]

                data['keywords'] = db_data[3]
                data['location'] = db_data[4]
            elif action == 'pending':
                # get keywords & title & locatyion & cat from ss_* - if already present - they were placed there from ee
                # blend with data from filename/in case of difference

                cur = db.cursor()
                cur.execute("select ss_title, ss_cat1, ss_cat2, ss_keywords, ss_location from ss_reviewed where ss_filename = %s ", (ssCommon.get_stripped_file_name(initial_filename),))
                db_data = cur.fetchone()
                if not db_data:
                    raise Exception('Original not found for:' + x.name + ' Searching it as:' + ssCommon.get_stripped_file_name(initial_filename))

                if not data['title']:
                    data['title'] = db_data[0]

                if not data['cat1']:
                    data['cat1'] = db_data[1]
                if not data['cat2']:
                    data['cat2'] = db_data[2]

                data['keywords'] = db_data[3]
                data['location'] = db_data[4]

            else:
                if not data['keywords']:
                    data['keywords'] = kwCommon.get_keywords(storage_client, TEMP_NAME, data['title'])

                if data['locationShort']:
                    data['location'] = ssCommon.lookup_location_by_code(db, data['locationShort'])

            # now setting through ss
            # if data['title']:
            #     print("setting title:" + data['title'])
            #     modify_exif_title(TEMP`_NAME, data['title'])
            # modify_exif_keywords(TEMP_NAME, keywords.split(','))

            if action == "new":
                handle_new_picture(db, data, x.name, initial_filename)
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

                # copy blob to the sent folder - removed 26.04.2020
                #sent = bucket.blob("sent/"+x.name)
                #with open(TEMP_NAME, "rb") as pic:
                #    sent.upload_from_file(pic)  # , predefined_acl='publicRead'
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

            cur = db.cursor()
            cur.execute("select state from ss_reviewed where state = '1' ")

            # only execure when there are pictures for processing. This will work both for the just processed pics and for
            # ones that were unfinieshed from previous processing
            if cur.fetchone():

                print('Sleeping ' + os.environ['SS_AUTO_UPLOAD_FIX_WAIT_TIME'] + ' sec.')
                time.sleep(int(os.environ['SS_AUTO_UPLOAD_FIX_WAIT_TIME']))
                ssCommon.ss_login()
                #print(str(fix_list))
                remainingFiles = updatePicDescription()

                # try to do that once more if not all files
                if len(remainingFiles):

                    print(str(len(remainingFiles)) + ' not found. Sleeping.')
                    time.sleep(int(os.environ['SS_AUTO_UPLOAD_FIX_WAIT_TIME']))
                    remainingCount = updatePicDescription()
                    if remainingCount:
                        print("WARNING. Some files not found.")
                        for file in remainingFiles.keys():
                            print(file)

                print('' + str(count - len(remainingFiles)) + ' files post-processed.')

        db.close()
        print('Processing finished.')

    except SystemExit:
        raise
    except:
        exception_data = ''.join(traceback.format_exception(*sys.exc_info()))
        ssCommon.handleException(exception_data, "processNewPics")
        raise
