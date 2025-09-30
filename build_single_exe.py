#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
roLabelImg 单文件打包脚本
专门用于创建单个exe文件，无源码暴露
"""

import os
import sys
import shutil
from subprocess import call

def build_single_exe():
    """
    使用PyInstaller将roLabelImg打包成单个exe文件
    """
    print("=" * 50)
    print("roLabelImg 单文件打包工具")
    print("=" * 50)
    
    # 检查PyInstaller是否安装
    try:
        import PyInstaller
        print(f"✓ PyInstaller 已安装 (版本: {PyInstaller.__version__})")
    except ImportError:
        print("✗ PyInstaller 未安装，正在安装...")
        call([sys.executable, "-m", "pip", "install", "pyinstaller"])
        print("✓ PyInstaller 安装完成")
    
    # 清理之前的构建文件
    print("\n清理之前的构建文件...")
    for dir_name in ["dist", "build"]:
        if os.path.exists(dir_name):
            shutil.rmtree(dir_name)
            print(f"✓ 已删除 {dir_name} 目录")
    
    if os.path.exists("roLabelImg.spec"):
        os.remove("roLabelImg.spec")
        print("✓ 已删除 roLabelImg.spec 文件")
    
    # 检查图标文件
    icon_path = None
    for icon_file in ["icons/Click.ico", "icons/Click.gif"]:
        if os.path.exists(icon_file):
            icon_path = icon_file
            print(f"✓ 找到图标文件: {icon_file}")
            break
    
    if not icon_path:
        print("⚠ 未找到图标文件，将使用默认图标")
    
    # 构建PyInstaller命令
    print("\n开始构建单个exe文件...")
    cmd = [
        "pyinstaller",
        "--name=roLabelImg",
        "--onefile",  # 单文件模式
        "--windowed",  # GUI模式，不显示控制台
        "--noconfirm",  # 不询问确认
        "--clean",  # 清理临时文件
        
        # 添加数据文件
        "--add-data=data;data",
        "--add-data=icons;icons",
        "--add-data=libs;libs",
        "--add-data=resources.py;.",
        "--add-data=roLabelImg使用说明.md;.",
        "--add-data=README.md;.",
        
        # 设置路径
        "--paths=libs",
        
        # 隐式导入
        "--hidden-import=PyQt5",
        "--hidden-import=PyQt5.QtCore",
        "--hidden-import=PyQt5.QtGui",
        "--hidden-import=PyQt5.QtWidgets",
        "--hidden-import=lxml.etree",
        "--hidden-import=resources",
        "--hidden-import=libs.lib",
        "--hidden-import=libs.shape",
        "--hidden-import=libs.canvas",
        "--hidden-import=libs.zoomWidget",
        "--hidden-import=libs.labelDialog",
        "--hidden-import=libs.colorDialog",
        "--hidden-import=libs.labelFile",
        "--hidden-import=libs.toolBar",
        "--hidden-import=libs.pascal_voc_io",
        "--hidden-import=libs.ustr",
        
        # 排除不需要的模块
        "--exclude-module=tkinter",
        "--exclude-module=matplotlib",
        "--exclude-module=numpy",
        "--exclude-module=scipy",
        
        # 优化选项
        "--strip",  # 去除调试信息
        "--optimize=2",  # 最高级别优化
    ]
    
    # 添加图标
    if icon_path:
        cmd.append(f"--icon={icon_path}")
    
    # 添加主程序文件
    cmd.append("roLabelImg.py")
    
    # 执行构建
    print("执行PyInstaller命令...")
    print("命令:", " ".join(cmd))
    print("\n" + "=" * 50)
    
    result = call(cmd)
    
    print("\n" + "=" * 50)
    if result == 0:
        exe_path = os.path.join("dist", "roLabelImg.exe")
        if os.path.exists(exe_path):
            file_size = os.path.getsize(exe_path) / (1024 * 1024)  # MB
            print("🎉 构建成功！")
            print(f"📁 可执行文件位置: {exe_path}")
            print(f"📊 文件大小: {file_size:.1f} MB")
            print("\n✨ 特性:")
            print("  • 单个exe文件，无需安装")
            print("  • 无源码暴露，安全可靠")
            print("  • 包含完整功能和说明文档")
            print("  • 支持批量删除和撤销功能")
            print("  • 内置标注特效和随机颜色")
        else:
            print("❌ 构建失败：未找到输出文件")
            return False
    else:
        print("❌ 构建失败")
        return False
    
    return True

if __name__ == "__main__":
    success = build_single_exe()
    
    print("\n" + "=" * 50)
    if success:
        print("✅ 打包完成！您可以将 dist/roLabelImg.exe 分发给用户使用。")
    else:
        print("❌ 打包失败，请检查错误信息。")
    
    input("\n按回车键退出...")