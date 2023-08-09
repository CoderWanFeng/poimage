#!/usr/bin/env python
# -*- coding:utf-8 -*-

import os

import cv2
import numpy as np
from PIL import Image

#############################################
# File Name: 图片.py
# Mail: 1957875073@qq.com
# Created Time:  2022-4-25 10:17:34
# Description: 有关 图片 的自动化操作
#############################################
from poimage.core.ImageType import MainImage

mainImage = MainImage()


# todo：输出文件路径
def add_watermark(file, mark, output_path='./mark_img', color="#8B8B1B", size=30, opacity=0.15, space=75,
                  angle=30):
    mainImage.add_watermark(file, mark, output_path, color, size, opacity, space, angle)


def down4img(url, output_path='.', output_name='down4img', type='jpg'):
    """
    :param url: 图片的下载链接，必填
    :param output_path: 下载后存放的位置，选填，默认
    :param output_name: 下载图片的名称，选填，默认：down4img
    :param type:下载图片的类型，选填，默认：jpg
    :return:
    """
    mainImage.down4img(url, output_path, output_name, type)


def del_watermark(input_image, output_image=r'./del_water_mark.jpg'):
    """
    去除微信文章的水印
    :param input_image:
    :param output_image:
    :return:
    """
    dir = os.getcwd()
    path = input_image
    newPath = output_image
    img = cv2.imread(path, 1)
    hight, width, depth = img.shape[0:3]

    # 截取
    cropped = img[int(hight * 0.8):hight, int(width * 0.7):width]  # 裁剪坐标为[y0:y1, x0:x1]
    cv2.imwrite(newPath, cropped)
    imgSY = cv2.imread(newPath, 1)

    # 图片二值化处理，把[200,200,200]-[250,250,250]以外的颜色变成0
    thresh = cv2.inRange(imgSY, np.array([200, 200, 200]), np.array([250, 250, 250]))
    # 创建形状和尺寸的结构元素
    kernel = np.ones((3, 3), np.uint8)
    # 扩展待修复区域
    hi_mask = cv2.dilate(thresh, kernel, iterations=10)
    specular = cv2.inpaint(imgSY, hi_mask, 5, flags=cv2.INPAINT_TELEA)
    cv2.imwrite(newPath, specular)

    # 覆盖图片
    imgSY = Image.open(newPath)
    img = Image.open(path)
    img.paste(imgSY, (int(width * 0.7), int(hight * 0.8), width, hight))
    img.save(newPath)


def txt2wordcloud(filename, color="white", result_file="your_wordcloud.png"):
    mainImage.txt2wordcloud(filename, color, result_file)


def compress_image(input_file: str, output_file: str, quality: int):
    mainImage.compress_image(input_file, output_file, quality)


# @except_dec()
def image2gif():
    mainImage.image2gif()


# todo：输入文件路径
def img2Cartoon(path, client_api='OVALewIvPyLmiNITnceIhrYf', client_secret='rpBQH8WuXP4ldRQo5tbDkv3t0VgzwvCN'):
    mainImage.img2Cartoon(path, client_api, client_secret)


def pencil4img(input_img, output_path='./', output_name=r'pencil4img.jpg'):
    mainImage.pencil4img(input_img, output_path, output_name)

    #
    # def decode_qrcode(qrcode_path):
    #     """
    #     解析二维码
    #     :param qrcode_path: 二维码图片的路径
    #     :return:
    #     """
    #     mainImage.decode_qrcode(qrcode_path)
