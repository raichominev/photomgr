import PIL
from PIL import Image

def resize_img(name, basewidth):
    img = Image.open(name)
    wpercent = (basewidth / float(img.size[0]))
    hsize = int((float(img.size[1]) * float(wpercent)))
    img = img.resize((basewidth, hsize), PIL.Image.ANTIALIAS)
    img.save(name+'resized.jpg', "JPEG",  quality = 80)


if __name__ == "__main__":
    resize_img('g:/prj/photomgr/DSC_5040.jpg',3000)
