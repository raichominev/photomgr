import requests
import json

from os.path import exists, join
import MySQLdb
import exiftool

BASE_FOLDER = "C:\\Users\\user-pc2\\Desktop\\shutterstock"
DEFAULT_HEADERS = {'User-Agent' : 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:71.0) Gecko/20100101 Firefox/71.0'}



LOGIN_COOKIES_DB_FILE = BASE_FOLDER + "\\" + "login.txt"

CATALOG_URL = "https://submit.shutterstock.com/api/catalog_manager/media_types/all/items"
CATALOG_ITEM_URL = "https://submit.shutterstock.com/api/content_editor/media/P"

CATEGORY_URL = "https://submit.shutterstock.com/api/content_editor/categories/photo"
NOTES_URL = "https://submit.shutterstock.com/api/content_editor/note_types"

#FOLDER_UNDER_REVIEW = BASE_FOLDER + "\\" + "underReview"
#FOLDER_TO_SUBMIT = BASE_FOLDER + "\\" + "tosubmit"
FOLDER_REVIEWED = BASE_FOLDER + "\\" + "submitted"
#FOLDER_REJECTED = BASE_FOLDER + "\\" + "rejected"
#FOLDER_FORUPLOAD = BASE_FOLDER + "\\" + "forupload"

EXIF_TOOL = "G:\\shutterwork" + "\\" + "exiftool.exe"

cookie_dict = {}
categories = None
reasons = None

def ini():
    global categories
    global reasons

    with open(LOGIN_COOKIES_DB_FILE) as f:
        cookies = f.readline()
        for c in cookies.split(';'):
            name,val = c.split('=',1)
            cookie_dict[name.strip()] = val.strip()

    ##############################
    # GET AUXILIARY  DATA LIST
    response = requests.get(CATEGORY_URL, cookies=cookie_dict, headers=DEFAULT_HEADERS)
    category_json = response.json()
    categories = dict((ct['cat_id'],ct) for ct in category_json['data'])

    print(json.dumps(categories))

    response = requests.get(NOTES_URL, cookies=cookie_dict, headers=DEFAULT_HEADERS)
    reasons_json = response.json()
    reasons = dict((ct['id'],ct['name']) for ct in reasons_json['data'])

    print(json.dumps(reasons))


def load_catalog_files(db):

    page = 1
    count = 0
    while True:
        response = requests.get(
            CATALOG_URL,
            params={'filter_type': 'keywords', 'filter_value': '', 'page_number':str(page), 'per_page': '100', 'sort':'newest'},
            cookies=cookie_dict,
            headers=DEFAULT_HEADERS
        )
        print(response.url)

        print(response)
        json_response = response.json()

        # print(json.dumps(json_response, indent = 4))
        print("Records for processing:" + str(len(json_response['data'])))
        if not len(json_response['data']):
            break
        page+=1

        ###############################################################
        # read catalog
        # check if exists in database
        # compare for changes
        # insert or update in picture file
        for picture in json_response['data']:

            response_pic = requests.get(CATALOG_ITEM_URL + picture['media_id'], cookies=cookie_dict, headers=DEFAULT_HEADERS)
            detailed_pic = response_pic.json()

            cur = db.cursor()
            cur.execute("SELECT ID,JSON_DATA FROM ss_reviewed where media_id = " + picture['media_id'])
            db_data = cur.fetchone()

            #print(json.dumps(detailed_pic, indent = 4))
            count +=1
            print('Record No:'+str(count) + " " + detailed_pic['data']['original_filename'])

            if db_data is None:

#                if exists(join(FOLDER_REVIEWED, detailed_pic['data']['original_filename'])):
#                    #print('Found:' + detailed_pic['data']['original_filename'])
#                    if not modify_exif_data(detailed_pic['data']):
#                        continue

                handle_new_picture(detailed_pic['data'])

            elif db_data[1] != json.dumps(detailed_pic['data']):

                if exists(join(FOLDER_REVIEWED, detailed_pic['data']['original_filename'])):
                    #print('Found:' + detailed_pic['data']['original_filename'])
                    if not modify_exif_data(detailed_pic['data']):
                        continue

                handle_modified_picture(detailed_pic['data'])

def handle_new_picture(picture):
    cur = db.cursor()
    cur.execute("insert into ss_reviewed (original_filename, media_id, title, keywords, json_data) values(%s,%s,%s,%s,%s)", (
        picture['original_filename'],
        picture['id'][1:],
        picture['description'],
        ';'.join(picture['keywords']),
        json.dumps(picture)
    ))

def handle_modified_picture(picture):
    cur = db.cursor()
    cur.execute("update ss_reviewed set original_filename = %s, media_id = %s, title = %s, keywords = %s, json_data = %s)", (
        picture['original_filename'],
        picture['id'][1:],
        picture['description'],
        ';'.join(picture['keywords']),
        json.dumps(picture)
    ))

