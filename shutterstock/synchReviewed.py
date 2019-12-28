import json
import shutil
from os.path import exists, join

from tinydb import TinyDB, Query
from selenium import webdriver
import exiftool

BASE_FOLDER = "G:\\shutterwork"

FOLDER_UNDER_REVIEW = BASE_FOLDER + "\\" + "underReview"
FOLDER_TO_SUBMIT = BASE_FOLDER + "\\" + "tosubmit"
FOLDER_REVIEWED = BASE_FOLDER + "\\" + "reviewed"
FOLDER_REJECTED = BASE_FOLDER + "\\" + "rejected"
FOLDER_FORUPLOAD = BASE_FOLDER + "\\" + "forupload"

DB_FILE = BASE_FOLDER + "\\" + "db.json"
LOGIN_COOKIES_DB_FILE = BASE_FOLDER + "\\" + "login.txt"

EXIF_TOOL = BASE_FOLDER + "\\" + "exiftool.exe"

BASE_URL = "https://submit.shutterstock.com"
CATEGORIES_URL = "https://submit.shutterstock.com/api/content_editor/categories/photo"
REVIEWED_URL = "https://submit.shutterstock.com/api/content_editor/photo?order=newest&per_page=100&page=1&status=reviewed&xhr_id=1"
CATEGORY_URL = "https://submit.shutterstock.com/api/content_editor/categories/photo"
NOTES_URL = "https://submit.shutterstock.com/api/content_editor/note_types"

def ini():

    driver = webdriver.Chrome("c:\\data\\chromedriver\\chromedriver_77.0.3865.40.exe")
    db = TinyDB(DB_FILE)

    driver.get(BASE_URL)
    #driver.delete_all_cookies()

#    print(driver.get_cookies())
    with open(LOGIN_COOKIES_DB_FILE) as f:
        cookies = f.readline()
#        cookie_dict = {}
        #print(driver.get_cookies())
        for c in cookies.split(';'):
          name,val = c.split('=')
          name = name.strip()
          val = val.strip()
#          cookie_dict[name] = val
 #         if not driver.get_cookie(name) and name not in ('visit_id','locale'):
#              print ("*"+name+"*","::", val)
          driver.add_cookie({'name':name, 'value':val})
#              sleep(1)

    print(driver.get_cookies())
    return driver,db

def upload_ready_files(driver, db):
    # todo: after uploading set categories, if present
    pass

def upload_ready_files(driver, db):
    pass

def load_reviewed_files(driver, db):

    ##############################
    # GET MAIN DATA LIST
    driver.get(REVIEWED_URL)

    if "{\"data\"" not in driver.page_source:
        print("not logged in")
        return

    print(driver.find_element_by_tag_name("pre").text)
    review_json = json.loads(driver.find_element_by_tag_name("pre").text)


    ##############################
    # GET AUXILIARY  DATA LIST
    driver.get(CATEGORY_URL)
    category_json = json.loads(driver.find_element_by_tag_name("pre").text)
    categories = dict((ct['cat_id'],ct) for ct in category_json['data'])

    print(json.dumps(categories))

    driver.get(NOTES_URL)
    reasons_json = json.loads(driver.find_element_by_tag_name("pre").text)
    reasons = dict((ct['id'],ct['name']) for ct in reasons_json['data'])

    print(json.dumps(reasons))

    ##############################
    # GET AUXILIARY  DATA LIST

    for picture in review_json['data']:
        if exists(join(FOLDER_UNDER_REVIEW, picture['original_filename'])):

            jpg_name = join(FOLDER_UNDER_REVIEW, picture['original_filename'])
            dng_name = join(FOLDER_UNDER_REVIEW + "\\dng", picture['original_filename'].replace('.jpg','.dng'))

            subject = ";".join(categories[int(ctg)]['name'] for ctg in picture['categories'])
            reason = ";".join(reasons[ctg['reason']] for ctg in picture['reasons']) if 'reasons' in picture else ''

            modification_list = (
                    (
                        b'-delete_original',
                        b'-makernotes=.',
                        b'-description=' + bytes(picture['description'],encoding='latin1'),
                        b'-caption=' + bytes(picture['description'],'latin1'),
                        b'-title=' + bytes(picture['description'],'latin1'),
                        b'-imagedescription=' + bytes(subject,'latin1'),
                        b'-ImageUniqueID=' + bytes(str(picture['media_id']),'latin1'),
                        b'-ImageID=' + bytes(str(picture['media_id']),'latin1'),
                        b'-UserComment=' + bytes(json.dumps(picture),'latin1'),
                        b'-copyright=' + bytes(reason,'latin1'),
                        b'keywords=',
                    ) +
                    tuple(b'-keywords=' + bytes(kwd,encoding='latin1') for kwd in picture['keywords'])
            )

            with exiftool.ExifTool(EXIF_TOOL) as et:
                et.execute( * ( modification_list + (bytes(jpg_name, encoding='latin1'),)) )
                et.execute( * ( modification_list + (bytes(dng_name, encoding='latin1'),)) )

            if picture['status'] == 'approved':
                print(json.dumps(picture))

                db.table("reviewed").insert(picture)

                shutil.move(jpg_name, FOLDER_REVIEWED)
                shutil.move(dng_name, FOLDER_REVIEWED + "\\dng")

            else:

                print("REJECTED " + json.dumps(picture))

                db.table("rejected").insert(picture)

                shutil.move(join(FOLDER_UNDER_REVIEW, picture['original_filename']), FOLDER_REJECTED )
                shutil.move(join(FOLDER_UNDER_REVIEW + "\\dng", picture['original_filename'].replace('.jpg','.dng')), FOLDER_REJECTED + "\\dng")


if __name__ == "__main__":
    driver,db = ini()
    load_reviewed_files(driver,db)