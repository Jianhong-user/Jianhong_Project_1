# roLabelImg 打包指南

本文档提供了将 roLabelImg 打包成 Windows 可执行文件 (EXE) 的步骤。

## 前提条件

- Python 3.6 或更高版本
- pip 包管理器
- Windows 操作系统

## 打包步骤

### 方法一：使用批处理文件（推荐）

1. 双击运行 `build_exe.bat` 文件
2. 选择打包模式：
   - 目录模式（推荐）：所有文件打包在一个目录中，启动更快
   - 单文件模式：打包成单个可执行文件，文件更少但启动较慢
3. 选择是否跳过依赖检查：
   - 检查并安装依赖（默认）：脚本会检查并安装所需的依赖项
   - 跳过依赖检查：如果您已经安装了所有依赖项，选择此选项可以避免重新安装
4. 选择图标选项：
   - 使用默认图标（不指定自定义图标）
   - 选择自定义图标（从显示的可用图标列表中选择）
5. 等待打包过程完成
6. 打包完成后，可执行文件将位于：
   - 目录模式：`dist/roLabelImg/roLabelImg.exe`
   - 单文件模式：`dist/roLabelImg.exe`

### 方法二：手动运行 Python 脚本

1. 打开命令提示符或 PowerShell
2. 导航到 roLabelImg 项目目录
3. 运行以下命令之一：
   ```
   # 目录模式（推荐）
   python build_exe.py
   
   # 单文件模式
   python build_exe.py --onefile
   
   # 使用自定义图标（目录模式）
   python build_exe.py --icon="icons/Drone sketch animation.gif"
   
   # 使用自定义图标（单文件模式）
   python build_exe.py --onefile --icon="icons/Drone sketch animation.gif"
   
   # 跳过依赖检查（如果已安装所有依赖）
   python build_exe.py --skip-deps
   
   # 组合使用参数
   python build_exe.py --onefile --skip-deps --icon="icons/Drone.gif"
   ```
4. 等待打包过程完成
5. 打包完成后，可执行文件将位于：
   - 目录模式：`dist/roLabelImg/roLabelImg.exe`
   - 单文件模式：`dist/roLabelImg.exe`

## 打包过程说明

打包脚本会执行以下操作：

1. 根据选择，检查并安装必要的依赖项（PyQt5、lxml、PyInstaller、Pillow）
   - 如果选择跳过依赖检查，此步骤将被省略
   - 如果您的网络连接不稳定或已安装所有依赖，建议选择跳过依赖检查
2. 清理之前的构建文件（如果存在）
3. 根据选择的模式，使用 PyInstaller 将 roLabelImg 打包成可执行文件：
   - 目录模式：生成包含多个文件的目录
   - 单文件模式：生成单个可执行文件
4. 应用选择的图标（默认或自定义）
   - 如果选择GIF格式图标，会自动转换为ICO格式（需要Pillow库）
5. 将必要的数据文件、图标文件和libs目录包含在可执行文件中
6. 添加必要的隐藏导入，确保所有模块都能被正确打包

我们对源代码进行了以下修改，以解决可能的模块导入问题：

1. 修改了 `roLabelImg.py` 文件中的导入语句，添加了备选导入路径
2. 更新了 `libs/__init__.py` 文件，使其能正确导出所有模块
3. 在 `build_exe.py` 中添加了 `--add-data=libs;libs` 参数，确保libs目录被包含在打包文件中

## 分发应用程序

打包完成后，您可以将 `dist/roLabelImg` 目录中的所有文件分发给用户。用户只需双击 `roLabelImg.exe` 即可运行应用程序，无需安装 Python 或任何依赖项。

## 故障排除

如果在打包过程中遇到问题，请检查以下几点：

1. 依赖项安装问题：
   - 如果依赖项安装过程中出现网络超时或连接错误，请选择跳过依赖检查选项
   - 您可以手动安装所需的依赖项：
   ```
   pip install PyQt5 lxml pyinstaller pillow --no-cache-dir
   ```
   - 使用 `--no-cache-dir` 参数可以避免某些网络缓存问题
   - 如果您已经安装了所有依赖项，建议在运行打包脚本时选择跳过依赖检查

2. 如果遇到 "hidden import" 相关的错误，可能需要在 `build_exe.py` 中添加更多的 `--hidden-import` 参数

3. 如果自定义图标不生效，请确保：
   - 图标文件路径正确
   - 图标文件格式为 .ico 或 .png（推荐使用 .ico 格式）
   - 图标文件名中如果包含空格，请确保在命令行中使用引号包围路径
   - 图标文件分辨率适合（建议使用 256x256 像素）
   - 注意：PyInstaller 在 Windows 上更好地支持 .ico 格式图标
   
   我们已经添加了自动将 GIF 图标转换为 ICO 格式的功能：
   - 当您选择 GIF 格式的图标时，脚本会自动将其转换为 ICO 格式
   - 转换后的 ICO 文件将保存在与原 GIF 文件相同的目录中
   - 如果您希望使用动态图标，请注意 Windows 应用图标不支持动画效果，只会显示 GIF 的第一帧

4. 如果运行打包后的 exe 文件时出现 `ModuleNotFoundError: No module named 'lib'` 错误：
   - 这是因为打包后的程序无法正确找到 libs 目录中的模块
   - 我们已经修改了 `roLabelImg.py` 文件，添加了备选导入路径
   - 确保 `build_exe.py` 中包含了 `--add-data=libs;libs` 参数
   - 确保所有需要的模块都在 `--hidden-import` 参数中列出

5. 对于其他问题，请查看 PyInstaller 的文档：https://pyinstaller.org/en/stable/