def modify_exif_data(picture):

    jpg_name = join(FOLDER_REVIEWED, picture['original_filename'])
    dng_name = join(FOLDER_REVIEWED + "_dng", picture['original_filename'].replace('.jpg','.dng'))

    subject = ";".join(categories[int(ctg)]['name'] for ctg in picture['categories'])
    reason = ";".join(reasons[ctg['reason']] for ctg in picture['reasons']) if 'reasons' in picture else ''

    print('=======================================================================')
    print(jpg_name)
    print(picture['description'])
    print(subject)
    print(reason)


    modification_list = (
            (
                b'-overwrite_original',
                b'-makernotes=.',
                b'-description=' + bytes(picture['description'],encoding='latin1'),
                b'-caption=' + bytes(picture['description'],'latin1'),
                b'-title=' + bytes(picture['description'],'latin1'),
                b'-imagedescription=' + bytes(subject,'latin1'),
                b'-ImageUniqueID=' + bytes(str(picture['id'][1:]),'latin1'),
                b'-ImageID=' + bytes(str(picture['id'][1:]),'latin1'),
                b'-UserComment=' + bytes(json.dumps(picture),'latin1'),
                b'-copyright=' + bytes(reason,'latin1'),
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

    db = MySQLdb.connect(host="laranart.com",    # your host, usually localhost
                         user="larana6_wo632",         # your username
                         passwd="ias_j2ee",  # your password
                         db="larana6_wo632")        # name of the data base

    # # you must create a Cursor object. It will let
    # #  you execute all the queries you need
    # cur = db.cursor()
    #
    # # Use all the SQL you like
    # cur.execute("SELECT * FROM wp_users")
    #
    # # print all the first cell of all the rows
    # for row in cur.fetchall():
    #     print (str(row))

    ini()
    load_catalog_files(db)

    db.close()



# Catalog JSON structure:

# {
#     "media_id": "1513267829",
#     "details": {
#         "id": 1513267829,
#         "submitter_id": 238906963,
#         "description": "Girl passing under an artificial waterfall in pool.",
#         "preview": {
#             "url": "https://image.shutterstock.com/display_pic_with_logo/238906963/1513267829/stock-photo-girl-passing-under-an-artificial-waterfall-in-pool-1513267829.jpg",
#             "width": 450,
#             "height": 300
#         },
#         "small_thumb": {
#             "url": "https://thumb1.shutterstock.com/thumb_small/238906963/1513267829/stock-photo-girl-passing-under-an-artificial-waterfall-in-pool-1513267829.jpg",
#             "width": 100,
#             "height": 67
#         },
#         "large_thumb": {
#             "url": "https://thumb1.shutterstock.com/thumb_large/238906963/1513267829/stock-photo-girl-passing-under-an-artificial-waterfall-in-pool-1513267829.jpg",
#             "width": 150,
#             "height": 100
#         },
#         "mosaic_250": {
#             "url": "https://image.shutterstock.com/image-photo/girl-passing-under-artificial-waterfall-250nw-1513267829.jpg",
#             "width": 250,
#             "height": 167
#         },
#         "aspect": 1.4984,
#         "media_type": "photo",
#         "status": "approved",
#         "preview_image_url": "https://image.shutterstock.com/image-photo/girl-passing-under-artificial-waterfall-250nw-1513267829.jpg",
#         "keywords": [
#            "water wall", "hands", "young", "summer", "wave", "fall", "waterfall", "action", "vacation", "sunny", "leisure", "moving",
#            "rest", "recreation", "wet", "pool", "pour", "active", "sunlit", "swimmer", "girl", "water", "shine", "lifestyle", "outdoor",
#            "face", "blue", "light", "outside", "person", "underwater", "passing", "under", "movement", "splash", "sport", "fun", "swim"
#         ]
#     }
# },





###############################################
# detailed data

# {
#     "data": {
#         "aspect": 1.4984,
#         "categories": [
#             "1",
#             "10"
#         ],
#         "cdn_image": {
#             "width": 0,
#             "height": 0,
#             "url": "https://image.shutterstock.com/image-photo/closeup-bee-hive-alternative-upper-[SIZE]-1524810485.jpg"
#         },
#         "content_tiers": [],
#         "dependent_upload_legacy_id": null,
#         "description": "Closeup of bee hive alternative upper entrance. Bees returning from flight.",
#         "discipled": 1,
#         "display_1500": {
#             "height": 1001,
#             "width": 1500,
#             "url": "https://image.shutterstock.com/z/stock-photo-closeup-of-bee-hive-alternative-upper-entrance-bees-returning-from-flight-1524810485.jpg"
#         },
#         "filename": "1524810485.jpg",
#         "has_model_release": null,
#         "has_property_release": null,
#         "id": "P1524810485",
#         "is_editorial": false,
#         "is_illustration": false,
#         "keywords": [
#             "animal",
#             "apiary",
#             "bee",
#             "beehive",
#             "beekeeping",
#             "bees",
#             "blue",
#             "bright",
#             "carry",
#             "cast",
#             "close",
#             "close-up",
#             "closeup",
#             "cluster",
#             "color",
#             "crawl",
#             "dirty",
#             "entrance",
#             "entry",
#             "gather",
#             "group",
#             "hive",
#             "honey",
#             "horizontal",
#             "insects",
#             "land",
#             "macro",
#             "many",
#             "material",
#             "old",
#             "paint",
#             "plate",
#             "rectangle",
#             "rectangular",
#             "rustic",
#             "shade",
#             "styrofoam",
#             "sun",
#             "sunlit",
#             "sunny",
#             "surface",
#             "village",
#             "walk",
#             "wild",
#             "wings",
#             "worn"
#         ],
#         "large_thumb": {
#             "width": 150,
#             "height": 100,
#             "url": "https://thumb9.shutterstock.com/thumb_large/238906963/1524810485/stock-photo-closeup-of-bee-hive-alternative-upper-entrance-bees-returning-from-flight-1524810485.jpg"
#         },
#         "location": {},
#         "margin": "",
#         "md5": "cbb61473ac762d9786fc3782b610a0ed",
#         "media_type": "image",
#         "model_release_info": null,
#         "original_filename": "DSC_6424.jpg",
#         "preview": {
#             "height": 300,
#             "width": 450,
#             "url": "https://image.shutterstock.com/display_pic_with_logo/238906963/1524810485/stock-photo-closeup-of-bee-hive-alternative-upper-entrance-bees-returning-from-flight-1524810485.jpg"
#         },
#         "releases": [],
#         "sizes": {
#             "huge_jpg": {
#                 "width": 7360,
#                 "height": 4912,
#                 "dpi": 300,
#                 "format": "jpg",
#                 "width_cm": "62.3 cm",
#                 "height_cm": "41.6 cm",
#                 "width_in": "24.5\"",
#                 "height_in": "16.4\"",
#                 "name": "huge_jpg",
#                 "display_name": "Huge",
#                 "size_in_bytes": 43490784,
#                 "human_readable_size": "41.5 MB"
#             },
#             "huge_tiff": {
#                 "width": 7360,
#                 "height": 4912,
#                 "dpi": 300,
#                 "format": "tiff",
#                 "width_cm": "62.3 cm",
#                 "height_cm": "41.6 cm",
#                 "width_in": "24.5\"",
#                 "height_in": "16.4\"",
#                 "name": "huge_tiff",
#                 "display_name": "Huge",
#                 "size_in_bytes": 108456960,
#                 "human_readable_size": "103.4 MB"
#             },
#             "medium_jpg": {
#                 "width": 1000,
#                 "height": 667,
#                 "dpi": 300,
#                 "format": "jpg",
#                 "width_cm": "8.5 cm",
#                 "height_cm": "5.6 cm",
#                 "width_in": "3.3\"",
#                 "height_in": "2.2\"",
#                 "name": "medium_jpg",
#                 "display_name": "Med",
#                 "size_in_bytes": 1207655,
#                 "human_readable_size": "1.2 MB"
#             },
#             "small_jpg": {
#                 "width": 500,
#                 "height": 334,
#                 "dpi": 300,
#                 "format": "jpg",
#                 "width_cm": "4.2 cm",
#                 "height_cm": "2.8 cm",
#                 "width_in": "1.7\"",
#                 "height_in": "1.1\"",
#                 "name": "small_jpg",
#                 "display_name": "Small",
#                 "size_in_bytes": 309670,
#                 "human_readable_size": "302 KB"
#             }
#         },
#         "small_thumb": {
#             "width": 100,
#             "height": 67,
#             "url": "https://thumb9.shutterstock.com/thumb_small/238906963/1524810485/stock-photo-closeup-of-bee-hive-alternative-upper-entrance-bees-returning-from-flight-1524810485.jpg"
#         },
#         "status": "approved",
#         "submitter_note": null,
#         "upload_id": 1776318941,
#         "upload_legacy_id": 1824489893,
#         "uploaded_date": "2019-10-07",
#         "channels": [
#             "shutterstock"
#         ],
#         "vector_extension": null,
#         "legacy_id": 1824489893,
#         "thumbnail_url": "//image.shutterstock.com/image-photo/closeup-bee-hive-alternative-upper-250nw-1524810485.jpg",
#         "thumbnail_url_480": "https://cdn.shutterstock.com/shutterstock/pending_photos/1824489893/thumb_480x270.jpg",
#         "is_adult": false,
#         "contributor_id": 238906963
#     }
# }