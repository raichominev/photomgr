import base64
import os
import requests
from google.cloud import storage
import PIL
from PIL import Image
from google.cloud.storage.acl import ACL


def resize_img(name, basewidth):
    img = Image.open(name)
    wpercent = (basewidth / float(img.size[0]))
    hsize = int((float(img.size[1]) * float(wpercent)))
    img = img.resize((basewidth, hsize), PIL.Image.ANTIALIAS)
    img.save(name+'.resized.jpg', "JPEG",  quality = 80)

if __name__ == "__main__":

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

        x.download_to_filename('pic.keyworder.tmp',raw_download=True)

        resize_img('pic.keyworder.tmp',3000)

        d = bucket.blob('pic.keyworder.tmp.jpg')
        with open('pic.keyworder.tmp.resized.jpg', "rb") as pic:
                d.upload_from_file(pic,predefined_acl='publicRead')

        # todo: parse filename & update exif title of temp file
        #

        image_url = 'http://storage.googleapis.com/myphotomgr/pic.keyworder.tmp.jpg'
        auth = b'Basic ' + bytes(os.environ['MYKEYWORDER_USER'],'latin1')+b':' + bytes(os.environ['MYKEYWORDER_KEY'],'latin1')
        headers = {'Authorization' : base64.b64encode(auth)}
        response = requests.get('http://mykeyworder.com/api/v1/analyze' ,{'url':image_url}, headers=headers)
        print(response)
        #print(response.json())

