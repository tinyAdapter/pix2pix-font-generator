# -*- coding: utf-8 -*-\
from PIL import Image, ImageDraw, ImageFont

point_size = 32
font = ImageFont.truetype("simsun.ttf", point_size)

startIndex = ord(u'一')
endIndex = ord(u'龟')

for i in range(startIndex, endIndex + 1):
    print("processing %d / %d" % (i, endIndex), end="\r")
    im = Image.Image()._new(font.getmask(str(i)))
    newIm = Image.new("L", (point_size, point_size))
    x, y = im.size
    region = im.crop((0, 0, x, y))
    newIm.paste(region, (int((point_size-x)/2), int((point_size-y)/2)))
    newIm.save("E:/py/ml/images" + i + ".bmp")
