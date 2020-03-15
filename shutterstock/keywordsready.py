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

        if 'pic.keyworder.tmp.jpg' in x.name: continue
        x.download_to_filename('pic.keyworder.tmp',raw_download=True)

        resize_img('pic.keyworder.tmp',400)

        d = bucket.blob('pic.keyworder.tmp.jpg')
        with open('pic.keyworder.tmp.resized.jpg', "rb") as pic:
            d.upload_from_file(pic,predefined_acl='publicRead')

        image_url = 'http://storage.googleapis.com/myphotomgr/pic.keyworder.tmp.jpg'
        headers = {"Content-type": "application/x-www-form-urlencoded" , 'api-key':'27039xQZPk51RFf8CCQrHACf50Att'}
        response = requests.post('https://keywordsready.com/api/analyzes' , {'url':image_url,  }, headers=headers )
        print(response)
        print(response.json())

