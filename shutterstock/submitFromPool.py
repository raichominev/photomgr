# workflow:
# 1. readied images go to local folder for upload
# 2. local service uploads them through proxy service
# 3. ???keywording?/title/category

import ftplib
import os
import psycopg2
from google.cloud import storage

# LOGIN_COOKIES_DB_FILE = "login.txt"
# CATEGORY_URL = "https://submit.shutterstock.com/api/content_editor/categories/photo"
# DEFAULT_HEADERS = {'User-Agent' : 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:71.0) Gecko/20100101 Firefox/71.0'}

cookie_dict = {}
categories = None
reasons = None


def connect_database():
   return psycopg2.connect(os.environ["DATABASE_URL"])


# def ini():
#    global categories
#
#    with open(LOGIN_COOKIES_DB_FILE) as f:
#       cookies = f.readline()
#       for c in cookies.split(';'):
#          name,val = c.split('=',1)
#          cookie_dict[name.strip()] = val.strip()
#
#    ##############################
#    # GET AUXILIARY  DATA LIST
#    response = requests.get(CATEGORY_URL, cookies=cookie_dict, headers=DEFAULT_HEADERS)
#    category_json = response.json()
#    categories = dict((ct['cat_id'],ct) for ct in category_json['data'])
#
#    print(json.dumps(categories))
#

if __name__ == "__main__":
   db = connect_database()
   #ini()

   f = open('cloud_auth_upload.txt','w+')
   f.write(os.environ['CLOUD_STORE_API'])
   f.close()

   storage_client = storage.Client.from_service_account_json('cloud_auth_upload.txt')

   bucket = storage_client.get_bucket('myphotomgr')

   cur = db.cursor()
   cur.execute("select ss_filename from ss_reviewed where state = 0 ")
   records = cur.fetchall()

   count = 0
   for db_data in records:

      x = bucket.get_blob(db_data[0])
      x.download_to_filename('pic.tmp',raw_download=True)
      print(x.name)

      session = ftplib.FTP('ftp.shutterstock.com',os.environ['SHUTTERSTOCK_USER'],os.environ['SHUTTERSTOCK_PASSWORD'])
      file = open('pic.tmp','rb')
      session.storbinary('STOR ' + db_data[0], file)
      file.close()
      session.quit()

      cur = db.cursor()
      cur.execute("update ss_reviewed set state = 1, date_submitted = now() where ss_filename = %s ", (db_data[0],))

      db.commit()
      count += 1

   print('' + str(count) + ' files processed.')
   db.close()
