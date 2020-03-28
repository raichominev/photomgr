import os
from datetime import datetime
import requests
import json
from os.path import exists, join
import exiftool
from shutterstock import ssCommon

CATALOG_URL = "https://submit.shutterstock.com/api/catalog_manager/media_types/all/items"
CATALOG_ITEM_URL = "https://submit.shutterstock.com/api/content_editor/media/P"

def load_catalog_files(db):

    page = 1
    count = 0
    while True:
        response = requests.get(
            CATALOG_URL,
            params={'filter_type': 'keywords', 'filter_value': '', 'page_number':str(page), 'per_page': '100', 'sort':'newest'},
            cookies=ssCommon.cookie_dict,
            headers=ssCommon.DEFAULT_HEADERS
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

            response_pic = requests.get(CATALOG_ITEM_URL + picture['media_id'], cookies=ssCommon.cookie_dict, headers=ssCommon.DEFAULT_HEADERS)
            detailed_pic = response_pic.json()

            cur = db.cursor()
            cur.execute("SELECT ID,ss_DATA, original_filename FROM ss_reviewed where ss_media_id = " + picture['media_id'])
            db_data = cur.fetchone()

            #print(json.dumps(detailed_pic, indent = 4))
            count +=1
            print('Record No:'+str(count) + " " + detailed_pic['data']['original_filename'] + ' Media id:' + picture['media_id'])

            if db_data is None:

#                if exists(join(ssCommon.FOLDER_REVIEWED, detailed_pic['data']['original_filename'])):
#                    #print('Found:' + detailed_pic['data']['original_filename'])
#                    if not modify_exif_data(detailed_pic['data']):
#                        continue

                print('=======================================')
                print('New image...')

                handle_new_picture(detailed_pic['data'])

                if not exists(join(ssCommon.FOLDER_REVIEWED, detailed_pic['data']['original_filename'])):
                    print('Missing...')
                    cur = db.cursor()
                    cur.execute("update ss_reviewed set kw_keywordsready = 'missing' where ss_media_id = %s ", (detailed_pic['data']['id'][1:],))
                    db.commit()

            elif json.dumps(db_data[1]) != json.dumps(detailed_pic['data']):
                print('=======================================')
                print('Change uncovered. Updating...')
                if exists(join(ssCommon.FOLDER_REVIEWED, db_data[2])):
                    #print('Found:' + detailed_pic['data']['original_filename'])
                    if not modify_exif_data(detailed_pic['data'], db_data[2]):
                        exit(1)

                handle_modified_picture(detailed_pic['data'])
            else:
                print("Up to date.")

def handle_new_picture(picture):
    cur = db.cursor()
    cur.execute("insert into ss_reviewed (original_filename, ss_filename, ss_media_id, ss_title, ss_keywords, ss_cat1, ss_cat2, ss_data, ss_location, ss_status, date_reviewed, state) values(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s, 50)", (
        picture['original_filename'],
        picture['original_filename'],
        picture['id'][1:],
        picture['description'],
        ','.join(picture['keywords']),
        picture['categories'][0] if len(picture['categories'])> 0 else None,
        picture['categories'][1] if len(picture['categories'])> 1 else None,
        json.dumps(picture),
        json.dumps(picture['location']),
        'approved',
        datetime.strptime(picture['uploaded_date'], '%Y-%m-%d'),
    ))
    db.commit()

def handle_modified_picture(picture):
    cur = db.cursor()
    cur.execute("update ss_reviewed set ss_filename = %s, ss_title = %s, ss_keywords = %s, ss_cat1 = %s, ss_cat2 = %s, ss_data =%s, ss_location = %s where ss_media_id = %s", (
        picture['original_filename'],
        picture['description'],
        ','.join(picture['keywords']),
        picture['categories'][0] if len(picture['categories'])>0 else None,
        picture['categories'][1] if len(picture['categories'])>1 else None,
        json.dumps(picture),
        json.dumps(picture['location']),
        picture['id'][1:]
    ))
    db.commit()

def modify_exif_data(picture, filename):

    jpg_name = join(ssCommon.FOLDER_REVIEWED, filename)
    dng_name = join(ssCommon.FOLDER_REVIEWED + "\\dng", ssCommon.get_stripped_file_name(filename).replace('.jpg','.dng'))

    subject = ";".join(ssCommon.categories[int(ctg)]['name'] for ctg in picture['categories'])

    print('=======================================================================')
    print(jpg_name)
    print(picture['description'])
    print(subject)

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
                b'-copyright=' + bytes(json.dumps(picture['location']),'latin1'),
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

    global EXIF_TOOL

    if 'EXIF_TOOL' in os.environ:
        EXIF_TOOL = os.environ['EXIF_TOOL']
    else:
        EXIF_TOOL = 'exiftool'

    os.environ['SS_AUTO_LOGIN_COOKIES'] = "locale=en-US; did=izwknfMux8KIk8VZXA__Lglwhq9MfRcqrgR2Bg2Opds%3D; ajs_user_id=%22239148037%22; ajs_group_id=null; visitor_id=44020985583; ajs_anonymous_id=%2206d2efca-d8aa-4349-a5ea-cd4c7d405ff6%22; __ssid=b91608fa8ae758b2479c8a0446eb43f; cto_lwid=d4cdedf9-5fbf-4c3d-a45b-17926ef11d3c; language=en; session=s%3AnpXoW00v62E8_pb_-hlwTh-SFpDpV1i0.ROXV7lG23aiCW1WuM4FPrmduaHjWwuSXf%2FQuCpI9a%2Fg; _ga=GA1.2.2025806565.1570193260; _ym_uid=1570193260262376265; _ym_d=1570193260; __qca=P0-32455493-1570193261124; cto_bundle=DHbsx19YQ0czb2owR0dhNWtleGRzNDBLZE9kRlJDV2pmb1Fobldrc1BBZFFwbG5EV01hdGI3YiUyQkpFbjZUeEp1ZXRSa21UY2wyNDdhZVgxZnNtUyUyQm9HQUpPUDdtJTJGQ1RtcSUyRk9SZjZTNGtUWmRDTjRTRHRwcDJJeEpGYWtlQTRuMk9LR3lzdEI2Sm45bXpjcjU4b3AlMkZvVTd5OXAlMkJOSG5GcFklMkJEUHlIc0l4Z09MeWgwbyUzRA; ELOQUA=GUID=29DBE6CD48E345CBA843A3B372D1CDEE; _ceir=1; IR_PI=030d3091-e9e1-11e9-9f43-42010a246604%7C1584818845651; accts_customer=; accts_customer_sso1=; splitVar=AB_Test-adroll; _cs_c=1; _cs_id=a49ec4fa-7aa4-a86f-da64-2386df0dc63c.1576221764.38.1580233576.1580233241.1576175022.1610385764368; splitVar=AB_Test-criteo; _fbp=fb.1.1577319066482.771139171; _biz_uid=5069e667b50f459ebd0bf686275426b4; _biz_nA=3; _biz_pendingA=%5B%5D; _biz_flagsA=%7B%22Version%22%3A1%2C%22XDomain%22%3A%221%22%7D; ei_client_id=5e0cbbc40b3de10010253878; __insp_wid=7949100; __insp_slim=1577892765372; __insp_nv=true; __insp_targlpu=aHR0cHM6Ly9jdXN0b20uc2h1dHRlcnN0b2NrLmNvbS8%3D; __insp_targlpt=U2h1dHRlcnN0b2NrIEN1c3RvbQ%3D%3D; __insp_norec_sess=true; _gcl_au=1.1.777535031.1578031777; bce=emailcore-shutters.23808045-; CookieAwin=Other; CookieAwinExpiration=1586082077520; accts_contributor=Raicho%20Minev; accts_contributor_sso1=238906963-undefined; _4c_=jVRLb%2BM2EP4rCx16Ch2S4kMMsFj0gRZ76Kkp9hhQ5MgW7IgCRcVxA%2F%2F3zvgV19kC64vJme%2F75sHRvFXbFQzVg9CNso3UVire3FVr2E3Vw1uV%2B0h%2FL9VDFbVRTRCGKRMbppTVzKs6sjpyU%2FMOojKhuqteScsJo2urtbB6f1eF8aTxVs15g1KrUsbp4f5%2Bmtvnviym1VwK5KmksF6E9HwPsS9fNn5Yzn4Jn2H4qexG%2BDyuUkkYAQZKZ8wRz9NU1lNfAA0hDSX37VxSJsfcTiH3Y%2BnT8IhsBMxDhK4fgHjzBPmv4ss8EXPG0M9AtJBmVNndoEOKJCDcQoiFREP5h66S43HMKc6hPJVjkC20n6a4RkeElz7A07aPZUVoXZt36wr65aqguTGKrGMmyEJqvGz7IabtLfFkvRCtpuhtTlssBe%2B%2F9xm69PrJkl6isr4dGBNe0QM5H2DUmmO%2Fbrt%2B8uDL3zipSOq4JOVNCn5DdBwaJECgBn%2Fovh%2FSsHtO8%2FQVx6fiJkrogmex8Z6pWjnmNXgWogo2Kq67jir84%2Benv7%2F%2BRoG41A032uiF0JYLV0tDxT7mfrmE%2FCeUVSLdx%2BxxUDC%2B31APKY0MEaZ%2BSblF6hLe1iWNF%2FP%2BNKCNakzjLAax%2BJoFhxIfgtNvf6z2MK9SXcGNEYab78CPb8B%2Bkb8yGC7ca2rtlJNO%2FS%2F1qnnXEpL%2FSPhxc4KLC9o64aRQyp3QeDyjcajPH3Tr8Zv1nrNOtJIp4RxzoW4ZB6ulAOOFM9WHDJqPGVDnj5JX7T%2FuAam1kUizFnH4NZ5TPWwbjh4j6xssWgh7lvS3Wkf%2F%2BL6YQgNK6y4ycAYYHVnbOsNC3UHrdCuUgfc6bGNVzbGWUx1WnsvoX7c36RFO%2Fif8wYLYcl5p1a76LiC%2Fax0cCtchLdbXGwtCXy611r5RvhM1cwpqfJEaWKuVZ50HHlvVKtnW15WgBJeXmRDNsZL9%2Fl8%3D; IR_gbd=shutterstock.com; IR_1305=1584777518731%7C-1%7C1584777518731%7C%7C; _pxvid=f74749c3-6a6d-11ea-8333-0242ac120009; _gid=GA1.2.647632038.1584683114; _ym_isad=1; visit_id=61104634570; _px3=909c781ba96d71afffae3d8df3e2d68042fc4187df8401e60fac9153bb50b760:eTdk7zI+NnJGfGyAHpj6LFqTN/jad/3eElVhsvC9zN7CEvCiCx590oo0s5H+1bI0KZhX1jDEixzLnLdvzanETA==:1000:TnQwvRe5gGSOPFcQmgj940O73yTc8eSkiDuJVm8HHQqCp2IzZyLqq1Ug1gmjHToflCKkH3HosKHDMtjOSBfrGJ3O4cC2X7Cvk2jmcRpzcoapXqm94RTVxlwjArD8s/ugkTMn3aXHVn0qceSGARaRg92nH+mNsYEJK8uVrp5EUpY=; _actts=1582551713.1584732447.1584777523; _actvc=12; _actcc=1.1.17.17; _actmu=208821ed-1609-45b0-a10b-8cfd4b3e8d40; AMP_TOKEN=%24NOT_FOUND; _gat_UA-32034-2=1"
    db = ssCommon.connect_database()

    ssCommon.ss_login()
    load_catalog_files(db)

    db.commit()
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