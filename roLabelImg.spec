# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['roLabelImg.py'],
    pathex=['libs'],
    binaries=[],
    datas=[('data', 'data'), ('icons', 'icons'), ('libs', 'libs'), ('resources.py', '.')],
    hiddenimports=['PyQt5', 'PyQt5.QtCore', 'PyQt5.QtGui', 'PyQt5.QtWidgets', 'lxml.etree', 'resources', 'libs', 'libs.lib', 'libs.shape', 'libs.canvas', 'libs.zoomWidget', 'libs.labelDialog', 'libs.colorDialog', 'libs.labelFile', 'libs.toolBar', 'libs.pascal_voc_io', 'libs.ustr', 'lib', 'shape', 'canvas', 'zoomWidget', 'labelDialog', 'colorDialog', 'labelFile', 'toolBar', 'pascal_voc_io', 'ustr'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='roLabelImg',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='roLabelImg',
)
