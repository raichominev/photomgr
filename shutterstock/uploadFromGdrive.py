import os
import re
import shutil
from os.path import join

from shutterstock import ssCommon

titleMatch = r'T#.*#T'

if __name__ == "__main__":
    from google.cloud import storage

    f = open('cloud_auth.txt','w+')
    f.write(os.environ['CLOUD_STORE_API'])
    f.close()

    storage_client = storage.Client.from_service_account_json('cloud_auth.txt')
    bucket = storage_client.get_bucket('myphotomgr')

    count = 0
    for filename in os.listdir(ssCommon.FOLDER_PENDING):
        if re.match(titleMatch, filename):
            print ('Uploading ' + filename)

            # upload to cloud storage
            d = bucket.blob(filename)
            with open(ssCommon.FOLDER_PENDING + "\\" + filename, "rb") as pic:
                d.upload_from_file(pic) # predefined_acl='publicRead'

            jpg_name = join(ssCommon.FOLDER_PENDING, filename)
            dng_name = join(ssCommon.FOLDER_PENDING + "\\dng", filename.replace('.jpg','.dng'))

            shutil.move(jpg_name, ssCommon.FOLDER_UNDER_REVIEW)
            shutil.move(dng_name, ssCommon.FOLDER_UNDER_REVIEW + "\\dng")

        count += 1

    print('Complete ' + str(count) + '.')