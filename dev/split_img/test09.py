# -*- coding: UTF-8 -*-
'''
@作者  ：B站/抖音/微博/小红书/公众号，都叫：程序员晚枫，微信：CoderWanFeng
@读者群     ：http://www.python4office.cn/wechat-group/
@学习网站      ：www.python-office.com
@代码日期    ：2023/10/22 0:31 
@本段代码的视频说明     ：
'''

# from PIL import Image
# #
# #
# # def fill_image(image):
# #     width, height = image.size
# #     new_image_length = width if width > height else height
# #     new_image = Image.new(image.mode, (new_image_length, new_image_length), color='white')
# #     if width > height:
# #         new_image.paste(image, (0, int((new_image_length - height) / 2)))
# #     else:
# #         new_image.paste(image, (int((new_image_length - width) / 2), 0))
# #     return new_image
# #
# #
# # def cut_image(image):
# #     width, height = image.size
# #     item_width = int(width / 3)
# #     box_list = []
# #     for i in range(0, 3):
# #         for j in range(0, 3):
# #             print((i * item_width, j * item_width, (i + 1) * item_width, (j + 1) * item_width))
# #             box = ((j * item_width, i * item_width, (j + 1) * item_width, (i + 1) * item_width))
# #             box_list.append(box)
# #     image_list = [image.crop(box) for box in box_list]
# #     return image_list
# #
# #
# # def save_images(image_list):
# #
# #
# # # index = 1
# #
# # # index += 1
# #
#
# def split4img(img_path, num=9):
#     image = Image.open(img_path)
#
#     width, height = image.size
#     new_image_length = width if width > height else height
#     new_image = Image.new(image.mode, (new_image_length, new_image_length), color='white')
#     if width > height:
#         new_image.paste(image, (0, int((new_image_length - height) / 2)))
#     else:
#         new_image.paste(image, (int((new_image_length - width) / 2), 0))
#     # 切割图片
#     width, _ = new_image.size
#     item_width = int(width / 3)
#     box_list = []
#     for i in range(0, 3):
#         for j in range(0, 3):
#             # print((i * item_width, j * item_width, (i + 1) * item_width, (j + 1) * item_width))
#             box = ((j * item_width, i * item_width, (j + 1) * item_width, (i + 1) * item_width))
#             box_list.append(box)
#     image_list = [image.crop(box) for box in box_list]
#     # 保存图片
#     for index, img in enumerate(image_list):
#         img.save(str(index + 1) + '.png', 'PNG')
#     # save_images(image_list)
#
import poimage

img_path = "./imgs/icon2.jpg"

poimage.split4img(img_path, output_path=r'D:\workplace\code\github\poimage\dev\split_img\output')
