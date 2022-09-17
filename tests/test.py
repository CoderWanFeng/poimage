import unittest

from poimage import *


class TestImage(unittest.TestCase):
    def test_wc(self):
        txt2wordcloud(filename=r'./test.txt')

    def test_add_watermark(self):
        add_watermark(file='./test_files/images/0816.jpg', mark='python-office')

    def test_down4img(self):
        down4img(url='https://www.python-office.com/api/img-cdn/python-office/find_excel_data/group.jpg')

    # def test_img2Cartoon(self):
    #     img2Cartoon()
