# -*- coding:utf-8 -*-
import os
from pathlib import Path

import cv2
import numpy as np
from pofile import mkdir

from poimage.core.ImageType import MainImage
from PIL import Image
import math

mainImage = MainImage()


# todo：输出文件路径
def add_watermark(file, mark, output_path='./mark_img', color="#eaeaea", size=30, opacity=0.35, space=200,
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
def img2Cartoon(path, client_api='', client_secret=''):
    mainImage.img2Cartoon(path, client_api, client_secret)


def pencil4img(input_img, output_path='./', output_name=r'pencil4img.jpg'):
    mainImage.pencil4img(input_img, output_path, output_name)


def flag2profile(profile_path, output_path, flag_path=None):
    """
    1行代码，生成国旗头像
    :param flag_path: 国旗的路径
    :param profile_path: 原始头像的路径
    :param output_path: 合成头像的路径
    :return:
    """
    key = 3.2  # 修改key值可以调整国旗的范围，推荐2~4之间的数字，支持小数
    if flag_path == None:
        root_path = Path(__file__).parent.parent
        src_path = root_path / 'src/imgs'
        flag_path = src_path / '1024.png'
    motherland_flag = Image.open(flag_path)
    head_picture = Image.open(profile_path)
    # 截图国旗上的五颗五角星
    flag_width, flag_height = motherland_flag.size
    crop_flag = motherland_flag.crop((66, 0, flag_height + 66, flag_height))
    # 将国旗截图处理成颜色渐变
    for i in range(flag_height):
        for j in range(flag_height):
            color = crop_flag.getpixel((i, j))
            distance = int(math.sqrt(i * i + j * j))
            alpha = 255 - int(distance // key)
            new_color = (*color[0:-1], alpha if alpha > 0 else 0)
            crop_flag.putpixel((i, j), new_color)
    # 修改渐变图片的尺寸，适应头像大小，粘贴到头像上
    new_crop_flag = crop_flag.resize(head_picture.size)
    head_picture.paste(new_crop_flag, (0, 0), new_crop_flag)
    # 保存自己的国旗头像
    mkdir(Path(output_path).absolute().parent)
    head_picture.save(output_path)


def split4img(img_path, output_path: str = r'./', num=9):
    """
    切割图片
    :param img_path:
    :param num:
    :return:
    """
    mainImage.split4img(img_path, output_path, num)


def compress_to_size(input_file: str, output_file: str, target_size_kb: int, min_quality: int = 10, max_quality: int = 95):
    """
    将图片压缩至指定目标大小（KB）
    
    参数:
        input_file (str): 输入图片文件路径，支持常见格式如JPEG、PNG等
        output_file (str): 输出图片文件路径
        target_size_kb (int): 目标大小，单位KB，必须大于0
        min_quality (int): 最低质量参数，范围1-100，默认10
        max_quality (int): 最高质量参数，范围1-100，默认95
        
    返回:
        dict: 包含压缩结果的字典
            - success (bool): 是否成功压缩
            - original_size (float): 原始大小（KB）
            - compressed_size (float): 压缩后大小（KB）
            - quality (int): 使用的质量参数
            - compression_ratio (float): 压缩比例（原始大小/压缩后大小）
            - message (str): 结果消息
            
    使用示例:
        >>> from poimage.api import image
        >>> result = image.compress_to_size('large_photo.jpg', 'small_photo.jpg', 100)
        >>> print(result['message'])
        >>> print(f"压缩比例: {result['compression_ratio']}")
        
    功能说明:
        - 使用自适应压缩算法，通过二分查找最优质量参数
        - 自动处理不同图片格式（JPEG、PNG等）
        - 如果原始文件已小于目标大小，直接复制无需压缩
        - 当无法达到目标大小时，使用最低质量参数并返回警告信息
        
    注意事项:
        - 目标大小设置过小可能导致图片质量严重下降
        - PNG格式的压缩效果可能不如JPEG明显
        - 压缩过程在内存中完成，避免频繁磁盘IO
    """
    return mainImage.compress_to_size(input_file, output_file, target_size_kb, min_quality, max_quality)
