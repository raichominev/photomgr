import io
import os
import ftplib

if __name__ == "__main__":
    from google.cloud import storage

    f = open('cloud_auth.txt','w+')
    f.write(os.environ['CLOUD_STORE_API'])
    f.close()

    storage_client = storage.Client.from_service_account_json('cloud_auth.txt')


    bucket = storage_client.get_bucket('myphotomgr')
    for x in storage_client.list_blobs('myphotomgr'):
        x.download_to_filename('pic.tmp',raw_download=True)
        print (x.name)

        session = ftplib.FTP('ftp.shutterstock.com',os.environ['SHUTTERSTOCK_USER'],os.environ['SHUTTERSTOCK_PASSWORD'])
        file = open(x.name,'rb')
        session.storbinary('STOR pic.tmp', file)
        file.close()
        session.quit()
