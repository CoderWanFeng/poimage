import base64
import multiprocessing
import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import cv2
import jieba
import requests
# 生成词云需要使用的类库
from PIL import Image
from pofile import get_files, mkdir
from poprogress import simple_progress
from wordcloud import WordCloud

from poimage.lib.image import add_watermark_service


# from pyzbar.pyzbar import decode  # 解析二维码用


class MainImage():
    def compress_image(self, input_file, output_file, quality):
        """
        压缩图片
        :param input_file: 输入图片
        :param output_file: 输出图片
        :param quality: 质量，1-100之间，数值越低压缩率越高
        :return:
        """
        img = Image.open(input_file)
        img.save(output_file, quality=quality)

    # TODO:自动生成gif
    def image2gif(self):
        im = Image.open("1.jpg")
        images = []
        images.append(Image.open('2.jpg'))
        images.append(Image.open('3.jpg'))
        im.save('gif.gif', save_all=True, append_images=images, loop=1, duration=1, comment=b"aaabb")

    def txt2wordcloud(self, filename, color, result_file):
        """
        @Author & Date  : CoderWanFeng 2022/4/28 9:26
        @Desc  : 生成词云的代码，可以添加更多个性化功能
        @Return  ：
        """
        with open(filename, encoding='utf8') as fp:
            text = fp.read()
            # 将读取的中文文档进行分词
            # 接收分词的字符串
            word_list = jieba.cut(text)
            # 分词后在单独个体之间加上空格
            cloud_text = " ".join(word_list)

            # 生成wordcloud对象
            wc = WordCloud(background_color=color,
                           max_words=200,
                           min_font_size=15,
                           max_font_size=50,
                           width=400,
                           font_path="msyh.ttc",  # 默认的简体中文字体，没有会报错
                           )
            wc.generate(cloud_text)
            wc.to_file(result_file)

    def add_watermark(self, file, mark, output_path, color="#eaeaea", size=30, opacity=0.35, space=75,
                      angle=30):
        """
        @Author & Date  : 2022/5/6 14:33
        @Desc  : 给图片添加水印
        @Return  ： 添加了水印的图片，输出到out指定的文件夹
        """
        out = Path(output_path).absolute()  # 拼接输出文件和文件夹，为输出路径
        images_list = get_files(file)
        # for image_path in simple_progress(images_list):
        #     add_watermark_service.add_mark2file(image_path, mark, str(out), color, size, opacity, space, angle)
        processes = multiprocessing.cpu_count()
        # 创建线程池
        with ThreadPoolExecutor(max_workers=2 * processes + 1) as executor:#计算多线程数量：https://blog.51cto.com/u_15072927/4642272
            # 向线程池添加任务
            for i in range(len(images_list)):
                params = (images_list[i], mark, str(out), color, size, opacity, space, angle)
                executor.submit(lambda cxp: add_watermark_service.add_mark2file(*cxp),
                                params)  # 线程池传参：https://www.jb51.net/article/277904.htm

    def get_access_token(self, client_api, client_secret):

        # 获取token的API
        url = 'https://aip.baidubce.com/oauth/2.0/token'
        # 获取access_token需要的参数
        params = {
            # 固定参数
            'grant_type': 'client_credentials',
            # 必选参数，传入你的API Key
            'client_id': client_api,
            # 必选参数，传入你的Secret Key
            'client_secret': client_secret
        }
        # 发送请求，获取响应数据

        response = requests.post(url, params)
        # 将响应的数据转成字典类型，然后取出access_token
        access_token = eval(response.text)['access_token']
        # 将access_token返回
        return access_token

    def img2Cartoon(self, path, client_api, client_secret):
        print('=' * 30)
        print('正在进行动漫头像的转换')
        print('本仓库的视频教程：http://t.cn/A6aAvu47')
        print('这个接口调用的是百度AI平台的免费试用接口（200次），如果代码报错，大概率是试用次数没有了')
        print('获取免费使用次数的教程，我整理在这个文档里了：https://python-office.com/office/image.html')
        print('=' * 30)

        # 头像动漫化的API
        url = 'https://aip.baidubce.com/rest/2.0/image-process/v1/selfie_anime'
        # 以二进制的方式读取原始图片
        origin_im = open(path, 'rb')
        # 将图片进行base64编码
        path = base64.b64encode(origin_im.read())
        # 关闭原图片
        origin_im.close()
        # 请求的headers信息，固定写法
        headers = {'content-type': 'application/x-www-form-urlencoded'}
        # 请求的参数
        params = {
            # 开始获取的access_token
            'access_token': self.get_access_token(client_api, client_secret),
            # 图片的base64编码
            'image': path,
        }
        # 发送请求
        response = requests.post(url, data=params, headers=headers)
        # 对响应结果进行处理
        if response:
            # 打开一个文件
            f = open('result.jpg', 'wb')
            try:
                # 获取动漫头像
                anime = response.json()['image']
            except:
                raise Exception(
                    '你没有开通百度AI账号，错误原因以及【免费】开通方式，见：https://mp.weixin.qq.com/s/5Eyk2j20jzSaVcr1DTsfvw')
            # 对返回的头像进行解码
            anime = base64.b64decode(anime)
            # 将头像写入文件当中
            f.write(anime)
            f.close()
        print('*' * 20 + "{}".format('动漫头像名称：result.jpg') + '*' * 20)
        print('*' * 20 + "{}".format('您的动漫头像转换完毕，请在本代码运行的文档里查看') + '*' * 20)

    def down4img(self, url, output_path, output_name, type):
        """
        下载指定url的一张图片，支持所有格式:jpg\png\gif .etc
        """
        response = requests.get(url, stream=True)
        mkdir(output_path)
        output_path_name = os.path.join(output_path, '.'.join((output_name, type)))
        with open(output_path_name, 'wb') as output_img:
            for chunk in response:
                output_img.write(chunk)
            output_img.close()
            print(f"下载成功，图片名称：{'.'.join((output_name, type))}")

    def pencil4img(self, input_img, output_path, output_name):
        """
        :param input_img: 需要转换的图片，带路径
        :param output_path: 输出路径
        :param output_name: 输出图片的名称，带格式
        :return:
        """
        img = cv2.imread(input_img)

        ## Image to Gray Image
        gray_image = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        ## Gray Image to Inverted Gray Image
        inverted_gray_image = 255 - gray_image

        ## Blurring The Inverted Gray Image
        blurred_inverted_gray_image = cv2.GaussianBlur(inverted_gray_image, (19, 19), 0)

        ## Inverting the blurred image
        inverted_blurred_image = 255 - blurred_inverted_gray_image

        ### Preparing Photo sketching
        sketck = cv2.divide(gray_image, inverted_blurred_image, scale=256.0)

        cv2.imwrite(os.path.join(output_path, output_name), sketck)

    def split4img(self, img_path: str, output_path: str = r'./', num: int = 9):
        image = Image.open(img_path)

        width, height = image.size
        new_image_length = width if width > height else height
        new_image = Image.new(image.mode, (new_image_length, new_image_length), color='white')
        if width > height:
            new_image.paste(image, (0, int((new_image_length - height) / 2)))
        else:
            new_image.paste(image, (int((new_image_length - width) / 2), 0))
        # 切割图片
        width, _ = new_image.size
        item_width = int(width / 3)
        box_list = []
        for i in range(0, 3):
            for j in range(0, 3):
                # print((i * item_width, j * item_width, (i + 1) * item_width, (j + 1) * item_width))
                box = ((j * item_width, i * item_width, (j + 1) * item_width, (i + 1) * item_width))
                box_list.append(box)
        image_list = [image.crop(box) for box in box_list]
        # 保存图片
        abs_output_path = Path(output_path).absolute()
        for index, img in enumerate(image_list):
            img.save(os.path.join(str(abs_output_path), str(index + 1) + '.png'), 'PNG')
        abs_output_path
    # def decode_qrcode(self, qrcode_path):
    #     qrcode_content = decode(Image.open(qrcode_path))
    #     qrcode_url = qrcode_content[0][0].decode()
    #     print(qrcode_url)
    #     return qrcode_url

    def compress_to_size(self, input_file, output_file, target_size_kb, min_quality=10, max_quality=95):
        """
        将图片压缩至指定目标大小（KB）
        
        参数:
            input_file (str): 输入图片文件路径
            output_file (str): 输出图片文件路径
            target_size_kb (int): 目标大小，单位KB
            min_quality (int): 最低质量参数，默认10
            max_quality (int): 最高质量参数，默认95
            
        返回:
            dict: 包含压缩结果的字典
                - success (bool): 是否成功
                - original_size (float): 原始大小（KB）
                - compressed_size (float): 压缩后大小（KB）
                - quality (int): 使用的质量参数
                - compression_ratio (float): 压缩比例
                - message (str): 结果消息
                
        异常:
            ValueError: 当输入参数无效时
            IOError: 当文件读写失败时
            Exception: 其他异常情况
        """
        result = {
            'success': False,
            'original_size': 0,
            'compressed_size': 0,
            'quality': 0,
            'compression_ratio': 0,
            'message': ''
        }
        
        try:
            # 参数验证
            if not os.path.exists(input_file):
                raise ValueError(f"输入文件不存在: {input_file}")
                
            if target_size_kb <= 0:
                raise ValueError(f"目标大小必须大于0，当前值: {target_size_kb}")
                
            if min_quality < 1 or min_quality > 100:
                raise ValueError(f"最低质量参数必须在1-100之间，当前值: {min_quality}")
                
            if max_quality < 1 or max_quality > 100:
                raise ValueError(f"最高质量参数必须在1-100之间，当前值: {max_quality}")
                
            if min_quality >= max_quality:
                raise ValueError(f"最低质量参数必须小于最高质量参数")
            
            # 获取原始文件大小
            original_size_bytes = os.path.getsize(input_file)
            original_size_kb = original_size_bytes / 1024
            result['original_size'] = round(original_size_kb, 2)
            
            # 如果原始文件已经小于目标大小，直接复制
            if original_size_kb <= target_size_kb:
                import shutil
                shutil.copy2(input_file, output_file)
                result['success'] = True
                result['compressed_size'] = original_size_kb
                result['quality'] = max_quality
                result['compression_ratio'] = 1.0
                result['message'] = f"原始文件大小({original_size_kb:.2f}KB)已小于目标大小({target_size_kb}KB)，无需压缩"
                return result
            
            # 打开图片
            img = Image.open(input_file)
            
            # 确定图片格式
            img_format = img.format if img.format else 'JPEG'
            
            # 转换为RGB模式（如果是RGBA且要保存为JPEG）
            if img.mode == 'RGBA' and img_format == 'JPEG':
                img = img.convert('RGB')
            
            # 自适应压缩算法：二分查找最优质量参数
            target_size_bytes = target_size_kb * 1024
            low, high = min_quality, max_quality
            best_quality = min_quality
            best_size = float('inf')
            best_img = None
            
            max_iterations = 20  # 最大迭代次数
            iteration = 0
            
            while iteration < max_iterations:
                iteration += 1
                mid_quality = (low + high) // 2
                
                # 创建内存缓冲区
                from io import BytesIO
                buffer = BytesIO()
                
                # 保存到内存缓冲区
                save_kwargs = {'quality': mid_quality, 'optimize': True}
                if img_format == 'JPEG':
                    save_kwargs['progressive'] = True
                elif img_format == 'PNG':
                    save_kwargs.pop('quality', None)  # PNG不支持quality参数
                
                img.save(buffer, format=img_format, **save_kwargs)
                compressed_size = buffer.tell()
                
                # 检查是否达到目标
                if compressed_size <= target_size_bytes:
                    best_quality = mid_quality
                    best_size = compressed_size
                    best_img = buffer
                    low = mid_quality + 1  # 尝试更高的质量
                else:
                    high = mid_quality - 1  # 降低质量
                
                # 如果已经达到最优解，提前结束
                if low > high:
                    break
            
            # 如果没有找到合适的质量参数，使用最低质量
            if best_img is None:
                from io import BytesIO
                buffer = BytesIO()
                save_kwargs = {'quality': min_quality, 'optimize': True}
                if img_format == 'JPEG':
                    save_kwargs['progressive'] = True
                elif img_format == 'PNG':
                    save_kwargs.pop('quality', None)
                
                img.save(buffer, format=img_format, **save_kwargs)
                best_img = buffer
                best_quality = min_quality
                best_size = buffer.tell()
            
            # 保存压缩后的图片
            mkdir(os.path.dirname(output_file))
            with open(output_file, 'wb') as f:
                f.write(best_img.getvalue())
            
            # 计算结果
            compressed_size_kb = best_size / 1024
            result['success'] = True
            result['compressed_size'] = round(compressed_size_kb, 2)
            result['quality'] = best_quality
            result['compression_ratio'] = round(original_size_kb / compressed_size_kb, 2)
            
            if compressed_size_kb <= target_size_kb:
                result['message'] = f"成功压缩至{compressed_size_kb:.2f}KB（目标：{target_size_kb}KB），质量参数：{best_quality}"
            else:
                result['message'] = f"压缩至{compressed_size_kb:.2f}KB（目标：{target_size_kb}KB），已达到最低质量限制{min_quality}"
            
            return result
            
        except ValueError as e:
            result['message'] = f"参数错误: {str(e)}"
            return result
        except IOError as e:
            result['message'] = f"文件操作错误: {str(e)}"
            return result
        except Exception as e:
            result['message'] = f"压缩失败: {str(e)}"
            return result
