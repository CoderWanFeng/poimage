'''
@Author  ：程序员晚枫，B站/抖音/微博/小红书/公众号
@WeChat     ：CoderWanFeng
@Blog      ：www.python-office.com
'''

# pip install poimage
import poimage

# 支持jpg、png等所有图片格式
poimage.del_watermark(
    input_image=r"D:\test\程序员晚枫\加了水印的图片.jpg",
    output_image=r'D:\test\程序员晚枫\去除了水印的图片.jpg')
