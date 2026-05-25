import unittest

from poimage import *


class TestImage(unittest.TestCase):
    def test_wc(self):
        txt2wordcloud(filename=r'./test.txt')

    def test_add_watermark(self):
        add_watermark(file='group.jpg', mark='python-office', output_path=r'./output_path')

    def test_down4img(self):
        down4img(url='https://cos.python-office.com/group/python-office-qr.jpg',
                 output_path=r'./')

    # def test_img2Cartoon(self):
    #     img2Cartoon()

    def test_pencil4img(self):
        pencil4img(input_img=r'D:\workplace\code\test\down4img\girl.jpg')

    def test_compress_image(self):
        """测试图片压缩功能 - 按质量压缩"""
        compress_image(
            input_file='group.jpg',
            output_file='./output_path/compressed_quality.jpg',
            quality=50
        )
    
    def test_compress_to_size(self):
        """测试图片压缩功能 - 按大小压缩"""
        result = compress_image(
            input_file='group.jpg',
            output_file='./output_path/compressed_size.jpg',
            target_size_mb=0.1  # 压缩到 0.1MB
        )
        print(f"压缩结果：{result}")

    # def test_decode_qrcode(self):
    #     decode_qrcode(qrcode_path=r'C:\Users\Lenovo\Desktop\temp\自媒体交流群.png')
