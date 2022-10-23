import unittest

from poimage import *


class TestImage(unittest.TestCase):
    def test_wc(self):
        txt2wordcloud(filename=r'./test.txt')

    def test_add_watermark(self):
        add_watermark(file='group.jpg', mark='python-office',output_path=r'./output_path')

    def test_down4img(self):
        down4img(url='https://www.python-office.com/api/img-cdn/python-office/find_excel_data/group.jpg',
                 output_path=r'./')

    # def test_img2Cartoon(self):
    #     img2Cartoon()

    def test_pencil4img(self):
        pencil4img(input_img=r'D:\workplace\code\test\down4img\girl.jpg')
