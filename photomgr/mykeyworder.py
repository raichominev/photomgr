import os
import requests
from google.cloud import storage

if __name__ == "__main__":

    f = open('cloud_auth.txt','w+')
    f.write(os.environ['CLOUD_STORE_API'])
    f.close()

    storage_client = storage.Client.from_service_account_json('cloud_auth.txt')


    bucket = storage_client.get_bucket('myphotomgr')
    count = 0
    for x in storage_client.list_blobs('myphotomgr'):
        image_url = 'http://mykeyworder.com/img/france.jpg'
        response = requests.get('http://mykeyworder.com/api/v1/analyze?url=%s' % image_url, auth=(os.environ['MYKEYWORDER_USER'],os.environ['MYKEYWORDER_KEY']))

        print(response.json())