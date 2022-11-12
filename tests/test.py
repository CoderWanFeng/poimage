import unittest

from poimage import *


class TestImage(unittest.TestCase):
    def test_wc(self):
        txt2wordcloud(filename=r'./test.txt')

    def test_add_watermark(self):
        add_watermark(file='group.jpg', mark='python-office', output_path=r'./output_path')

    def test_down4img(self):
        down4img(url='https://python-office-1300615378.cos.ap-chongqing.myqcloud.com/python-office-qr.jpg',
                 output_path=r'./')

    # def test_img2Cartoon(self):
    #     img2Cartoon()

    def test_pencil4img(self):
        pencil4img(input_img=r'D:\workplace\code\test\down4img\girl.jpg')

    def test_decode_qrcode(self):
        decode_qrcode(qrcode_path=r'C:\Users\Lenovo\Desktop\temp\自媒体交流群.png')
