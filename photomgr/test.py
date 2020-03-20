import os

import PIL
# import exif
# import piexif
from PIL import Image

def resize_img(name, basewidth):
    img = Image.open(name)
    wpercent = (basewidth / float(img.size[0]))
    hsize = int((float(img.size[1]) * float(wpercent)))
    img = img.resize((basewidth, hsize), PIL.Image.ANTIALIAS)
    img.save(name+'resized.jpg', "JPEG",  quality = 80)

# def dump(name):
#
#     # image_file = open(name, 'rb')
#     # my_image = exif.Image(image_file)
#     # image_file.close()
#     # print(dir(my_image))
#
#     img = Image.open(name)
#     exif_dict = piexif.load(img.info['exif'])
#     print(str(exif_dict))
#
#
# def set_title_in_exif(name, title):
#
#     # image_file = open(name, 'rb')
#     # my_image = exif.Image(image_file)
#     # my_image.title = title
#     # my_image.caption = title
#     # my_image.description = title
#     # image_file.close()
#     #
#     #
#     # with open(name, 'wb') as new_image_file:
#     #     new_image_file.write(my_image.get_file())
#
#     img = Image.open(name)
#     exif_dict = piexif.load(img.info['exif'])
#
# #    exif_dict['0th'][piexif.ImageIFD.XPTitle] = title
#
#     exif_bytes = piexif.dump(exif_dict)
#     img.save('%s.jpg' % name, "jpeg", exif=exif_bytes)

if __name__ == "__main__":
    #resize_img('g:/prj/photomgr/DSC_5040.jpg',3000)
    # set_title_in_exif('g:/prj/photomgr/DSC_5040.jpg', 'xxx')
    # dump('g:/prj/photomgr/DSC_5040.jpg.jpg')
    #
    # dump('C:\\Users\\user-pc2\\Desktop\\shutterstock\\submitted\\_DSC5684.jpg')

    #todo: fix library path in PATH
    #todo: move to 64 bit python

    import pyexiv2

    metadata = pyexiv2.ImageMetadata('C:\\Users\\user-pc2\\Desktop\\shutterstock\\submitted\\_DSC5684.jpg')
    metadata.read()
    print(str(metadata.exif_keys))

    metadata._set_xmp_tag('Xmp.dc.title', 'xyz')
    metadata._set_xmp_tag('Xmp.dc.description', 'xyz')
    metadata._set_xmp_tag('Xmp.acdsee.caption', 'xyz')
    metadata._set_xmp_tag('Iptc.Application2.Keywords', ['a','b','c'])


    for key in  metadata.xmp_keys:
        print (key + ':' + str(metadata._get_xmp_tag(key)))

    for key in  metadata.exif_keys:
        print (key + ':' + str(metadata._get_exif_tag(key)))

    for key in  metadata.iptc_keys:
        print (key + ':' + str(metadata._get_iptc_tag(key)))

