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
    count = 0
    for x in storage_client.list_blobs('myphotomgr'):
        x.download_to_filename('pic.tmp',raw_download=True)
        print (x.name)
        print (x._get_download_url())

        # session = ftplib.FTP('ftp.shutterstock.com',os.environ['SHUTTERSTOCK_USER'],os.environ['SHUTTERSTOCK_PASSWORD'])
        # file = open('pic.tmp','rb')
        # session.storbinary('STOR ' + x.name, file)
        # file.close()
        # session.quit()
        # count+=1

    print ('Complete ' + str(count) + '.')