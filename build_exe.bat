@echo off
echo roLabelImg 打包工具
echo ==================

:: 检查Python是否安装
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo 错误: 未找到Python，请安装Python 3.6+
    pause
    exit /b 1
)

:: 询问用户选择打包模式
echo 请选择打包模式:
echo 1. 目录模式 (推荐，启动更快)
echo 2. 单文件模式 (文件更少，但启动较慢)
echo.

set /p mode=请输入选项 (1 或 2): 

:: 询问用户是否跳过依赖检查
echo.
echo 是否跳过依赖检查和安装？
echo 1. 检查并安装依赖 (默认)
echo 2. 跳过依赖检查 (如果您已经安装了所有依赖)
echo.

set /p skip_deps=请输入选项 (1 或 2): 

:: 询问用户是否要自定义图标
echo.
echo 是否要使用自定义图标？
echo 1. 使用默认图标
echo 2. 选择自定义图标
echo.

set /p icon_choice=请输入选项 (1 或 2): 

set icon_param=
if "%icon_choice%"=="2" (
    echo.
    echo 可用的图标文件:
    dir /b icons\*.png icons\*.ico icons\*.gif 2>nul
    echo.
    echo 注意: 如果选择GIF格式图标，将自动转换为ICO格式以获得更好的兼容性
    echo 转换后的ICO文件将保存在与原GIF文件相同的目录中
    echo.
    set /p icon_file=请输入图标文件名 (例如: Drone.gif): 
    set icon_file=icons\%icon_file%
    set icon_param=--icon="%icon_file%"
    echo 将使用图标: %icon_file%
)

:: 设置跳过依赖检查参数
set skip_deps_param=
if "%skip_deps%"=="2" (
    set skip_deps_param=--skip-deps
    echo 将跳过依赖检查和安装
)

if "%mode%"=="1" (
    echo 选择了目录模式
    python build_exe.py %skip_deps_param% %icon_param%
    if %errorlevel% equ 0 (
        echo.
        echo 构建成功！可执行文件位于: dist\roLabelImg\roLabelImg.exe
    )
) else if "%mode%"=="2" (
    echo 选择了单文件模式
    python build_exe.py --onefile %skip_deps_param% %icon_param%
    if %errorlevel% equ 0 (
        echo.
        echo 构建成功！可执行文件位于: dist\roLabelImg.exe
    )
) else (
    echo 无效的选项，请输入 1 或 2
    pause
    exit /b 1
)

echo.
echo 打包过程完成
echo.

pause