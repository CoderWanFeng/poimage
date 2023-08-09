# -*- coding: UTF-8 -*-
'''
@作者 ：B站/抖音/微博/小红书/公众号，都叫：程序员晚枫
@微信 ：CoderWanFeng : https://mp.weixin.qq.com/s/yFcocJbfS9Hs375NhE8Gbw
@个人网站 ：www.python-office.com
@Date    ：2023/7/3 23:05 
@Description     ：
'''

from PIL import Image


def compress_image(input_file, output_file, quality):
    img = Image.open(input_file)
    img.save(output_file, quality=quality)


input_file = r'D:\workplace\code\github\poimage\tests\group.jpg'
output_file = "compressed.jpg"
quality = 50  # 质量，1-100之间，数值越低压缩率越高

import poimage

poimage.compress_image(input_file, output_file, quality)
