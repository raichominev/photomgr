import base64
import os
from datetime import datetime

import PIL
import requests
from PIL import Image

import exiftool
from shutterstock import ssCommon

JUNK_KEYWORDS = ['icee', 'snowstorm', 'fair weather', 'snowdrift', 'subway system', 'christmas', 'celebration']

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
    print(os.environ['EXIF_TOOL'])
    with exiftool.ExifTool(os.environ['EXIF_TOOL']) as et:
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

    with exiftool.ExifTool(os.environ['EXIF_TOOL']) as et:
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


def get_keywords(storage_client, temp_name, title):

    resize_img(temp_name, 3000)

    if title:
        modify_exif_title(temp_name + '.resized.jpg', title)

    idx = str(round(datetime.now().timestamp() * 1000000))
    bucket = storage_client.get_bucket('myphotomgr')
    d = bucket.blob(ssCommon.get_stripped_file_name(os.path.basename(temp_name)) + idx +'.jpg')
    with open(temp_name + '.resized.jpg', "rb") as pic:
        d.upload_from_file(pic, predefined_acl='publicRead')

    image_url = 'http://storage.googleapis.com/myphotomgr/'+ssCommon.get_stripped_file_name(os.path.basename(temp_name))+idx+'.jpg'
    auth = bytes(os.environ['MYKEYWORDER_USER'], 'latin1') + b':' + bytes(os.environ['MYKEYWORDER_KEY'], 'latin1')
    headers = {'Authorization': b'Basic ' + base64.b64encode(auth)}

    response = requests.get('http://mykeyworder.com/api/v1/analyze', {'url': image_url}, headers=headers)

    data = response.json()

    print(str(data))

    for x in JUNK_KEYWORDS:
        if x in data['keywords']:
            data['keywords'].remove(x)

    keywords = ",".join(data['keywords'])

    #print('kw:'+keywords)

    d.delete()

    return keywords
