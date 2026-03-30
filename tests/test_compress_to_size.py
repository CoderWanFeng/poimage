# -*- coding: UTF-8 -*-
'''
测试按目标大小压缩图片功能
'''

import os
from poimage.api import image

def test_compress_to_size():
    """
    测试按目标大小压缩图片功能
    """
    
    # 测试用例1: 压缩到100KB
    print("=" * 50)
    print("测试用例1: 压缩图片到100KB")
    print("=" * 50)
    
    input_file = 'tests/group.jpg'
    output_file = 'tests/output_path/output/compressed_100kb.jpg'
    target_size = 100
    
    if os.path.exists(input_file):
        result = image.compress_to_size(input_file, output_file, target_size)
        
        print(f"原始大小: {result['original_size']} KB")
        print(f"压缩后大小: {result['compressed_size']} KB")
        print(f"目标大小: {target_size} KB")
        print(f"压缩比例: {result['compression_ratio']}")
        print(f"质量参数: {result['quality']}")
        print(f"状态: {result['message']}")
        print(f"成功: {result['success']}")
    else:
        print(f"测试文件不存在: {input_file}")
    
    print()
    
    # 测试用例2: 压缩到50KB
    print("=" * 50)
    print("测试用例2: 压缩图片到50KB")
    print("=" * 50)
    
    output_file2 = 'tests/output_path/output/compressed_50kb.jpg'
    target_size2 = 50
    
    if os.path.exists(input_file):
        result2 = image.compress_to_size(input_file, output_file2, target_size2)
        
        print(f"原始大小: {result2['original_size']} KB")
        print(f"压缩后大小: {result2['compressed_size']} KB")
        print(f"目标大小: {target_size2} KB")
        print(f"压缩比例: {result2['compression_ratio']}")
        print(f"质量参数: {result2['quality']}")
        print(f"状态: {result2['message']}")
        print(f"成功: {result2['success']}")
    else:
        print(f"测试文件不存在: {input_file}")
    
    print()
    
    # 测试用例3: 测试PNG格式
    print("=" * 50)
    print("测试用例3: 压缩PNG图片到200KB")
    print("=" * 50)
    
    png_input = 'tests/your_wordcloud.png'
    png_output = 'tests/output_path/output/compressed_png_200kb.png'
    target_size3 = 200
    
    if os.path.exists(png_input):
        result3 = image.compress_to_size(png_input, png_output, target_size3)
        
        print(f"原始大小: {result3['original_size']} KB")
        print(f"压缩后大小: {result3['compressed_size']} KB")
        print(f"目标大小: {target_size3} KB")
        print(f"压缩比例: {result3['compression_ratio']}")
        print(f"质量参数: {result3['quality']}")
        print(f"状态: {result3['message']}")
        print(f"成功: {result3['success']}")
    else:
        print(f"测试文件不存在: {png_input}")
    
    print()
    
    # 测试用例4: 测试错误处理 - 不存在的文件
    print("=" * 50)
    print("测试用例4: 测试错误处理 - 不存在的文件")
    print("=" * 50)
    
    result4 = image.compress_to_size('nonexistent.jpg', 'output.jpg', 100)
    print(f"错误处理结果: {result4['message']}")
    print(f"成功: {result4['success']}")
    
    print()
    
    # 测试用例5: 测试错误处理 - 无效的目标大小
    print("=" * 50)
    print("测试用例5: 测试错误处理 - 无效的目标大小")
    print("=" * 50)
    
    if os.path.exists(input_file):
        result5 = image.compress_to_size(input_file, 'output.jpg', -100)
        print(f"错误处理结果: {result5['message']}")
        print(f"成功: {result5['success']}")
    
    print()
    
    # 测试用例6: 测试自定义质量范围
    print("=" * 50)
    print("测试用例6: 测试自定义质量范围 (20-80)")
    print("=" * 50)
    
    output_file6 = 'tests/output_path/output/compressed_custom_quality.jpg'
    
    if os.path.exists(input_file):
        result6 = image.compress_to_size(input_file, output_file6, 80, min_quality=20, max_quality=80)
        
        print(f"原始大小: {result6['original_size']} KB")
        print(f"压缩后大小: {result6['compressed_size']} KB")
        print(f"目标大小: 80 KB")
        print(f"压缩比例: {result6['compression_ratio']}")
        print(f"质量参数: {result6['quality']}")
        print(f"状态: {result6['message']}")
        print(f"成功: {result6['success']}")
    
    print()
    
    # 测试用例7: 测试已小于目标大小的情况
    print("=" * 50)
    print("测试用例7: 测试原始文件已小于目标大小")
    print("=" * 50)
    
    small_input = 'tests/your_wordcloud.png'
    small_output = 'tests/output_path/output/small_copy.png'
    large_target = 10000  # 10MB
    
    if os.path.exists(small_input):
        result7 = image.compress_to_size(small_input, small_output, large_target)
        
        print(f"原始大小: {result7['original_size']} KB")
        print(f"压缩后大小: {result7['compressed_size']} KB")
        print(f"目标大小: {large_target} KB")
        print(f"压缩比例: {result7['compression_ratio']}")
        print(f"质量参数: {result7['quality']}")
        print(f"状态: {result7['message']}")
        print(f"成功: {result7['success']}")
    
    print()
    print("=" * 50)
    print("所有测试完成")
    print("=" * 50)

if __name__ == '__main__':
    test_compress_to_size()