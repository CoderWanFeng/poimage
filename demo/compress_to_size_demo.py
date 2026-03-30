# -*- coding: UTF-8 -*-
'''
按目标大小压缩图片功能演示

本示例展示如何使用poimage库的compress_to_size功能
将图片压缩到指定的大小（KB）
'''

from poimage.api import image
import os

def demo_basic_usage():
    """
    基础使用示例：将图片压缩到指定大小
    """
    print("=" * 60)
    print("基础使用示例")
    print("=" * 60)
    
    # 示例1：压缩到100KB
    result = image.compress_to_size(
        input_file='tests/group.jpg',
        output_file='demo/compressed_100kb.jpg',
        target_size_kb=100
    )
    
    print(f"原始大小: {result['original_size']} KB")
    print(f"压缩后大小: {result['compressed_size']} KB")
    print(f"压缩比例: {result['compression_ratio']}")
    print(f"质量参数: {result['quality']}")
    print(f"状态: {result['message']}")
    print()

def demo_custom_quality_range():
    """
    自定义质量范围示例
    """
    print("=" * 60)
    print("自定义质量范围示例")
    print("=" * 60)
    
    # 限制质量范围在30-70之间
    result = image.compress_to_size(
        input_file='tests/group.jpg',
        output_file='demo/compressed_limited_quality.jpg',
        target_size_kb=80,
        min_quality=30,  # 最低质量
        max_quality=70   # 最高质量
    )
    
    print(f"质量范围: 30-70")
    print(f"实际使用质量: {result['quality']}")
    print(f"压缩后大小: {result['compressed_size']} KB")
    print(f"状态: {result['message']}")
    print()

def demo_different_targets():
    """
    不同目标大小对比示例
    """
    print("=" * 60)
    print("不同目标大小对比示例")
    print("=" * 60)
    
    targets = [200, 100, 50, 20]
    results = []
    
    for target in targets:
        output_file = f'demo/compressed_{target}kb.jpg'
        result = image.compress_to_size(
            input_file='tests/group.jpg',
            output_file=output_file,
            target_size_kb=target
        )
        results.append(result)
    
    # 输出对比表格
    print(f"{'目标(KB)':<12} {'实际(KB)':<12} {'压缩比例':<10} {'质量参数':<10} {'状态'}")
    print("-" * 60)
    for result in results:
        target = result['compressed_size']
        original = result['original_size']
        ratio = result['compression_ratio']
        quality = result['quality']
        success = "✓" if result['success'] else "✗"
        print(f"{target:<12.2f} {result['compressed_size']:<12.2f} {ratio:<10.2f} {quality:<10} {success}")
    print()

def demo_error_handling():
    """
    错误处理示例
    """
    print("=" * 60)
    print("错误处理示例")
    print("=" * 60)
    
    # 示例1：文件不存在
    print("1. 测试不存在的文件:")
    result = image.compress_to_size('nonexistent.jpg', 'output.jpg', 100)
    print(f"   错误信息: {result['message']}")
    print(f"   成功状态: {result['success']}")
    print()
    
    # 示例2：无效的目标大小
    print("2. 测试无效的目标大小:")
    result = image.compress_to_size('tests/group.jpg', 'output.jpg', -50)
    print(f"   错误信息: {result['message']}")
    print(f"   成功状态: {result['success']}")
    print()
    
    # 示例3：无效的质量参数
    print("3. 测试无效的质量参数:")
    result = image.compress_to_size('tests/group.jpg', 'output.jpg', 100, min_quality=150)
    print(f"   错误信息: {result['message']}")
    print(f"   成功状态: {result['success']}")
    print()

def demo_already_small():
    """
    原始文件已小于目标大小的示例
    """
    print("=" * 60)
    print("原始文件已小于目标大小示例")
    print("=" * 60)
    
    # 使用一个较小的PNG文件，目标设置得很大
    result = image.compress_to_size(
        input_file='tests/your_wordcloud.png',
        output_file='demo/small_copy.png',
        target_size_kb=10000  # 10MB
    )
    
    print(f"原始大小: {result['original_size']} KB")
    print(f"目标大小: 10000 KB")
    print(f"压缩后大小: {result['compressed_size']} KB")
    print(f"状态: {result['message']}")
    print("说明: 当原始文件已小于目标大小时，函数会直接复制文件，不进行压缩")
    print()

def demo_batch_compression():
    """
    批量压缩示例
    """
    print("=" * 60)
    print("批量压缩示例")
    print("=" * 60)
    
    # 假设有一个文件夹包含多张图片
    input_files = ['tests/group.jpg', 'tests/your_wordcloud.png']
    target_size = 50
    
    print(f"将以下图片压缩到 {target_size}KB:")
    print("-" * 60)
    
    for i, input_file in enumerate(input_files, 1):
        if os.path.exists(input_file):
            output_file = f'demo/batch_compressed_{i}.jpg'
            result = image.compress_to_size(input_file, output_file, target_size)
            
            print(f"{i}. {os.path.basename(input_file)}")
            print(f"   原始: {result['original_size']:.2f}KB -> 压缩: {result['compressed_size']:.2f}KB")
            print(f"   压缩比例: {result['compression_ratio']:.2f}x")
            print(f"   质量: {result['quality']}")
            print()
        else:
            print(f"{i}. 文件不存在: {input_file}")
            print()

def main():
    """
    主函数：运行所有演示示例
    """
    print("\n" + "=" * 60)
    print("poimage 按目标大小压缩图片功能演示")
    print("=" * 60 + "\n")
    
    # 确保demo目录存在
    os.makedirs('demo', exist_ok=True)
    
    # 运行各种演示
    demo_basic_usage()
    demo_custom_quality_range()
    demo_different_targets()
    demo_error_handling()
    demo_already_small()
    demo_batch_compression()
    
    print("=" * 60)
    print("演示完成！")
    print("=" * 60)
    print("\n提示：")
    print("- 压缩后的图片保存在 demo/ 目录下")
    print("- 可以根据需要调整目标大小和质量范围")
    print("- 压缩算法会自动寻找最优的质量参数")
    print("- 对于PNG格式，压缩效果可能不如JPEG明显")

if __name__ == '__main__':
    main()