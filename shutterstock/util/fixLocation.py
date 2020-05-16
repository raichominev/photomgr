import json
import os
from os.path import join

import exiftool
from shutterstock import ssCommon

def modify_exif_data(picture, jpg_name ,dng_name):

    print('=======================================================================')
    print(jpg_name)

    # =40.3258678 =23.9813901 -GPSLongitudeRef=E -GPSLatitudeRef=N
    modification_list = (
                b'-overwrite_original',
                b'-m',
                b'-XMP:GPSLatitude=' + bytes(str(picture['lat']).replace("-","") if picture['lat'] else "",'latin1'),
                b'-XMP:GPSLongitude=' + bytes(str(picture['long']).replace("-","") if picture['long'] else "",'latin1'),
                b'-GPSLatitudeRef=' + bytes('S' if '-' in str(picture['lat']) else 'N' if picture['lat'] else "",'latin1'),
                b'-GPSLongitudeRef=' + bytes('W' if '-' in str(picture['lat']) else 'E' if picture['long'] else "",'latin1'),
    )

    with exiftool.ExifTool(EXIF_TOOL, False) as et:
        # print (str(( modification_list + (bytes(jpg_name, encoding='latin1'),))))

        #shutil.move(jpg_name, 'xx.jpg' )
        outcome =  et.execute( * ( modification_list + (bytes(jpg_name.replace("/",'\\'), encoding='latin1'),)) )
        print(outcome)

        #shutil.move('xx.jpg', jpg_name )
        if b'1 image files updated' not in outcome:
            return False
        outcome = et.execute( * ( modification_list + (bytes(dng_name.replace("/",'\\'), encoding='latin1'),)) )
        print(outcome)
        if b'1 image files updated' not in outcome:
            return False

    return True


if __name__ == "__main__":

    os.environ["DATABASE_URL"] = "postgres://uhztcmpnkqyhop:c203bc824367be7762e38d1838b54448fe503f16fe34bb783d45a4a8bb370c00@ec2-34-200-116-132.compute-1.amazonaws.com:5432/d42v6sfcnns36v"

    global EXIF_TOOL

    if 'EXIF_TOOL' in os.environ:
        EXIF_TOOL = os.environ['EXIF_TOOL']
    else:
        EXIF_TOOL = 'exiftool'

    db = ssCommon.connect_database()
    #ini()

    cur = db.cursor()
    cur.execute("select id, ss_location, ss_filename from ss_reviewed where ss_lat is not null and state > 10")
    records = cur.fetchall()

    count = 0
    for db_data in records:

        location = json.loads(db_data[1])
        loc_data = json.loads(location["external_metadata"])

        lat = loc_data["geometry"]["location"]["lat"]
        long = loc_data["geometry"]["location"]["lng"]

        jpg_name = join(ssCommon.FOLDER_UNDER_REVIEW, db_data[2])
        dng_name = join(ssCommon.FOLDER_UNDER_REVIEW + "\\dng", ssCommon.get_stripped_file_name(db_data[2]).replace('.jpg','.dng'))

        fix_list = {'lat': lat, 'long':long}

        modify_exif_data(fix_list, jpg_name ,dng_name)

        db.commit()
        count += 1

    print('' + str(count) + ' files processed.')
    db.close()


#        {"external_metadata":"{\"address_components\":[{\"long_name\":\"Eleshnitsa\",\"short_name\":\"Eleshnitsa\",\"types\":[\"locality\",\"political\"]},{\"long_name\":\"Blagoevgrad Province\",\"short_name\":\"Blagoevgrad Province\",\"types\":[\"administrative_area_level_1\",\"political\"]},{\"long_name\":\"Bulgaria\",\"short_name\":\"BG\",\"types\":[\"country\",\"political\"]},{\"long_name\":\"2782\",\"short_name\":\"2782\",\"types\":[\"postal_code\"]}],\"adr_address\":\"<span class=\\\"postal-code\\\">2782</span> <span class=\\\"locality\\\">Eleshnitsa</span>, <span class=\\\"country-name\\\">Bulgaria</span>\",\"formatted_address\":\"2782 Eleshnitsa, Bulgaria\",
#        \"geometry\":{\"location\":{\"lat\":41.864309,\"lng\":23.6166949},\"viewport\":{\"northeast\":{\"lat\":41.87452140000001,\"lng\":23.6283817},\"southwest\":{\"lat\":41.861446,\"lng\":23.6115956}}},\"icon\":\"https://maps.gstatic.com/mapfiles/place_api/icons/geocode-71.png\",\"name\":\"Eleshnitsa\",\"place_id\":\"ChIJ4W6zbAinqxQRXI9I31OdRr4\",\"types\":[\"locality\",\"political\"],\"url\":\"https://maps.google.com/?q=2782+Eleshnitsa,+Bulgaria&ftid=0x14aba7086cb36ee1:0xbe469d53df488f5c\",\"utc_offset\":180,\"vicinity\":\"Eleshnitsa\"}","external_metadata_source":"google","collected_full_location_string":"2782 Eleshnitsa, Bulgaria","collected_full_location_language":"en","english_full_location":"2782 Eleshnitsa, Bulgaria"}

# {"external_metadata": "{\"address_components\":[{\"long_name\":\"Ouranoupoli\",\"short_name\":\"Ouranoupoli\",\"types\":[\"locality\",\"political\"]},{\"long_name\":\"Halkidiki\",\"short_name\":\"Halkidiki\",\"types\":[\"administrative_area_level_3\",\"political\"]},{\"long_name\":\"Greece\",\"short_name\":\"GR\",\"types\":[\"country\",\"political\"]}],\"adr_address\":\"<span class=\\\"locality\\\">Ouranoupoli</span>, <span class=\\\"country-name\\\">Greece</span>\",\"formatted_address\":\"Ouranoupoli, Greece\",
#         \"geometry\":{\"location\":{\"lat\":40.3258678,\"lng\":23.9813901},\"viewport\":{\"northeast\":{\"lat\":40.3291179,\"lng\":23.984157},\"southwest\":{\"lat\":40.3238227,\"lng\":23.9781703}}},\"icon\":\"https://maps.gstatic.com/mapfiles/place_api/icons/geocode-71.png\",\"name\":\"Ouranoupoli\",\"place_id\":\"ChIJF1r7vvvIqBQR0yBsVExCSTk\",\"types\":[\"locality\",\"political\"],\"url\":\"https://maps.google.com/?q=Ouranoupoli,+Greece&ftid=0x14a8c8fbbefb5a17:0x3949424c546c20d3\",\"utc_offset\":120,\"vicinity\":\"Ouranoupoli\"}", "external_metadata_source": "google", "collected_full_location_string": "Ouranoupoli, Greece", "collected_full_location_language": "en", "english_full_location": "Ouranoupoli, Greece"}
