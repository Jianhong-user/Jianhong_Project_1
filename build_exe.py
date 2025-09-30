import os
import sys
import shutil
import argparse
from subprocess import call

# 尝试导入Pillow库，用于图标转换
try:
    from PIL import Image
    PILLOW_AVAILABLE = True
except ImportError:
    PILLOW_AVAILABLE = False

def check_dependencies():
    """
    检查并安装必要的依赖项
    """
    dependencies = [
        "PyQt5",
        "lxml",
        "pyinstaller",
        "pillow"  # 添加Pillow库，用于图标转换
    ]
    
    for dep in dependencies:
        try:
            if dep.lower() == "pillow":
                __import__("PIL")
            else:
                __import__(dep.lower())
            print(f"{dep} 已安装，跳过安装步骤")
        except ImportError:
            print(f"正在安装 {dep}...")
            # 使用--no-cache-dir参数避免连接超时问题
            try:
                call([sys.executable, "-m", "pip", "install", "--no-cache-dir", dep])
                print(f"{dep} 安装完成")
            except Exception as e:
                print(f"安装 {dep} 时出错: {e}")
                print(f"请手动安装 {dep} 后再运行此脚本")
                sys.exit(1)



def build_exe(onefile=False, icon_path=None):
    """
    使用PyInstaller将roLabelImg打包成exe文件
    
    Args:
        onefile: 是否打包成单个文件
    """
    print("开始构建roLabelImg.exe...")
    
    # 清理之前的构建文件
    if os.path.exists("dist"):
        shutil.rmtree("dist")
    if os.path.exists("build"):
        shutil.rmtree("build")
    if os.path.exists("roLabelImg.spec"):
        os.remove("roLabelImg.spec")
    
    # 构建命令
    cmd = [
        "pyinstaller",
        "--name=roLabelImg",
        "--windowed",  # 使用GUI模式，不显示控制台
        "--add-data=data;data",  # 添加数据文件，Windows使用分号分隔
        "--add-data=icons;icons",  # 添加图标文件
        "--add-data=libs;libs",  # 添加libs目录
        "--add-data=resources.py;.",  # 添加resources.py文件到根目录
        "--add-data=roLabelImg使用说明.md;.",  # 添加使用说明文档
        "--add-data=README.md;.",  # 添加README文档
        "--workpath=build",  # 指定构建工作目录
        "--distpath=dist",  # 指定输出目录
        "--paths=libs",  # 添加libs目录到Python路径
        "--hidden-import=PyQt5",
        "--hidden-import=PyQt5.QtCore",
        "--hidden-import=PyQt5.QtGui",
        "--hidden-import=PyQt5.QtWidgets",
        "--hidden-import=lxml.etree",
        "--hidden-import=resources",  # 添加resources模块的隐式导入
        "--hidden-import=libs",
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
        "--hidden-import=lib",
        "--hidden-import=shape",
        "--hidden-import=canvas",
        "--hidden-import=zoomWidget",
        "--hidden-import=labelDialog",
        "--hidden-import=colorDialog",
        "--hidden-import=labelFile",
        "--hidden-import=toolBar",
        "--hidden-import=pascal_voc_io",
        "--hidden-import=ustr",
    ]
    
    def convert_to_ico(input_file):
        """
        将图像文件转换为ICO格式
        
        Args:
            input_file: 输入图像文件路径（支持GIF、PNG、JPG等格式）
        
        Returns:
            输出ICO文件的路径，如果转换失败则返回None
        """
        if not PILLOW_AVAILABLE:
            print("警告: Pillow库未安装，无法转换图标格式")
            return None
        
        if not os.path.exists(input_file):
            print(f"错误: 输入文件 {input_file} 不存在")
            return None
        
        # 如果已经是ICO格式，则直接返回
        if input_file.lower().endswith(".ico"):
            return input_file
        
        # 生成输出文件路径
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
            print(f"转换图标失败: {e}")
            return None

# 设置图标
    if icon_path:
        # 检查图标文件是否存在
        if os.path.exists(icon_path):
            # 如果是GIF格式，尝试转换为ICO格式
            if icon_path.lower().endswith(".gif"):
                print(f"检测到GIF格式图标: {icon_path}，尝试转换为ICO格式...")
                ico_path = convert_to_ico(icon_path)
                if ico_path:
                    cmd.append(f"--icon={ico_path}")
                    print(f"使用转换后的ICO图标: {ico_path}")
                else:
                    print(f"警告: 无法转换图标 {icon_path}，将使用原始图标")
                    cmd.append(f"--icon={icon_path}")
                    print(f"使用原始图标: {icon_path}")
            else:
                cmd.append(f"--icon={icon_path}")
                print(f"使用自定义图标: {icon_path}")
        else:
            print(f"警告: 图标文件 {icon_path} 不存在，将使用默认图标")
            # 尝试使用默认图标
            default_icon = "icons/Click.ico"
            if os.path.exists(default_icon):
                cmd.append(f"--icon={default_icon}")
                print(f"使用默认图标: {default_icon}")
    else:
        # 尝试使用默认图标
        default_icon = "icons/Click.ico"
        if os.path.exists(default_icon):
            cmd.append(f"--icon={default_icon}")
            print(f"使用默认图标: {default_icon}")
        else:
            # 尝试转换GIF图标
            gif_icon = "icons/Click.gif"
            if os.path.exists(gif_icon):
                print(f"找到GIF图标: {gif_icon}，尝试转换为ICO格式...")
                ico_path = convert_to_ico(gif_icon)
                if ico_path:
                    cmd.append(f"--icon={ico_path}")
                    print(f"使用转换后的ICO图标: {ico_path}")
                else:
                    print("无法转换图标，将使用默认图标")
            else:
                print("未找到图标文件，将使用系统默认图标")
    
    # 如果选择单文件模式，添加--onefile参数
    if onefile:
        cmd.append("--onefile")
    else:
        cmd.append("--onedir")
    
    # 添加主程序文件
    cmd.append("roLabelImg.py")
    
    # 执行构建命令
    print("执行PyInstaller命令...")
    call(cmd)
    
    # 输出结果信息
    if onefile:
        print("构建完成！")
        print("可执行文件位于: dist/roLabelImg.exe")
    else:
        print("构建完成！")
        print("可执行文件位于: dist/roLabelImg/roLabelImg.exe")

if __name__ == "__main__":
    # 解析命令行参数
    parser = argparse.ArgumentParser(description="构建roLabelImg可执行文件")
    parser.add_argument("--onefile", action="store_true", help="打包成单个可执行文件")
    parser.add_argument("--icon", type=str, help="指定应用图标文件路径")
    parser.add_argument("--skip-deps", action="store_true", help="跳过依赖检查和安装")
    args = parser.parse_args()
    
    # 如果指定了跳过依赖检查
    if args.skip_deps:
        print("跳过依赖检查和安装...")
        # 直接检查Pillow是否可用
        try:
            __import__("PIL")
            PILLOW_AVAILABLE = True
        except ImportError:
            PILLOW_AVAILABLE = False
    else:
        # 检查依赖项
        check_dependencies()
    
    # 执行构建
    build_exe(onefile=args.onefile, icon_path=args.icon)