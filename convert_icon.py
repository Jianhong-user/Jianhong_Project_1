#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
将GIF图标转换为ICO格式，以便PyInstaller在Windows上使用
"""

import os
import sys
from PIL import Image

def convert_to_ico(input_file, output_file=None):
    """
    将图像文件转换为ICO格式
    
    Args:
        input_file: 输入图像文件路径（支持GIF、PNG、JPG等格式）
        output_file: 输出ICO文件路径，如果不指定，则使用输入文件名并更改扩展名为.ico
    
    Returns:
        输出ICO文件的路径
    """
    if not os.path.exists(input_file):
        print(f"错误: 输入文件 {input_file} 不存在")
        return None
    
    if output_file is None:
        # 如果没有指定输出文件，则使用输入文件名并更改扩展名为.ico
        file_name, _ = os.path.splitext(input_file)
        output_file = f"{file_name}.ico"
    
    try:
        # 打开图像文件
        img = Image.open(input_file)
        
        # 确保图像是正方形的，如果不是，则裁剪为正方形
        width, height = img.size
        size = min(width, height)
        left = (width - size) // 2
        top = (height - size) // 2
        right = left + size
        bottom = top + size
        img = img.crop((left, top, right, bottom))
        
        # 调整图像大小为标准图标尺寸（多尺寸）
        icon_sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
        img.save(output_file, format='ICO', sizes=icon_sizes)
        
        print(f"成功将 {input_file} 转换为 {output_file}")
        return output_file
    except Exception as e:
        print(f"转换失败: {e}")
        return None

def main():
    # 检查命令行参数
    if len(sys.argv) < 2:
        print("用法: python convert_icon.py <输入图像文件> [输出ICO文件]")
        return
    
    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None
    
    convert_to_ico(input_file, output_file)

if __name__ == "__main__":
    main()