# -*- coding: UTF-8 -*-
'''
@作者  ：B站/抖音/微博/小红书/公众号，都叫：程序员晚枫
@微信     ：CoderWanFeng : https://mp.weixin.qq.com/s/B1V6KeXc7IOEB8DgXLWv3g
@个人网站      ：www.python-office.com
@代码日期    ：2023/10/22 0:31 
@本段代码的视频说明     ：
'''
# from Pillow import Image
from PIL import Image
import sys


def fill_image(image):
    width, height = image.size
    new_image_length = width if width > height else height
    new_image = Image.new(image.mode, (new_image_length, new_image_length), color='white')
    if width > height:
        new_image.paste(image, (0, int((new_image_length - height) / 2)))
    else:
        new_image.paste(image, (int((new_image_length - width) / 2), 0))
    return new_image


def cut_image(image):
    width, height = image.size
    item_width = int(width / 2)
    box_list = []
    for i in range(0, 2):
        for j in range(0, 2):
            print((i * item_width, j * item_width, (i + 1) * item_width, (j + 1) * item_width))
            box = ((j * item_width, i * item_width, (j + 1) * item_width, (i + 1) * item_width))
            box_list.append(box)
    image_list = [image.crop(box) for box in box_list]
    return image_list


def save_images(image_list):
    index = 1
    for image in image_list:
        #               image.show()
        image.save(str(index) + '.png', 'PNG')
        index += 1


if __name__ == '__main__':
    file_path = "./imgs/icon2.jpg"
    image = Image.open(file_path)
    image.show()
    image = fill_image(image)
    image.show()
    image_list = cut_image(image)
    save_images(image_list)