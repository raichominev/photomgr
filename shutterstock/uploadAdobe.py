import ftplib
import os

from shutterstock import ssCommon

BATCH_SIZE = 25

if __name__ == "__main__":

    db = ssCommon.connect_database()

    cur = db.cursor()
    cur.execute("select original_filename, id from ss_reviewed where ss_status = 'approved' and adobe_status is null" )
    db_records = cur.fetchall()
    print('Database records pending:' + str(len(db_records)))
    count = 0
    for i in range(BATCH_SIZE):
        db_data = db_records[i]
        if db_data is None:
              break

        current_file_name = db_data[0]
        id = db_data[1]

        print('Uploading file ' + current_file_name)

        session = ftplib.FTP('ftp.contributor.adobestock.com',os.environ['ADOBE_USER'],os.environ['ADOBE_PASSWORD'])
        file = open(ssCommon.FOLDER_REVIEWED + "\\" + current_file_name,'rb')
        session.storbinary('STOR ' + ssCommon.get_stripped_file_name(current_file_name), file)
        file.close()
        session.quit()

        cur = db.cursor()
        cur.execute("update ss_reviewed set adobe_status = 'uploaded', adobe_upload_date = now() where id =  " + str(id))
        db.commit()
        count+=1

    print('' + str(count) + ' files uploaded.')