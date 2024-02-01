# -*- coding: UTF-8 -*-
'''
@学习网站      ：www.python-office.com
@读者群     ：http://www.python4office.cn/wechat-group/
@作者  ：B站/抖音/微博/小红书/公众号，都叫：程序员晚枫，微信：CoderWanFeng
@代码日期    ：2024/2/1 0:32 
@本段代码的视频说明     ：
'''
import multiprocessing
import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from PIL import Image
from pofile import get_files, mkdir

from poimage.lib.image.add_watermark_service import im_add_mark


def add_mark2file(imageFile, text, out, color, size, opacity, space, angle):
    '''
    添加水印，然后保存图片
    '''
    name = os.path.basename(imageFile)
    new_name = os.path.join(out, name)
    try:
        im = Image.open(imageFile)
        image = im_add_mark(im, text, color, size, opacity, space, angle)
        mkdir(out)
        if os.path.splitext(new_name)[1] != '.png':
            image = image.convert('RGB')
        image.save(new_name)
        print(new_name, "保存成功。")
    except Exception as e:
        print(new_name, "保存失败。错误信息：", e)


def add(num):
    print(num)


def add_watermark(file, mark='程序员晚枫', output_path=r'./multi', color="#eaeaea", size=30, opacity=0.35, space=75,
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
    # math.ceil(images_list / processes)
    # 创建进程池
    with ThreadPoolExecutor(max_workers=processes) as executor:
        # 向进程池添加任务
        for i in range(len(images_list)):
            params = (images_list[i], mark, str(out), color, size, opacity, space, angle)
            # executor.submit(add_mark2file, params)
            executor.submit(lambda cxp:add_mark2file(*cxp),params)
        executor.submit(add, (1))
    print("All processes are done.")


if __name__ == '__main__':
    add_watermark(r'D:\test\py310\image\imgs')
