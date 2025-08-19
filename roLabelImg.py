#!/usr/bin/env python
# -*- coding: utf8 -*-
import codecs
import os.path
import re
import sys
import subprocess
import hashlib

from functools import partial
from collections import defaultdict

try:
    from PyQt5.QtGui import *
    from PyQt5.QtCore import *
    from PyQt5.QtWidgets import *
    from PyQt5.QtCore import QTimer  # 添加这行
except ImportError:
    # needed for py3+qt4
    # Ref:
    # http://pyqt.sourceforge.net/Docs/PyQt4/incompatible_apis.html
    # http://stackoverflow.com/questions/21217399/pyqt4-qtcore-qvariant-object-instead-of-a-string
    if sys.version_info.major >= 3:
        import sip
        sip.setapi('QVariant', 2)
    from PyQt4.QtGui import *
    from PyQt4.QtCore import *
    from PyQt4.QtCore import QTimer  # 也在PyQt4部分添加

import resources
# Add internal libs
dir_name = os.path.abspath(os.path.dirname(__file__))
libs_path = os.path.join(dir_name, 'libs')
sys.path.insert(0, libs_path)

try:
    # 首先尝试直接导入
    from lib import struct, newAction, newIcon, addActions, fmtShortcut
    from shape import Shape, DEFAULT_LINE_COLOR, DEFAULT_FILL_COLOR
    # from canvas import Canvas  # 注释掉这行
    from libs.canvas import Canvas  # 强制使用libs中的Canvas
    from zoomWidget import ZoomWidget
    from labelDialog import LabelDialog
    from colorDialog import ColorDialog
    from labelFile import LabelFile, LabelFileError
    from toolBar import ToolBar
except ImportError:
    # 如果直接导入失败，尝试从libs包导入
    from libs.lib import struct, newAction, newIcon, addActions, fmtShortcut
    from libs.shape import Shape, DEFAULT_LINE_COLOR, DEFAULT_FILL_COLOR
    from libs.canvas import Canvas
    from libs.zoomWidget import ZoomWidget
    from libs.labelDialog import LabelDialog
    from libs.colorDialog import ColorDialog
    from libs.labelFile import LabelFile, LabelFileError
    from libs.toolBar import ToolBar
try:
    # 首先尝试直接导入
    from pascal_voc_io import PascalVocReader
    from pascal_voc_io import XML_EXT
    from ustr import ustr
except ImportError:
    # 如果直接导入失败，尝试从libs包导入
    from libs.pascal_voc_io import PascalVocReader
    from libs.pascal_voc_io import XML_EXT
    from libs.ustr import ustr

__appname__ = 'roLabelImg'

# Utility functions and classes.


def have_qstring():
    '''p3/qt5 get rid of QString wrapper as py3 has native unicode str type'''
    return not (sys.version_info.major >= 3 or QT_VERSION_STR.startswith('5.'))


def util_qt_strlistclass():
    return QStringList if have_qstring() else list


class WindowMixin(object):

    def menu(self, title, actions=None):
        menu = self.menuBar().addMenu(title)
        if actions:
            addActions(menu, actions)
        return menu

    def toolbar(self, title, actions=None):
        toolbar = ToolBar(title)
        toolbar.setObjectName(u'%sToolBar' % title)
        # toolbar.setOrientation(Qt.Vertical)
        toolbar.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        if actions:
            addActions(toolbar, actions)
        self.addToolBar(Qt.LeftToolBarArea, toolbar)
        return toolbar


# PyQt5: TypeError: unhashable type: 'QListWidgetItem'
class HashableQListWidgetItem(QListWidgetItem):

    def __init__(self, *args):
        super(HashableQListWidgetItem, self).__init__(*args)

    def __hash__(self):
        return hash(id(self))


class MainWindow(QMainWindow, WindowMixin):
    FIT_WINDOW, FIT_WIDTH, MANUAL_ZOOM = list(range(3))
    selectionChanged = pyqtSignal(bool)  # 添加选择改变信号

    def __init__(self, defaultFilename=None, defaultPrefdefClassFile=None):
        super(MainWindow, self).__init__()
        self.setWindowTitle(__appname__)
        # Save as Pascal voc xml
        self.defaultSaveDir = None
        self.usingPascalVocFormat = True
        # For loading all image under a directory
        self.mImgList = []
        self.dirname = None
        self.labelHist = []
        self.lastOpenDir = None

        # Whether we need to save or not.
        self.dirty = False

        self.isEnableCreate = True
        self.isEnableCreateRo = True

        # Enble auto saving if pressing next
        self.autoSaving = True
        self._noSelectionSlot = False
        self._beginner = True
        self.screencastViewer = "firefox"
        self.screencast = "https://youtu.be/7D5lvol_QRA"
        # For a demo of original labelImg, please see "https://youtu.be/p0nR2YsCY_U"

        # 添加进度显示相关变量
        self.progressLabel = None
        
        # 添加模式显示标签 - 新的美观设计
        self.modeLabel = QLabel()
        self.modeLabel.setFixedHeight(32)
        self.modeLabel.setAlignment(Qt.AlignCenter)
        
        # 设置现代化样式
        beginner_style = """
            QLabel {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                    stop:0 #4CAF50, stop:1 #45a049);
                color: white;
                font-weight: bold;
                font-size: 12px;
                border-radius: 16px;
                padding: 6px 16px;
                margin: 2px;
                border: 2px solid #388E3C;
            }
            QLabel:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                    stop:0 #45a049, stop:1 #4CAF50);
            }
        """
        
        advanced_style = """
            QLabel {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                    stop:0 #FF6B35, stop:1 #F7931E);
                color: white;
                font-weight: bold;
                font-size: 12px;
                border-radius: 16px;
                padding: 6px 16px;
                margin: 2px;
                border: 2px solid #E65100;
                box-shadow: 0 2px 4px rgba(0,0,0,0.2);
            }
            QLabel:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                    stop:0 #F7931E, stop:1 #FF6B35);
                transform: translateY(-1px);
            }
        """
        
        # 存储样式以便切换时使用
        self.beginnerModeStyle = beginner_style
        self.advancedModeStyle = advanced_style
        
        # 添加双击放大相关变量
        self.isZoomedIn = False  # 是否已放大
        self.originalZoom = 100  # 原始缩放比例
        self.zoomCenter = None   # 放大中心点

        # Main widgets and related state.
        self.labelDialog = LabelDialog(parent=self, listItem=self.labelHist)
        
        self.itemsToShapes = {}
        self.shapesToItems = {}
        self.prevLabelText = ''

        listLayout = QVBoxLayout()
        listLayout.setContentsMargins(0, 0, 0, 0)
        
        # Create a widget for using default label
        self.useDefautLabelCheckbox = QCheckBox(u'Use default label')
        self.useDefautLabelCheckbox.setChecked(False)
        self.defaultLabelTextLine = QLineEdit()
        useDefautLabelQHBoxLayout = QHBoxLayout()       
        useDefautLabelQHBoxLayout.addWidget(self.useDefautLabelCheckbox)
        useDefautLabelQHBoxLayout.addWidget(self.defaultLabelTextLine)
        useDefautLabelContainer = QWidget()
        useDefautLabelContainer.setLayout(useDefautLabelQHBoxLayout)

        # Create a widget for edit and diffc button
        self.diffcButton = QCheckBox(u'difficult')
        self.diffcButton.setChecked(False)
        self.diffcButton.stateChanged.connect(self.btnstate)
        self.editButton = QToolButton()
        self.editButton.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)

        # Add some of widgets to listLayout 
        listLayout.addWidget(self.editButton)
        listLayout.addWidget(self.diffcButton)
        listLayout.addWidget(useDefautLabelContainer)

        # Create and add a widget for showing current label items
        self.labelList = QListWidget()
        # 设置为多选模式
        self.labelList.setSelectionMode(QAbstractItemView.ExtendedSelection)
        labelListContainer = QWidget()
        labelListContainer.setLayout(listLayout)
        self.labelList.itemActivated.connect(self.labelSelectionChanged)
        self.labelList.itemSelectionChanged.connect(self.labelSelectionChanged)
        self.labelList.itemDoubleClicked.connect(self.editLabel)
        # Connect to itemChanged to detect checkbox changes.
        self.labelList.itemChanged.connect(self.labelItemChanged)
        listLayout.addWidget(self.labelList)

        self.dock = QDockWidget(u'Box Labels', self)
        self.dock.setObjectName(u'Label')
        self.dock.setWidget(labelListContainer)

        # Tzutalin 20160906 : Add file list and dock to move faster
        self.fileListWidget = QListWidget()
        self.fileListWidget.itemDoubleClicked.connect(self.fileitemDoubleClicked)
        filelistLayout = QVBoxLayout()
        filelistLayout.setContentsMargins(0, 0, 0, 0)
        filelistLayout.addWidget(self.fileListWidget)
        fileListContainer = QWidget()
        fileListContainer.setLayout(filelistLayout)
        self.filedock = QDockWidget(u'File List', self)
        self.filedock.setObjectName(u'File')
        self.filedock.setWidget(fileListContainer)

        # 添加统计面板
        self.createStatisticsPanel()

        self.zoomWidget = ZoomWidget()
        self.colorDialog = ColorDialog(parent=self)

        self.canvas = Canvas()
        self.canvas.zoomRequest.connect(self.zoomRequest)

        scroll = QScrollArea()
        scroll.setWidget(self.canvas)
        scroll.setWidgetResizable(True)
        self.scrollBars = {
            Qt.Vertical: scroll.verticalScrollBar(),
            Qt.Horizontal: scroll.horizontalScrollBar()
        }
        self.canvas.scrollRequest.connect(self.scrollRequest)

        self.canvas.newShape.connect(self.newShape)
        self.canvas.shapeMoved.connect(self.setDirty)
        self.canvas.selectionChanged.connect(self.shapeSelectionChanged)
        self.canvas.drawingPolygon.connect(self.toggleDrawingSensitive)
        self.canvas.status.connect(self.status)

        self.canvas.hideNRect.connect(self.enableCreate)
        self.canvas.hideRRect.connect(self.enableCreateRo)
        # 添加双击放大信号连接
        self.canvas.doubleClickZoom.connect(self.handleDoubleClickZoom)

        self.setCentralWidget(scroll)
        self.addDockWidget(Qt.RightDockWidgetArea, self.dock)
        # Tzutalin 20160906 : Add file list and dock to move faster
        self.addDockWidget(Qt.RightDockWidgetArea, self.filedock)
        # 添加统计面板到右侧dock区域
        self.addDockWidget(Qt.RightDockWidgetArea, self.statsdock)
        
        self.dockFeatures = QDockWidget.DockWidgetClosable | QDockWidget.DockWidgetFloatable
        # 修改：使用正确的特性设置，保留toggleViewAction功能
        self.dock.setFeatures(QDockWidget.DockWidgetMovable | QDockWidget.DockWidgetClosable)
        self.filedock.setFeatures(QDockWidget.DockWidgetMovable | QDockWidget.DockWidgetClosable)
        self.statsdock.setFeatures(QDockWidget.DockWidgetMovable | QDockWidget.DockWidgetClosable)

        # Actions
        action = partial(newAction, self)
        quit = action('&Quit', self.close,
                      'Ctrl+Q', 'quit', u'Quit application')

        open = action('&Open', self.openFile,
                      'Ctrl+O', 'open', u'Open image or label file')

        opendir = action('&Open Dir', self.openDir,
                         'Ctrl+u', 'open', u'Open Dir')

        changeSavedir = action('&Change default saved Annotation dir', self.changeSavedir,
                               'Ctrl+r', 'open', u'Change default saved Annotation dir')

        openAnnotation = action('&Open Annotation', self.openAnnotation,
                                'Ctrl+Shift+O', 'openAnnotation', u'Open Annotation')

        openNextImg = action('&Next Image', self.openNextImg,
                             'd', 'next', u'Open Next')

        openPrevImg = action('&Prev Image', self.openPrevImg,
                             'a', 'prev', u'Open Prev')

        verify = action('&Verify Image', self.verifyImg,
                        'space', 'verify', u'Verify Image')

        save = action('&Save', self.saveFile,
                      'Ctrl+S', 'save', u'Save labels to file', enabled=False)
        saveAs = action('&Save As', self.saveFileAs,
                        'Ctrl+Shift+S', 'save-as', u'Save labels to a different file',
                        enabled=False)
        close = action('&Close', self.closeFile,
                       'Ctrl+E', 'close', u'Close current file')
        color1 = action('Box &Line Color', self.chooseColor1,
                        'Ctrl+L', 'color_line', u'Choose Box line color')
        color2 = action('Box &Fill Color', self.chooseColor2,
                        'Ctrl+Shift+L', 'color', u'Choose Box fill color')

        createMode = action('Create\nRectBox', self.setCreateMode,
                            'Ctrl+N', 'new', u'Start drawing Boxs', enabled=False)
        editMode = action('&Edit\nRectBox', self.setEditMode,
                          'Ctrl+J', 'edit', u'Move and edit Boxs', enabled=False)

        create = action('Create\nRectBox', self.createShape,
                        'e', 'new', u'Draw a new Box', enabled=False)

        createRo = action('Create\nRotatedRBox', self.createRoShape,
                        'w', 'newRo', u'Draw a new RotatedRBox', enabled=False)

        # delete = action('Delete\nRectBox', self.deleteSelectedShape,
        #                 'Delete', 'delete', u'Delete', enabled=False)
        delete = action('Delete\nRectBox', self.deleteSelectedShape, 'Delete', 'delete', u'Delete', enabled=False)
        delete.setShortcuts(["Delete", "F"])
        copy = action('&Duplicate\nRectBox', self.copySelectedShape,
                      'Ctrl+D', 'copy', u'Create a duplicate of the selected Box',
                      enabled=False)

        advancedMode = action('&Advanced Mode', self.toggleAdvancedMode,
                              'Ctrl+Shift+P', 'expert', u'Switch to advanced mode',
                              checkable=True)

        hideAll = action('&Hide\nRectBox', partial(self.togglePolygons, False),
                         'Ctrl+H', 'hide', u'Hide all Boxs',
                         enabled=False)
        showAll = action('&Show\nRectBox', partial(self.togglePolygons, True),
                         'Ctrl+A', 'hide', u'Show all Boxs',
                         enabled=False)

        help = action('&Tutorial', self.tutorial, 'Ctrl+T', 'help',
                      u'Show demos')

        copyToNext = action('复制框到下一帧', self.copyShapesToNextImage,
                    'Ctrl+C', 'copy', u'将当前帧的所有标注框复制到下一帧',
                    enabled=True)
                    
        copyToNextAndSave = action('复制框到下一帧并保存', self.copySelectedShapesToNextImageAndSave,
                    'Ctrl+V', 'copy', u'将当前帧的标注框复制到下一帧并自动保存',
                    enabled=True)

        # 添加半自动标注功能
        autoAnnotate = action('AI半自动标注', self.showAutoAnnotateDialog,
                             'Ctrl+I', 'ai', u'使用AI模型进行半自动标注',
                             enabled=True)

        zoom = QWidgetAction(self)
        zoom.setDefaultWidget(self.zoomWidget)
        self.zoomWidget.setWhatsThis(
            u"Zoom in or out of the image. Also accessible with"
            " %s and %s from the canvas." % (fmtShortcut("Ctrl+[-+]"),
                                             fmtShortcut("Ctrl+Wheel")))
        self.zoomWidget.setEnabled(False)

        zoomIn = action('Zoom &In', partial(self.addZoom, 10),
                        'Ctrl++', 'zoom-in', u'Increase zoom level', enabled=False)
        zoomOut = action('&Zoom Out', partial(self.addZoom, -10),
                         'Ctrl+-', 'zoom-out', u'Decrease zoom level', enabled=False)
        zoomOrg = action('&Original size', partial(self.setZoom, 100),
                         'Ctrl+=', 'zoom', u'Zoom to original size', enabled=False)
        fitWindow = action('&Fit Window', self.setFitWindow,
                           'Ctrl+F', 'fit-window', u'Zoom follows window size',
                           checkable=True, enabled=False)
        fitWidth = action('Fit &Width', self.setFitWidth,
                          'Ctrl+Shift+F', 'fit-width', u'Zoom follows window width',
                          checkable=True, enabled=False)
        # Group zoom controls into a list for easier toggling.
        zoomActions = (self.zoomWidget, zoomIn, zoomOut,
                       zoomOrg, fitWindow, fitWidth)
        self.zoomMode = self.MANUAL_ZOOM
        self.scalers = {
            self.FIT_WINDOW: self.scaleFitWindow,
            self.FIT_WIDTH: self.scaleFitWidth,
            # Set to one to scale to 100% when loading files.
            self.MANUAL_ZOOM: lambda: 1,
        }

        edit = action('&Edit Label', self.editLabel,
                      'Ctrl+W', 'edit', u'Modify the label of the selected Box',
                      enabled=False)
        self.editButton.setDefaultAction(edit)

        shapeLineColor = action('Shape &Line Color', self.chshapeLineColor,
                                icon='color_line', tip=u'Change the line color for this specific shape',
                                enabled=False)
        shapeFillColor = action('Shape &Fill Color', self.chshapeFillColor,
                                icon='color', tip=u'Change the fill color for this specific shape',
                                enabled=False)

        labels = self.dock.toggleViewAction()
        labels.setText('Show/Hide Label Panel')
        labels.setShortcut('Ctrl+P')

        # Lavel list context menu.
        labelMenu = QMenu()
        addActions(labelMenu, (edit, delete))
        self.labelList.setContextMenuPolicy(Qt.CustomContextMenu)
        self.labelList.customContextMenuRequested.connect(
            self.popLabelListMenu)

        # Store actions for further handling.
        self.actions = struct(save=save, saveAs=saveAs, open=open, close=close,
                              lineColor=color1, fillColor=color2,
                              create=create, createRo=createRo, delete=delete, edit=edit, copy=copy,
                              createMode=createMode, editMode=editMode, advancedMode=advancedMode,
                              autoAnnotate=autoAnnotate, openNextImg=openNextImg, openPrevImg=openPrevImg,
                              shapeLineColor=shapeLineColor, shapeFillColor=shapeFillColor,
                              zoom=zoom, zoomIn=zoomIn, zoomOut=zoomOut, zoomOrg=zoomOrg,
                              fitWindow=fitWindow, fitWidth=fitWidth,
                              zoomActions=zoomActions,
                              copyToNext=copyToNext, copyToNextAndSave=copyToNextAndSave,
                              fileMenuActions=(
                                  open, opendir, save, saveAs, close, quit),
                              beginner=(), advanced=(),
                              editMenu=(edit, copy, delete,
                                        None, color1, color2),
                              beginnerContext=(create, edit, copy, delete),
                              advancedContext=(createMode, editMode, edit, copy,
                                               delete, shapeLineColor, shapeFillColor),
                              onLoadActive=(
                                  close, create, createMode, editMode),
                              onShapesPresent=(saveAs, hideAll, showAll))

        self.menus = struct(
            file=self.menu('&File'),
            edit=self.menu('&Edit'),
            view=self.menu('&View'),
            help=self.menu('&Help'),
            recentFiles=QMenu('Open &Recent'),
            labelList=labelMenu)

        addActions(self.menus.file,
                   (open, opendir, changeSavedir, openAnnotation, self.menus.recentFiles, save, saveAs, close, None, quit))
        addActions(self.menus.help, (help,))
        addActions(self.menus.view, (
            labels, advancedMode, None,
            hideAll, showAll, None,
            zoomIn, zoomOut, zoomOrg, None,
            fitWindow, fitWidth))

        self.menus.file.aboutToShow.connect(self.updateFileMenu)

        # Custom context menu for the canvas widget:
        addActions(self.canvas.menus[0], self.actions.beginnerContext)
        addActions(self.canvas.menus[1], (
            action('&Copy here', self.copyShape),
            action('&Move here', self.moveShape)))

        self.tools = self.toolbar('Tools')
        self.actions.beginner = (
            open, opendir, openNextImg, openPrevImg, verify, save, None, create, createRo, copy, delete, None,
            zoomIn, zoom, zoomOut, fitWindow, fitWidth, copyToNext, copyToNextAndSave)

        self.actions.advanced = (
            open, opendir, openNextImg, openPrevImg, save, None,  # 添加图片切换功能
            create, createRo, copy, delete, None,                # 基本标注功能
            createMode, editMode, None,                          # 高级编辑模式
            autoAnnotate, None,                                  # AI半自动标注功能
            hideAll, showAll, None,                              # 显示控制
            zoomIn, zoom, zoomOut, fitWindow, fitWidth, None,    # 缩放控制
            copyToNext, copyToNextAndSave)                       # 批量操作

        self.statusBar().showMessage('%s started.' % __appname__)
        self.statusBar().show()

        # 创建状态栏右侧容器
        statusRightWidget = QWidget()
        statusRightLayout = QHBoxLayout(statusRightWidget)
        statusRightLayout.setContentsMargins(5, 2, 5, 2)
        statusRightLayout.setSpacing(10)
        
        # 添加进度显示标签到状态栏
        self.progressLabel = QLabel()
        self.progressLabel.setAlignment(Qt.AlignCenter)
        self.progressLabel.setStyleSheet("""
            QLabel {
                color: #2E8B57;
                font-weight: bold;
                font-size: 11px;
                padding: 4px 8px;
                background-color: rgba(46, 139, 87, 0.1);
                border-radius: 8px;
                border: 1px solid rgba(46, 139, 87, 0.3);
            }
        """)
        
        # 添加分隔符
        separator = QLabel("|")
        separator.setStyleSheet("color: #CCCCCC; font-weight: bold;")
        
        # 将组件添加到布局
        statusRightLayout.addWidget(self.progressLabel)
        statusRightLayout.addWidget(separator)
        statusRightLayout.addWidget(self.modeLabel)
        
        # 将右侧容器添加到状态栏
        self.statusBar().addPermanentWidget(statusRightWidget)

        # Application state.
        self.image = QImage()
        self.filePath = ustr(defaultFilename)
        self.recentFiles = []
        self.maxRecent = 7
        self.lineColor = None
        self.fillColor = None
        self.zoom_level = 100
        self.fit_window = False
        # Add Chris
        self.difficult = False

        # Load predefined classes to the list
        self.loadPredefinedClasses(defaultPrefdefClassFile)
        # XXX: Could be completely declarative.
        # Restore application settings.
        if have_qstring():
            types = {
                'filename': QString,
                'recentFiles': QStringList,
                'window/size': QSize,
                'window/position': QPoint,
                'window/geometry': QByteArray,
                'line/color': QColor,
                'fill/color': QColor,
                'advanced': bool,
                # Docks and toolbars:
                'window/state': QByteArray,
                'savedir': QString,
                'lastOpenDir': QString,
            }
        else:
            types = {
                'filename': str,
                'recentFiles': list,
                'window/size': QSize,
                'window/position': QPoint,
                'window/geometry': QByteArray,
                'line/color': QColor,
                'fill/color': QColor,
                'advanced': bool,
                # Docks and toolbars:
                'window/state': QByteArray,
                'savedir': str,
                'lastOpenDir': str,
            }

        self.settings = settings = Settings(types)
        self.recentFiles = list(settings.get('recentFiles', []))
        size = settings.get('window/size', QSize(600, 500))
        position = settings.get('window/position', QPoint(0, 0))
        self.resize(size)
        self.move(position)
        saveDir = ustr(settings.get('savedir', None))
        self.lastOpenDir = ustr(settings.get('lastOpenDir', None))
        if saveDir is not None and os.path.exists(saveDir):
            self.defaultSaveDir = saveDir
            self.statusBar().showMessage('%s started. Annotation will be saved to %s' %
                                         (__appname__, self.defaultSaveDir))
            self.statusBar().show()

        # or simply:
        # self.restoreGeometry(settings['window/geometry']
        self.restoreState(settings.get('window/state', QByteArray()))
        self.lineColor = QColor(settings.get('line/color', Shape.line_color))
        self.fillColor = QColor(settings.get('fill/color', Shape.fill_color))
        Shape.line_color = self.lineColor
        Shape.fill_color = self.fillColor
        # Add chris
        Shape.difficult = self.difficult

        def xbool(x):
            if isinstance(x, QVariant):
                return x.toBool()
            return bool(x)

        if xbool(settings.get('advanced', False)):
            self.actions.advancedMode.setChecked(True)
            self.toggleAdvancedMode()

        # Populate the File menu dynamically.
        self.updateFileMenu()
        # Since loading the file may take some time, make sure it runs in the
        # background.
        self.queueEvent(partial(self.loadFile, self.filePath or ""))

        # Callbacks:
        self.zoomWidget.valueChanged.connect(self.paintCanvas)

        # 初始化模式显示
        self.updateModeDisplay()

        self.populateModeActions()

    ## Support Functions ##

    def noShapes(self):
        return not self.itemsToShapes

    def toggleAdvancedMode(self, value=True):
        self._beginner = not value
        self.canvas.setEditing(True)  # 保持编辑功能启用
        self.populateModeActions()
        self.editButton.setVisible(not value)  # 高级模式隐藏编辑按钮

        self.updateModeDisplay()

        if value:
            status_msg = "已切换到高级模式 - 更多专业功能已启用"
            # 启用高级功能
            self.enableAdvancedFeatures()
        else:
            status_msg = "已切换到初学者模式 - 简化界面更易上手"
            # 禁用高级功能
            self.disableAdvancedFeatures()

        # 添加切换动画效果
        self.animateModeSwitch()

        self.status(status_msg)

    def enableAdvancedFeatures(self):
        """启用高级模式专有功能"""
        # 启用批量选择
        self.labelList.setSelectionMode(QAbstractItemView.ExtendedSelection)
        # 启用精确编辑模式
        if hasattr(self, 'precisionPanel'):
            self.precisionPanel.setVisible(True)

    def animateModeSwitch(self):
        """为模式切换添加平滑动画效果"""
        try:
            from PyQt5.QtCore import QPropertyAnimation, QEasingCurve
            from PyQt5.QtCore import pyqtProperty
            
            # 创建透明度动画
            self.modeAnimation = QPropertyAnimation(self.modeLabel, b"windowOpacity")
            self.modeAnimation.setDuration(300)
            self.modeAnimation.setStartValue(0.3)
            self.modeAnimation.setEndValue(1.0)
            self.modeAnimation.setEasingCurve(QEasingCurve.OutCubic)
            self.modeAnimation.start()
            
        except ImportError:
            # 如果动画库不可用，跳过动画
            pass
        
    def disableAdvancedFeatures(self):
        """禁用高级模式专有功能"""
        # 禁用批量选择，回到单选模式
        self.labelList.setSelectionMode(QAbstractItemView.SingleSelection)
        # 隐藏精确编辑面板
        if hasattr(self, 'precisionPanel'):
            self.precisionPanel.setVisible(False)

    def updateModeDisplay(self):
        """更新模式显示，支持主题切换"""
        if self.beginner():
            self.modeLabel.setText("🌱 初学者模式")
            self.modeLabel.setStyleSheet(self.beginnerModeStyle)
            # 更新工具栏主题色
            self.tools.setStyleSheet("""
                QToolBar {
                    border-bottom: 3px solid #4CAF50;
                }
            """)
        else:
            self.modeLabel.setText("🚀 高级模式")
            self.modeLabel.setStyleSheet(self.advancedModeStyle)
            # 更新工具栏主题色
            self.tools.setStyleSheet("""
                QToolBar {
                    border-bottom: 3px solid #FF6B35;
                }
            """)

    def populateModeActions(self):
        if self.beginner():
            tool, menu = self.actions.beginner, self.actions.beginnerContext
        else:
            tool, menu = self.actions.advanced, self.actions.advancedContext
        self.tools.clear()
        addActions(self.tools, tool)
        self.canvas.menus[0].clear()
        addActions(self.canvas.menus[0], menu)
        self.menus.edit.clear()
        actions = (self.actions.create,) if self.beginner()\
            else (self.actions.createMode, self.actions.editMode)
        addActions(self.menus.edit, actions + self.actions.editMenu + (self.actions.copyToNext, self.actions.copyToNextAndSave,))

    def setBeginner(self):
        self.tools.clear()
        addActions(self.tools, self.actions.beginner)

    def setAdvanced(self):
        self.tools.clear()
        addActions(self.tools, self.actions.advanced)

    def setDirty(self):
        self.dirty = True
        self.canvas.verified = False
        self.actions.save.setEnabled(True)

    def setClean(self):
        self.dirty = False
        self.actions.save.setEnabled(False)
        self.actions.create.setEnabled(True)
        self.actions.createRo.setEnabled(True)

    def enableCreate(self,b):
        self.isEnableCreate = not b
        self.actions.create.setEnabled(self.isEnableCreate)

    def enableCreateRo(self,b):
        self.isEnableCreateRo = not b
        self.actions.createRo.setEnabled(self.isEnableCreateRo)

    def createStatisticsPanel(self):
        """创建统计面板"""
        # 创建统计面板的主容器
        statsWidget = QWidget()
        statsLayout = QVBoxLayout()
        statsLayout.setContentsMargins(5, 5, 5, 5)
        statsLayout.setSpacing(10)
        
        # 当前图像统计区域
        currentImageGroup = QGroupBox("当前图像统计")
        currentImageLayout = QVBoxLayout()
        
        # 标注框总数
        self.totalBoxesLabel = QLabel("标注框总数: 0")
        self.totalBoxesLabel.setStyleSheet("font-weight: bold; color: #2E86AB;")
        currentImageLayout.addWidget(self.totalBoxesLabel)
        
        # 旋转框数量
        self.rotatedBoxesLabel = QLabel("旋转框: 0")
        self.rotatedBoxesLabel.setStyleSheet("color: #A23B72;")
        currentImageLayout.addWidget(self.rotatedBoxesLabel)
        
        # 普通框数量
        self.normalBoxesLabel = QLabel("普通框: 0")
        self.normalBoxesLabel.setStyleSheet("color: #F18F01;")
        currentImageLayout.addWidget(self.normalBoxesLabel)
        
        # 困难样本数量
        self.difficultBoxesLabel = QLabel("困难样本: 0")
        self.difficultBoxesLabel.setStyleSheet("color: #C73E1D;")
        currentImageLayout.addWidget(self.difficultBoxesLabel)
        
        currentImageGroup.setLayout(currentImageLayout)
        statsLayout.addWidget(currentImageGroup)
        
        # 标签分类统计区域
        labelStatsGroup = QGroupBox("标签分类统计")
        labelStatsLayout = QVBoxLayout()
        
        # 创建标签统计的滚动区域
        self.labelStatsScrollArea = QScrollArea()
        self.labelStatsWidget = QWidget()
        self.labelStatsLayout = QVBoxLayout()
        self.labelStatsWidget.setLayout(self.labelStatsLayout)
        self.labelStatsScrollArea.setWidget(self.labelStatsWidget)
        self.labelStatsScrollArea.setWidgetResizable(True)
        self.labelStatsScrollArea.setMaximumHeight(150)
        
        labelStatsLayout.addWidget(self.labelStatsScrollArea)
        labelStatsGroup.setLayout(labelStatsLayout)
        statsLayout.addWidget(labelStatsGroup)
        
        # 项目整体统计区域
        projectStatsGroup = QGroupBox("项目整体统计")
        projectStatsLayout = QVBoxLayout()
        
        # 总图像数
        self.totalImagesLabel = QLabel("总图像数: 0")
        self.totalImagesLabel.setStyleSheet("font-weight: bold;")
        projectStatsLayout.addWidget(self.totalImagesLabel)
        
        # 已标注图像数
        self.annotatedImagesLabel = QLabel("已标注: 0")
        self.annotatedImagesLabel.setStyleSheet("color: #28A745;")
        projectStatsLayout.addWidget(self.annotatedImagesLabel)
        
        # 标注进度
        self.progressPercentLabel = QLabel("进度: 0.0%")
        self.progressPercentLabel.setStyleSheet("color: #007BFF;")
        projectStatsLayout.addWidget(self.progressPercentLabel)
        
        # 进度条
        self.progressBar = QProgressBar()
        self.progressBar.setRange(0, 100)
        self.progressBar.setValue(0)
        self.progressBar.setStyleSheet("""
            QProgressBar {
                border: 2px solid grey;
                border-radius: 5px;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: #28A745;
                border-radius: 3px;
            }
        """)
        projectStatsLayout.addWidget(self.progressBar)
        
        projectStatsGroup.setLayout(projectStatsLayout)
        statsLayout.addWidget(projectStatsGroup)
        
        # 添加弹性空间
        statsLayout.addStretch()
        
        # 刷新按钮
        refreshButton = QPushButton("刷新统计")
        refreshButton.setStyleSheet("""
            QPushButton {
                background-color: #007BFF;
                color: white;
                border: none;
                padding: 8px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #0056B3;
            }
            QPushButton:pressed {
                background-color: #004085;
            }
        """)
        refreshButton.clicked.connect(self.updateStatistics)
        statsLayout.addWidget(refreshButton)
        
        statsWidget.setLayout(statsLayout)
        
        # 创建dock widget
        self.statsdock = QDockWidget(u'统计面板', self)
        self.statsdock.setObjectName(u'Statistics')
        self.statsdock.setWidget(statsWidget)
        
        # 初始化统计数据
        self.updateStatistics()

    def updateStatistics(self):
        """更新统计数据"""
        if not hasattr(self, 'statsdock'):
            return
            
        # 当前图像统计
        if hasattr(self, 'canvas') and self.canvas.shapes:
            shapes = self.canvas.shapes
            total_boxes = len(shapes)
            rotated_boxes = sum(1 for shape in shapes if hasattr(shape, 'isRotated') and shape.isRotated)
            normal_boxes = total_boxes - rotated_boxes
            difficult_boxes = sum(1 for shape in shapes if hasattr(shape, 'difficult') and shape.difficult)
            
            self.totalBoxesLabel.setText(f"标注框总数: {total_boxes}")
            self.rotatedBoxesLabel.setText(f"旋转框: {rotated_boxes}")
            self.normalBoxesLabel.setText(f"普通框: {normal_boxes}")
            self.difficultBoxesLabel.setText(f"困难样本: {difficult_boxes}")
            
            # 更新标签分类统计
            self.updateLabelStatistics(shapes)
        else:
            self.totalBoxesLabel.setText("标注框总数: 0")
            self.rotatedBoxesLabel.setText("旋转框: 0")
            self.normalBoxesLabel.setText("普通框: 0")
            self.difficultBoxesLabel.setText("困难样本: 0")
            self.clearLabelStatistics()
        
        # 项目整体统计
        self.updateProjectStatistics()
        
        # 添加重叠检测
        self.updateOverlapWarning()

    def updateLabelStatistics(self, shapes):
        """更新标签分类统计"""
        # 清除现有的标签统计
        self.clearLabelStatistics()
        
        # 统计各标签的数量
        label_counts = {}
        for shape in shapes:
            label = shape.label if hasattr(shape, 'label') and shape.label else "未命名"
            label_counts[label] = label_counts.get(label, 0) + 1
        
        # 显示标签统计
        for label, count in sorted(label_counts.items()):
            label_item = QLabel(f"{label}: {count}")
            label_item.setStyleSheet("padding: 2px; border-bottom: 1px solid #E0E0E0;")
            self.labelStatsLayout.addWidget(label_item)

    def clearLabelStatistics(self):
        """清除标签统计显示"""
        while self.labelStatsLayout.count():
            child = self.labelStatsLayout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

    def updateProjectStatistics(self):
        """更新项目整体统计"""
        if hasattr(self, 'mImgList') and self.mImgList:
            total_images = len(self.mImgList)
            annotated_count = 0
            
            # 计算已标注的图像数量
            for img_path in self.mImgList:
                img_dir = os.path.dirname(img_path)
                img_name = os.path.basename(img_path)
                xml_name = os.path.splitext(img_name)[0] + XML_EXT
                
                if self.defaultSaveDir:
                    xml_path = os.path.join(self.defaultSaveDir, xml_name)
                else:
                    xml_path = os.path.join(img_dir, xml_name)
                    
                if os.path.exists(xml_path):
                    annotated_count += 1
            
            # 计算进度百分比
            progress_percent = (annotated_count / total_images * 100) if total_images > 0 else 0
            
            # 更新显示
            self.totalImagesLabel.setText(f"总图像数: {total_images}")
            self.annotatedImagesLabel.setText(f"已标注: {annotated_count}")
            self.progressPercentLabel.setText(f"进度: {progress_percent:.1f}%")
            self.progressBar.setValue(int(progress_percent))
        else:
            self.totalImagesLabel.setText("总图像数: 0")
            self.annotatedImagesLabel.setText("已标注: 0")
            self.progressPercentLabel.setText("进度: 0.0%")
            self.progressBar.setValue(0)

    def toggleActions(self, value=True):
        """Enable/Disable widgets which depend on an opened image."""
        for z in self.actions.zoomActions:
            z.setEnabled(value)
        for action in self.actions.onLoadActive:
            action.setEnabled(value)

    def queueEvent(self, function):
        QTimer.singleShot(0, function)

    def status(self, message, delay=5000):
        # print(message)
        self.statusBar().showMessage(message, delay)
        self.statusBar().show()

    def resetState(self):
        self.itemsToShapes.clear()
        self.shapesToItems.clear()
        self.labelList.clear()
        self.filePath = None
        self.imageData = None
        self.labelFile = None
        self.canvas.resetState()

    def currentItem(self):
        items = self.labelList.selectedItems()
        if items:
            return items[0]
        return None

    def addRecentFile(self, filePath):
        if filePath in self.recentFiles:
            self.recentFiles.remove(filePath)
        elif len(self.recentFiles) >= self.maxRecent:
            self.recentFiles.pop()
        self.recentFiles.insert(0, filePath)

    def beginner(self):
        return self._beginner

    def advanced(self):
        return not self.beginner()

    ## Callbacks ##
    def tutorial(self):
        # 获取当前脚本所在目录
        current_dir = os.path.dirname(os.path.abspath(__file__))
        # 构建使用说明文档的路径
        doc_path = os.path.join(current_dir, 'roLabelImg使用说明.md')
        
        # 检查文件是否存在
        if os.path.exists(doc_path):
            try:
                # 在Windows系统上使用默认程序打开markdown文件
                if sys.platform.startswith('win'):
                    os.startfile(doc_path)
                # 在macOS系统上使用默认程序打开
                elif sys.platform.startswith('darwin'):
                    subprocess.Popen(['open', doc_path])
                # 在Linux系统上使用默认程序打开
                else:
                    subprocess.Popen(['xdg-open', doc_path])
                    
                self.status("已打开使用说明文档")
            except Exception as e:
                self.status(f"无法打开使用说明文档: {str(e)}")
                # 显示内置帮助对话框而不是启动外部程序
                self.showBuiltinHelp()
        else:
            self.status("使用说明文档不存在")
            # 显示内置帮助对话框而不是启动外部程序
            self.showBuiltinHelp()

    def showBuiltinHelp(self):
        """显示内置帮助对话框"""
        help_text = """
# roLabelImg 使用帮助

## 基本操作
- W: 创建旋转矩形
- Ctrl+U: 创建普通矩形
- D: 下一张图片
- A: 上一张图片
- Del: 删除选中的标注框
- Ctrl+S: 保存
- Ctrl+Shift+A: 切换高级/初学者模式

## 标注操作
- 左键点击: 选择标注框
- 右键拖动: 移动图片
- 鼠标滚轮: 缩放图片
- 双击: 放大到鼠标位置

## 旋转矩形操作
- Z/X: 顺时针微调旋转
- C/V: 逆时针微调旋转
- 右键拖动顶点: 旋转矩形

更多详细信息请查看项目目录下的使用说明文档。
        """
        
        msg = QMessageBox(self)
        msg.setWindowTitle("使用帮助")
        msg.setText(help_text)
        msg.setTextFormat(Qt.PlainText)
        msg.setStandardButtons(QMessageBox.Ok)
        msg.exec_()

    # create Normal Rect
    def createShape(self):
        # assert self.beginner()  # 移除这行断言
        self.canvas.setEditing(False)
        self.actions.create.setEnabled(False)
        self.actions.createRo.setEnabled(True)
        self.canvas.fourpoint = False

    # create Rotated Rect
    def createRoShape(self):
        # assert self.beginner()  # 移除这行断言
        self.canvas.setEditing(False)
        self.actions.create.setEnabled(True)
        self.actions.createRo.setEnabled(False)
        self.canvas.fourpoint = True

    def toggleDrawingSensitive(self, drawing=True):
        """In the middle of drawing, toggling between modes should be disabled."""
        self.actions.editMode.setEnabled(not drawing)
        if not drawing and self.beginner():
            # Cancel creation.
            print('Cancel creation.')
            self.canvas.setEditing(True)
            self.canvas.restoreCursor()
            self.actions.create.setEnabled(True)
            self.actions.createRo.setEnabled(True)
            

    def toggleDrawMode(self, edit=True):
        self.canvas.setEditing(edit)
        self.actions.createMode.setEnabled(edit)
        self.actions.editMode.setEnabled(not edit)

    def setCreateMode(self):
        print('setCreateMode')
        assert self.advanced()
        self.toggleDrawMode(False)

    def setEditMode(self):
        assert self.advanced()
        self.toggleDrawMode(True)

    def updateFileMenu(self):
        currFilePath = self.filePath

        def exists(filename):
            return os.path.exists(filename)
        menu = self.menus.recentFiles
        menu.clear()
        files = [f for f in self.recentFiles if f !=
                 currFilePath and exists(f)]
        for i, f in enumerate(files):
            icon = newIcon('labels')
            action = QAction(
                icon, '&%d %s' % (i + 1, QFileInfo(f).fileName()), self)
            action.triggered.connect(partial(self.loadRecent, f))
            menu.addAction(action)

    def popLabelListMenu(self, point):
        self.menus.labelList.exec_(self.labelList.mapToGlobal(point))

    def editLabel(self, item=None):
        # 移除编辑模式检查，允许在任何模式下编辑标签
        # if not self.canvas.editing():
        #     return
        item = item if item else self.currentItem()
        # 添加空值检查，防止崩溃
        if item is None:
            return
        text = self.labelDialog.popUp(item.text())
        if text is not None:
            item.setText(text)
            self.setDirty()

    # Tzutalin 20160906 : Add file list and dock to move faster
    def fileitemDoubleClicked(self, item=None):
        if item is None:
            return
        
        # 获取当前项在文件列表中的索引
        currIndex = self.fileListWidget.row(item)
        if 0 <= currIndex < len(self.mImgList):
            filename = self.mImgList[currIndex]
            if filename:
                self.loadFile(filename)

    # Add chris
    def btnstate(self, item= None):
        """ Function to handle difficult examples
         date on each object """
        if not self.canvas.editing():
            return

        item = self.currentItem()
        if not item: # If not selected Item, take the first one
            item = self.labelList.item(self.labelList.count()-1)

        difficult = self.diffcButton.isChecked()

        try:
            shape = self.itemsToShapes[item]
        except:
            pass
        # Checked and Update
        try:
            if difficult != shape.difficult:
                shape.difficult = difficult
                self.setDirty()
            else:  # User probably changed item visibility
                self.canvas.setShapeVisible(shape, item.checkState() == Qt.Checked)
        except:
            pass

    # React to canvas signals.
    def shapeSelectionChanged(self, selected=False):
        if self._noSelectionSlot:
            self._noSelectionSlot = False
        else:
            shape = self.canvas.selectedShape
            if shape:
                self.shapesToItems[shape].setSelected(True)
            else:
                self.labelList.clearSelection()
        self.actions.delete.setEnabled(selected)
        self.actions.copy.setEnabled(selected)
        # 修改edit action的启用逻辑：当有选中的shape或labelList中有选中项时启用
        has_label_selection = len(self.labelList.selectedItems()) > 0
        self.actions.edit.setEnabled(selected or has_label_selection)
        self.actions.shapeLineColor.setEnabled(selected)
        self.actions.shapeFillColor.setEnabled(selected)

    def addLabel(self, shape):
        shape.paintLabel = True
        item = HashableQListWidgetItem(shape.label)
        item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
        item.setCheckState(Qt.Checked)
        # 为形状设置基于标签的颜色
        shape.line_color = self.getLabelColor(shape.label)
        shape.fill_color = QColor(shape.line_color.red(), shape.line_color.green(), shape.line_color.blue(), 128)
        self.itemsToShapes[item] = shape
        self.shapesToItems[shape] = item
        self.labelList.addItem(item)
        for action in self.actions.onShapesPresent:
            action.setEnabled(True)
        self.updateStatistics()
        self.updateOverlapWarning()

    def remLabel(self, shape):
        if shape is None:
            # print('rm empty label')
            return
        item = self.shapesToItems[shape]
        self.labelList.takeItem(self.labelList.row(item))
        del self.shapesToItems[shape]
        del self.itemsToShapes[item]
        self.updateStatistics()
        self.updateOverlapWarning()

    def loadLabels(self, shapes):
        s = []
        for label, points, direction, isRotated, line_color, fill_color, difficult in shapes:
            shape = Shape(label=label)
            for x, y in points:
                shape.addPoint(QPointF(x, y))
            shape.difficult = difficult
            shape.direction = direction
            shape.isRotated = isRotated
            shape.close()
            
            # 如果没有指定颜色，则根据标签生成颜色
            if not line_color:
                shape.line_color = self.getLabelColor(label)
                shape.fill_color = QColor(shape.line_color.red(), shape.line_color.green(), shape.line_color.blue(), 128)
            else:
                shape.line_color = QColor(*line_color)
                shape.fill_color = QColor(*fill_color) if fill_color else QColor(shape.line_color.red(), shape.line_color.green(), shape.line_color.blue(), 128)
                
            s.append(shape)
            self.addLabel(shape)

        self.canvas.loadShapes(s)
        self.updateStatistics()
        self.updateOverlapWarning()

    def saveLabels(self, annotationFilePath):
        annotationFilePath = ustr(annotationFilePath)
        if self.labelFile is None:
            self.labelFile = LabelFile()
            self.labelFile.verified = self.canvas.verified

        def format_shape(s):
            return dict(label=s.label,
                        line_color=s.line_color.getRgb()
                        if s.line_color != self.lineColor else None,
                        fill_color=s.fill_color.getRgb()
                        if s.fill_color != self.fillColor else None,
                        points=[(p.x(), p.y()) for p in s.points],
                       # add chris
                        difficult = s.difficult,
                        # You Hao 2017/06/21
                        # add for rotated bounding box
                        direction = s.direction,
                        center = s.center,
                        isRotated = s.isRotated)

        shapes = [format_shape(shape) for shape in self.canvas.shapes]
        # Can add differrent annotation formats here
        try:
            if self.usingPascalVocFormat is True:
                print ('Img: ' + self.filePath + ' -> Its xml: ' + annotationFilePath)
                self.labelFile.savePascalVocFormat(annotationFilePath, shapes, self.filePath, self.imageData,
                                                   self.lineColor.getRgb(), self.fillColor.getRgb())
            else:
                self.labelFile.save(annotationFilePath, shapes, self.filePath, self.imageData,
                                    self.lineColor.getRgb(), self.fillColor.getRgb())
            return True
        except LabelFileError as e:
            self.errorMessage(u'Error saving label data',
                              u'<b>%s</b>' % e)
            return False

    def copySelectedShape(self):
        shape = self.canvas.copySelectedShape()
        self.addLabel(shape)
        # fix copy and delete
        self.shapeSelectionChanged(True)
        # 添加自动保存功能
        self.setDirty()
        self.saveFile()

    def labelSelectionChanged(self):
        items = self.labelList.selectedItems()
        if items:
            item = items[0]
            shape = self.itemsToShapes[item]
            # Callback functions:
            if not self._noSelectionSlot:
                self._noSelectionSlot = True  # 设置标志防止递归
                self.canvas.selectShape(shape)
                self.selectionChanged.emit(True)
                self._noSelectionSlot = False  # 重置标志
            # 更新edit action的启用状态
            has_shape_selection = self.canvas.selectedShape is not None
            has_label_selection = len(items) > 0
            self.actions.edit.setEnabled(has_shape_selection or has_label_selection)
        else:
            # 当没有选中任何标签时，检查是否有选中的shape
            has_shape_selection = self.canvas.selectedShape is not None
            self.actions.edit.setEnabled(has_shape_selection)

    def labelItemChanged(self, item):
        shape = self.itemsToShapes[item]
        label = item.text()
        if label != shape.label:
            shape.label = item.text()
            self.setDirty()
        else:  # User probably changed item visibility
            self.canvas.setShapeVisible(shape, item.checkState() == Qt.Checked)

    # Callback functions:
    def newShape(self):
        """Pop-up and give focus to the label editor.

        position MUST be in global coordinates.
        """
        if not self.useDefautLabelCheckbox.isChecked() or not self.defaultLabelTextLine.text():
            if len(self.labelHist) > 0:
                self.labelDialog = LabelDialog(
                    parent=self, listItem=self.labelHist)

            text = self.labelDialog.popUp(text=self.prevLabelText)
        else:
            text = self.defaultLabelTextLine.text()

        # Add Chris
        self.diffcButton.setChecked(False)
        if text is not None:
            self.prevLabelText = text
            self.addLabel(self.canvas.setLastLabel(text))
            if self.beginner():  # Switch to edit mode.
                self.canvas.setEditing(True)
                self.actions.create.setEnabled(self.isEnableCreate)
                self.actions.createRo.setEnabled(self.isEnableCreateRo)
            else:
                self.actions.editMode.setEnabled(True)
            self.setDirty()

            if text not in self.labelHist:
                self.labelHist.append(text)
        else:
            # self.canvas.undoLastLine()
            self.canvas.resetAllLines()

    def scrollRequest(self, delta, orientation):
        # 处理鼠标拖动时的滚动请求
        if isinstance(delta, float):
            # 当delta是浮点数时，表示是从拖动操作传来的像素级别滚动
            bar = self.scrollBars[orientation]
            value = bar.value() - delta
            bar.setValue(value)
        else:
            # 原有的滚轮滚动处理
            units = - delta / (8 * 7.5)
            bar = self.scrollBars[orientation]
            bar.setValue(bar.value() + bar.singleStep() * units)

    def setZoom(self, value):
        self.actions.fitWidth.setChecked(False)
        self.actions.fitWindow.setChecked(False)
        self.zoomMode = self.MANUAL_ZOOM
        self.zoomWidget.setValue(value)

    def addZoom(self, increment=10):
        self.setZoom(self.zoomWidget.value() + increment)

    def zoomRequest(self, delta):
        units = delta / (8 * 15)
        scale = 10
        self.addZoom(scale * units)

    def setFitWindow(self, value=True):
        if value:
            self.actions.fitWidth.setChecked(False)
        self.zoomMode = self.FIT_WINDOW if value else self.MANUAL_ZOOM
        self.adjustScale()

    def setFitWidth(self, value=True):
        if value:
            self.actions.fitWindow.setChecked(False)
        self.zoomMode = self.FIT_WIDTH if value else self.MANUAL_ZOOM
        self.adjustScale()

    def togglePolygons(self, value):
        for item, shape in self.itemsToShapes.items():
            item.setCheckState(Qt.Checked if value else Qt.Unchecked)

    def loadFile(self, filePath=None):
        """Load the specified file, or the last opened file if None."""
        self.resetState()
        self.canvas.setEnabled(False)
        if filePath is None:
            filePath = self.settings.get('filename')

        unicodeFilePath = ustr(filePath)
        # Tzutalin 20160906 : Add file list and dock to move faster
        # Highlight the file item
        if unicodeFilePath and self.fileListWidget.count() > 0:
            index = self.mImgList.index(unicodeFilePath)
            fileWidgetItem = self.fileListWidget.item(index)
            fileWidgetItem.setSelected(True)

        if unicodeFilePath and os.path.exists(unicodeFilePath):
            if LabelFile.isLabelFile(unicodeFilePath):
                try:
                    self.labelFile = LabelFile(unicodeFilePath)
                except LabelFileError as e:
                    self.errorMessage(u'Error opening file',
                                      (u"<p><b>%s</b></p>"
                                       u"<p>Make sure <i>%s</i> is a valid label file.")
                                      % (e, unicodeFilePath))
                    self.status("Error reading %s" % unicodeFilePath)
                    return False
                self.imageData = self.labelFile.imageData
                self.lineColor = QColor(*self.labelFile.lineColor)
                self.fillColor = QColor(*self.labelFile.fillColor)
            else:
                # Load image:
                # read data first and store for saving into label file.
                self.imageData = read(unicodeFilePath, None)
                self.labelFile = None
            image = QImage.fromData(self.imageData)
            if image.isNull():
                self.errorMessage(u'Error opening file',
                                  u"<p>Make sure <i>%s</i> is a valid image file." % unicodeFilePath)
                self.status("Error reading %s" % unicodeFilePath)
                return False
            self.status("Loaded %s" % os.path.basename(unicodeFilePath))
            self.image = image
            self.filePath = unicodeFilePath
            self.canvas.loadPixmap(QPixmap.fromImage(image))
            if self.labelFile:
                self.loadLabels(self.labelFile.shapes)
            self.setClean()
            self.canvas.setEnabled(True)
            self.adjustScale(initial=True)
            self.paintCanvas()
            self.addRecentFile(self.filePath)
            self.toggleActions(True)

            # Label xml file and show bound box according to its filename
            if self.usingPascalVocFormat is True:
                if self.defaultSaveDir is not None:
                    basename = os.path.basename(
                        os.path.splitext(self.filePath)[0]) + XML_EXT
                    xmlPath = os.path.join(self.defaultSaveDir, basename)
                    self.loadPascalXMLByFilename(xmlPath)
                else:
                    xmlPath = filePath.split(".")[0] + XML_EXT
                    if os.path.isfile(xmlPath):
                        self.loadPascalXMLByFilename(xmlPath)

            self.setWindowTitle(__appname__ + ' ' + filePath)

            # Default : select last item if there is at least one item
            if self.labelList.count():
                self.labelList.setCurrentItem(self.labelList.item(self.labelList.count()-1))
                # self.labelList.setItemSelected(self.labelList.item(self.labelList.count()-1), True)

            self.canvas.setFocus(True)
            
            # 加载文件后更新进度显示
            self.updateProgressDisplay()
            self.updateFileListDisplay()
            
            return True
        return False

    def resizeEvent(self, event):
        if self.canvas and not self.image.isNull()\
           and self.zoomMode != self.MANUAL_ZOOM:
            self.adjustScale()
        super(MainWindow, self).resizeEvent(event)

    def paintCanvas(self):
        assert not self.image.isNull(), "cannot paint null image"
        self.canvas.scale = 0.01 * self.zoomWidget.value()
        self.canvas.adjustSize()
        self.canvas.update()

    def adjustScale(self, initial=False):
        value = self.scalers[self.FIT_WINDOW if initial else self.zoomMode]()
        self.zoomWidget.setValue(int(100 * value))

    def scaleFitWindow(self):
        """Figure out the size of the pixmap in order to fit the main widget."""
        e = 2.0  # So that no scrollbars are generated.
        w1 = self.centralWidget().width() - e
        h1 = self.centralWidget().height() - e
        a1 = w1 / h1
        # Calculate a new scale value based on the pixmap's aspect ratio.
        w2 = self.canvas.pixmap.width() - 0.0
        h2 = self.canvas.pixmap.height() - 0.0
        a2 = w2 / h2
        return w1 / w2 if a2 >= a1 else h1 / h2

    def scaleFitWidth(self):
        # The epsilon does not seem to work too well here.
        w = self.centralWidget().width() - 2.0
        return w / self.canvas.pixmap.width()

    def closeEvent(self, event):
        if not self.mayContinue():
            event.ignore()
        s = self.settings
        # If it loads images from dir, don't load it at the begining
        if self.dirname is None:
            s['filename'] = self.filePath if self.filePath else ''
        else:
            s['filename'] = ''

        s['window/size'] = self.size()
        s['window/position'] = self.pos()
        s['window/state'] = self.saveState()
        s['line/color'] = self.lineColor
        s['fill/color'] = self.fillColor
        s['recentFiles'] = self.recentFiles
        s['advanced'] = not self._beginner
        if self.defaultSaveDir is not None and len(self.defaultSaveDir) > 1:
            s['savedir'] = ustr(self.defaultSaveDir)
        else:
            s['savedir'] = ""

        if self.lastOpenDir is not None and len(self.lastOpenDir) > 1:
            s['lastOpenDir'] = self.lastOpenDir
        else:
            s['lastOpenDir'] = ""

    ## User Dialogs ##

    def loadRecent(self, filename):
        if self.mayContinue():
            self.loadFile(filename)

    def scanAllImages(self, folderPath):
        extensions = ['.jpeg', '.jpg', '.png', '.bmp']
        images = []

        for root, dirs, files in os.walk(folderPath):
            for file in files:
                if file.lower().endswith(tuple(extensions)):
                    relativePath = os.path.join(root, file)
                    images.append(relativePath)
        images.sort(key=lambda x: x.lower())
        return images

    def changeSavedir(self, _value=False):
        if self.defaultSaveDir is not None:
            path = ustr(self.defaultSaveDir)
        else:
            path = '.'

        dirpath = ustr(QFileDialog.getExistingDirectory(self,
                                                       '%s - Save to the directory' % __appname__, path,  QFileDialog.ShowDirsOnly
                                                       | QFileDialog.DontResolveSymlinks))

        if dirpath is not None and len(dirpath) > 1:
            self.defaultSaveDir = dirpath

        self.statusBar().showMessage('%s . Annotation will be saved to %s' %
                                     ('Change saved folder', self.defaultSaveDir))
        self.statusBar().show()

    def openAnnotation(self, _value=False):
        if self.filePath is None:
            return

        path = os.path.dirname(ustr(self.filePath))\
            if self.filePath else '.'
        if self.usingPascalVocFormat:
            filters = "Open Annotation XML file (%s)" % \
                      ' '.join(['*.xml'])
            filename = QFileDialog.getOpenFileName(self,'%s - Choose a xml file' % __appname__, path, filters)
            if filename:
                if isinstance(filename, (tuple, list)):
                    filename = filename[0]
            self.loadPascalXMLByFilename(filename)

    def openDir(self, _value=False):
        if not self.mayContinue():
            return

        path = os.path.dirname(self.filePath)\
            if self.filePath else '.'

        if self.lastOpenDir is not None and len(self.lastOpenDir) > 1:
            path = self.lastOpenDir

        dirpath = ustr(QFileDialog.getExistingDirectory(self,
                                                     '%s - Open Directory' % __appname__, path,  QFileDialog.ShowDirsOnly
                                                     | QFileDialog.DontResolveSymlinks))

        if dirpath is not None and len(dirpath) > 1:
            self.lastOpenDir = dirpath

        self.dirname = dirpath
        self.filePath = None
        self.fileListWidget.clear()
        self.mImgList = self.scanAllImages(dirpath)
        self.openNextImg()
        for imgPath in self.mImgList:
            item = QListWidgetItem(os.path.basename(imgPath))
            self.fileListWidget.addItem(item)
        
        # 打开目录后更新进度显示
        self.updateProgressDisplay()
        self.updateFileListDisplay()

    def verifyImg(self, _value=False):
        # Proceding next image without dialog if having any label
         if self.filePath is not None:
            try:
                self.labelFile.toggleVerify()
            except AttributeError:
                # If the labelling file does not exist yet, create if and
                # re-save it with the verified attribute.
                self.saveFile()
                if self.labelFile is not None:
                    self.labelFile.toggleVerify()
            if self.labelFile is not None:
                self.canvas.verified = True
            self.paintCanvas()
            self.saveFile()

    def openPrevImg(self, _value=False):
        if not self.mayContinue():
            return

        if len(self.mImgList) <= 0:
            return

        if self.filePath is None:
            return

        currIndex = self.mImgList.index(self.filePath)
        if currIndex - 1 >= 0:
            filename = self.mImgList[currIndex - 1]
            if filename:
                self.loadFile(filename)
                # 更新进度显示和文件列表显示
                self.updateProgressDisplay()
                self.updateFileListDisplay()

    def openNextImg(self, _value=False):
        # Proceding next image without dialog if having any label
        if self.autoSaving is True and self.defaultSaveDir is not None:
            if self.dirty is True: 
                self.dirty = False
                self.canvas.verified = True               
                self.saveFile()

        if not self.mayContinue():
            return

        if len(self.mImgList) <= 0:
            return

        filename = None
        if self.filePath is None:
            filename = self.mImgList[0]
        else:
            currIndex = self.mImgList.index(self.filePath)
            if currIndex + 1 < len(self.mImgList):
                filename = self.mImgList[currIndex + 1]

        if filename:
            self.loadFile(filename)
            # 更新进度显示和文件列表显示
            self.updateProgressDisplay()
            self.updateFileListDisplay()

    def copyShapesToNextImage(self):
        # 检查是否有下一帧
        if not self.mayContinue():
            return
        
        if len(self.mImgList) <= 0:
            return
        
        if self.filePath is None:
            return
        
        # 获取当前帧索引和下一帧文件名
        currIndex = self.mImgList.index(self.filePath)
        if currIndex + 1 >= len(self.mImgList):
            # 已经是最后一帧，无法复制到下一帧
            self.status("已经是最后一帧，无法复制到下一帧")
            return
        
        filename = self.mImgList[currIndex + 1]
        
        # 获取选中的标注框
        selected_items = self.labelList.selectedItems()
        if not selected_items:
            self.status("请先选择至少一个标注框")
            return
        
        # 保存选中的标注框
        selected_shapes = []
        for item in selected_items:
            shape = self.itemsToShapes[item]
            selected_shapes.append(shape.copy())
        
        # 如果当前有未保存的更改，先保存
        if self.dirty:
            self.saveFile()
        
        # 加载下一帧
        self.loadFile(filename)
        
        # 将选中的标注框添加到新图像
        for shape in selected_shapes:
            self.canvas.shapes.append(shape)
            self.addLabel(shape)
        
        # 设置为已修改并自动保存
        self.setDirty()
        self.saveFile()  # 添加自动保存功能
        self.canvas.update()
        self.status(f"已将选中的 {len(selected_shapes)} 个标注框复制到下一帧并保存")
            
    def copySelectedShapesToNextImageAndSave(self):
        # 检查是否有下一帧
        if not self.mayContinue():
            return
        
        if len(self.mImgList) <= 0:
            return
        
        if self.filePath is None:
            return
        
        # 获取当前帧索引和下一帧文件名
        currIndex = self.mImgList.index(self.filePath)
        if currIndex + 1 >= len(self.mImgList):
            # 已经是最后一帧，无法复制到下一帧
            self.status("已经是最后一帧，无法复制到下一帧")
            return
        
        filename = self.mImgList[currIndex + 1]
        
        # 获取当前帧的所有标注框
        current_shapes = []
        for shape in self.canvas.shapes:
            current_shapes.append(shape.copy())
        
        # 如果当前有未保存的更改，先保存
        if self.dirty:
            self.saveFile()
        
        # 加载下一帧
        self.loadFile(filename)
        
        # 将当前帧的所有标注框添加到新图像
        for shape in current_shapes:
            self.canvas.shapes.append(shape)
            self.addLabel(shape)
        
        # 设置为已修改并自动保存
        self.setDirty()
        self.saveFile()
        self.canvas.update()
        self.status(f"已将当前帧的 {len(current_shapes)} 个标注框复制到下一帧并保存")


    def openFile(self, _value=False):
        if not self.mayContinue():
            return
        path = os.path.dirname(ustr(self.filePath)) if self.filePath else '.'
        formats = ['*.%s' % fmt.data().decode("ascii").lower() for fmt in QImageReader.supportedImageFormats()]
        filters = "Image & Label files (%s)" % ' '.join(formats + ['*%s' % LabelFile.suffix])
        filename = QFileDialog.getOpenFileName(self, '%s - Choose Image or Label file' % __appname__, path, filters)
        if filename:
            if isinstance(filename, (tuple, list)):
                filename = filename[0]
            self.loadFile(filename)

    def saveFile(self, _value=False):
        if self.defaultSaveDir is not None and len(ustr(self.defaultSaveDir)):
            if self.filePath:
                imgFileName = os.path.basename(self.filePath)
                savedFileName = os.path.splitext(imgFileName)[0] + XML_EXT
                savedPath = os.path.join(ustr(self.defaultSaveDir), savedFileName)
                self._saveFile(savedPath)
        else:
            imgFileDir = os.path.dirname(self.filePath)
            imgFileName = os.path.basename(self.filePath)
            savedFileName = os.path.splitext(imgFileName)[0] + XML_EXT
            savedPath = os.path.join(imgFileDir, savedFileName)
            self._saveFile(savedPath if self.labelFile
                           else self.saveFileDialog())

    def saveFileAs(self, _value=False):
        assert not self.image.isNull(), "cannot save empty image"
        self._saveFile(self.saveFileDialog())

    def saveFileDialog(self):
        caption = '%s - Choose File' % __appname__
        filters = 'File (*%s)' % LabelFile.suffix
        openDialogPath = self.currentPath()
        dlg = QFileDialog(self, caption, openDialogPath, filters)
        dlg.setDefaultSuffix(LabelFile.suffix[1:])
        dlg.setAcceptMode(QFileDialog.AcceptSave)
        filenameWithoutExtension = os.path.splitext(self.filePath)[0]
        dlg.selectFile(filenameWithoutExtension)
        dlg.setOption(QFileDialog.DontUseNativeDialog, False)
        if dlg.exec_():
            return dlg.selectedFiles()[0]
        return ''

    def _saveFile(self, annotationFilePath):
        if annotationFilePath and self.saveLabels(annotationFilePath):
            self.setClean()
            self.statusBar().showMessage('Saved to  %s' % annotationFilePath)
            self.statusBar().show()
            # 保存后更新进度显示
            self.updateProgressDisplay()
            self.updateFileListDisplay()

    def closeFile(self, _value=False):
        if not self.mayContinue():
            return
        self.resetState()
        self.setClean()
        self.toggleActions(False)
        self.canvas.setEnabled(False)
        self.actions.saveAs.setEnabled(False)

    def mayContinue(self):
        return not (self.dirty and not self.discardChangesDialog())

    def discardChangesDialog(self):
        yes, no = QMessageBox.Yes, QMessageBox.No
        msg = u'You have unsaved changes, proceed anyway?'
        return yes == QMessageBox.warning(self, u'Attention', msg, yes | no)

    def errorMessage(self, title, message):
        return QMessageBox.critical(self, title,
                                    '<p><b>%s</b></p>%s' % (title, message))

    def currentPath(self):
        return os.path.dirname(self.filePath) if self.filePath else '.'

    def chooseColor1(self):
        color = self.colorDialog.getColor(self.lineColor, u'Choose line color',
                                          default=DEFAULT_LINE_COLOR)
        if color:
            self.lineColor = color
            # Change the color for all shape lines:
            Shape.line_color = self.lineColor
            self.canvas.update()
            self.setDirty()

    def chooseColor2(self):
        color = self.colorDialog.getColor(self.fillColor, u'Choose fill color',
                                          default=DEFAULT_FILL_COLOR)
        if color:
            self.fillColor = color
            Shape.fill_color = self.fillColor
            self.canvas.update()
            self.setDirty()

    def deleteSelectedShape(self):
        self.remLabel(self.canvas.deleteSelected())
        self.setDirty()
        if self.noShapes():
            for action in self.actions.onShapesPresent:
                action.setEnabled(False)

    def getSelectedShapes(self):
        """获取所有选中的形状"""
        selected_items = self.labelList.selectedItems()
        selected_shapes = []
        for item in selected_items:
            if item in self.itemsToShapes:
                selected_shapes.append(self.itemsToShapes[item])
        return selected_shapes
        
    def batchDeleteShapes(self):
        """批量删除选中的形状"""
        if not self.advanced():
            return
            
        selected_shapes = self.getSelectedShapes()
        if not selected_shapes:
            return
            
        reply = QMessageBox.question(self, '批量删除', 
                                   f'确定要删除选中的 {len(selected_shapes)} 个标注框吗？',
                                   QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            for shape in selected_shapes:
                self.canvas.deleteShape(shape)
                self.remLabel(shape)
            self.setDirty()
            self.status(f"已删除 {len(selected_shapes)} 个标注框")

    def chshapeLineColor(self):
        color = self.colorDialog.getColor(self.lineColor, u'Choose line color',
                                          default=DEFAULT_LINE_COLOR)
        if color:
            self.canvas.selectedShape.line_color = color
            self.canvas.update()
            self.setDirty()

    def chshapeFillColor(self):
        color = self.colorDialog.getColor(self.fillColor, u'Choose fill color',
                                          default=DEFAULT_FILL_COLOR)
        if color:
            self.canvas.selectedShape.fill_color = color
            self.canvas.update()
            self.setDirty()

    def getLabelColor(self, label):
        """根据标签名称生成唯一的颜色"""
        # 定义一组美观的颜色调色板
        beautiful_colors = [
            (255, 99, 132),   # 粉红色
            (54, 162, 235),   # 蓝色
            (255, 205, 86),   # 黄色
            (75, 192, 192),   # 青色
            (153, 102, 255),  # 紫色
            (255, 159, 64),   # 橙色
            (199, 199, 199),  # 灰色
            (83, 102, 255),   # 靛蓝色
            (255, 99, 255),   # 洋红色
            (99, 255, 132),   # 绿色
            (255, 206, 84),   # 金色
            (46, 204, 113),   # 翠绿色
            (155, 89, 182),   # 紫罗兰色
            (52, 152, 219),   # 天蓝色
            (241, 196, 15),   # 向日葵色
            (230, 126, 34),   # 胡萝卜色
            (231, 76, 60),    # 红色
            (149, 165, 166),  # 混凝土色
        ]
        
        # 使用标签文本的哈希值选择颜色，确保相同标签总是获得相同颜色
        hash_object = hashlib.md5(label.encode())
        hash_value = int(hash_object.hexdigest(), 16)
        color_index = hash_value % len(beautiful_colors)
        
        r, g, b = beautiful_colors[color_index]
        
        # 返回带有一定透明度的颜色
        return QColor(r, g, b, 128)

    def copyShape(self):
        self.canvas.endMove(copy=True)
        self.addLabel(self.canvas.selectedShape)
        self.setDirty()

    def moveShape(self):
        self.canvas.endMove(copy=False)
        self.setDirty()

    def showAutoAnnotateDialog(self):
        """显示半自动标注功能的占位对话框"""
        QMessageBox.information(self, "AI半自动标注", 
                               "敬请期待！\n\n此功能将在后续版本中提供：\n" +
                               "• 自动检测目标\n" +
                               "• 智能标注建议\n" +
                               "• 批量处理功能")

    def loadPredefinedClasses(self, predefClassesFile):
        if os.path.exists(predefClassesFile) is True:
            with codecs.open(predefClassesFile, 'r', 'utf8') as f:
                for line in f:
                    line = line.strip()
                    if self.labelHist is None:
                        self.lablHist = [line]
                    else:
                        self.labelHist.append(line)

    def calculateAnnotationProgress(self):
        """计算当前目录的标注进度"""
        if not self.mImgList or not self.dirname:
            return 0, 0, 0.0
            
        total_images = len(self.mImgList)
        annotated_count = 0
        
        for img_path in self.mImgList:
            # 生成对应的XML文件路径
            img_dir = os.path.dirname(img_path)
            img_name = os.path.basename(img_path)
            xml_name = os.path.splitext(img_name)[0] + XML_EXT
            
            # 检查默认保存目录或图片同目录下是否存在XML文件
            if self.defaultSaveDir:
                xml_path = os.path.join(self.defaultSaveDir, xml_name)
            else:
                xml_path = os.path.join(img_dir, xml_name)
                
            if os.path.exists(xml_path):
                annotated_count += 1
                
        progress_percentage = (annotated_count / total_images * 100) if total_images > 0 else 0.0
        return annotated_count, total_images, progress_percentage
    
    def updateProgressDisplay(self):
        """更新进度显示"""
        if not self.progressLabel:
            return
            
        annotated, total, percentage = self.calculateAnnotationProgress()
        if total > 0:
            progress_text = f"已标注: {annotated}/{total} ({percentage:.1f}%)"
            self.progressLabel.setText(progress_text)
        else:
            self.progressLabel.setText("")
    
    def updateFileListDisplay(self):
        """更新文件列表显示，为已标注的图片添加视觉标识"""
        if not self.fileListWidget or not self.mImgList:
            return
            
        for i in range(self.fileListWidget.count()):
            item = self.fileListWidget.item(i)
            if item:
                img_path = self.mImgList[i]
                img_dir = os.path.dirname(img_path)
                img_name = os.path.basename(img_path)
                xml_name = os.path.splitext(img_name)[0] + XML_EXT
                
                # 检查是否已标注
                if self.defaultSaveDir:
                    xml_path = os.path.join(self.defaultSaveDir, xml_name)
                else:
                    xml_path = os.path.join(img_dir, xml_name)
                    
                if os.path.exists(xml_path):
                    # 已标注 - 设置为绿色
                    item.setForeground(QColor(34, 139, 34))  # Forest Green
                    item.setToolTip(f"已标注: {xml_path}")
                else:
                    # 未标注 - 设置为默认颜色
                    item.setForeground(QColor(0, 0, 0))  # Black
                    item.setToolTip("未标注")

    def loadPascalXMLByFilename(self, xmlPath):
        if self.filePath is None:
            return
        if os.path.isfile(xmlPath) is False:
            return

        tVocParseReader = PascalVocReader(xmlPath)
        shapes = tVocParseReader.getShapes()
        self.loadLabels(shapes)
        self.canvas.verified = tVocParseReader.verified
        # 更新进度显示和文件列表显示
        self.updateProgressDisplay()
        self.updateFileListDisplay()

    def handleDoubleClickZoom(self, click_pos):
        """处理双击画布的放大/缩小功能"""
        if not self.image:
            return
            
        if not self.isZoomedIn:
            # 第一次双击：放大到200%
            self.originalZoom = self.zoomWidget.value()
            
            # 获取当前缩放比例
            current_scale = self.canvas.scale
            
            # 将点击位置转换为图像坐标
            # 使用canvas的transformPos方法进行正确的坐标转换
            image_pos = self.canvas.transformPos(QPointF(click_pos))
            
            # 保存图像坐标位置
            self.zoomCenter = image_pos
            
            # 设置放大比例为200%
            target_zoom = 200
            self.setZoom(target_zoom)
            
            # 等待缩放完成后调整滚动位置
            QTimer.singleShot(50, lambda: self.adjustScrollToCenter(image_pos, target_zoom))
            
            self.isZoomedIn = True
            self.status("双击放大到200%，再次双击恢复原始大小")
        else:
            # 第二次双击：恢复原始大小
            self.setZoom(self.originalZoom)
            self.isZoomedIn = False
            self.zoomCenter = None
            self.status("已恢复到原始大小")

    def checkOverlappingBoxes(self):
        """检测重叠的标注框"""
        if not hasattr(self, 'canvas') or not self.canvas.shapes:
            return []
        
        shapes = self.canvas.shapes
        overlapping_pairs = []
        
        # 检查每对标注框是否重叠
        for i in range(len(shapes)):
            for j in range(i + 1, len(shapes)):
                shape1 = shapes[i]
                shape2 = shapes[j]
                
                if self.isOverlapping(shape1, shape2):
                    overlapping_pairs.append((i, j, shape1, shape2))
        
        return overlapping_pairs
    
    def isOverlapping(self, shape1, shape2):
        """判断两个标注框是否重叠"""
        try:
            # 获取两个形状的边界矩形
            rect1 = shape1.boundingRect()
            rect2 = shape2.boundingRect()
            
            # 检查边界矩形是否相交
            if not rect1.intersects(rect2):
                return False
            
            # 对于旋转框，需要更精确的检测
            if (hasattr(shape1, 'isRotated') and shape1.isRotated) or \
               (hasattr(shape2, 'isRotated') and shape2.isRotated):
                return self.checkRotatedBoxOverlap(shape1, shape2)
            else:
                # 普通矩形框的重叠检测
                return self.checkRectangleOverlap(shape1, shape2)
                
        except Exception as e:
            print(f"重叠检测错误: {e}")
            return False
    
    def checkRectangleOverlap(self, shape1, shape2):
        """检测普通矩形框的重叠"""
        try:
            rect1 = shape1.boundingRect()
            rect2 = shape2.boundingRect()
            
            # 计算重叠面积
            intersection = rect1.intersected(rect2)
            if intersection.isEmpty():
                return False
            
            # 计算重叠比例（重叠面积 / 较小框面积）
            area1 = rect1.width() * rect1.height()
            area2 = rect2.width() * rect2.height()
            overlap_area = intersection.width() * intersection.height()
            
            min_area = min(area1, area2)
            overlap_ratio = overlap_area / min_area if min_area > 0 else 0
            
            # 重叠比例超过10%认为是重叠
            return overlap_ratio > 0.1
            
        except Exception as e:
            print(f"矩形重叠检测错误: {e}")
            return False
    
    def checkRotatedBoxOverlap(self, shape1, shape2):
        """检测旋转框的重叠（使用SAT算法）"""
        try:
            # 获取两个形状的顶点
            points1 = shape1.points if hasattr(shape1, 'points') else []
            points2 = shape2.points if hasattr(shape2, 'points') else []
            
            if len(points1) < 4 or len(points2) < 4:
                return False
            
            # 使用分离轴定理(SAT)检测旋转矩形重叠
            return self.separatingAxisTheorem(points1, points2)
            
        except Exception as e:
            print(f"旋转框重叠检测错误: {e}")
            return False
    
    def separatingAxisTheorem(self, points1, points2):
        """分离轴定理检测多边形重叠"""
        try:
            def getAxes(points):
                """获取多边形的所有边的法向量作为分离轴"""
                axes = []
                for i in range(len(points)):
                    p1 = points[i]
                    p2 = points[(i + 1) % len(points)]
                    edge = QPointF(p2.x() - p1.x(), p2.y() - p1.y())
                    # 法向量（垂直于边）
                    normal = QPointF(-edge.y(), edge.x())
                    # 归一化
                    length = (normal.x() ** 2 + normal.y() ** 2) ** 0.5
                    if length > 0:
                        axes.append(QPointF(normal.x() / length, normal.y() / length))
                return axes
            
            def projectPolygon(points, axis):
                """将多边形投影到轴上"""
                dots = [point.x() * axis.x() + point.y() * axis.y() for point in points]
                return min(dots), max(dots)
            
            # 获取两个多边形的所有分离轴
            axes = getAxes(points1) + getAxes(points2)
            
            # 检查每个轴上的投影是否分离
            for axis in axes:
                min1, max1 = projectPolygon(points1, axis)
                min2, max2 = projectPolygon(points2, axis)
                
                # 如果在某个轴上分离，则不重叠
                if max1 < min2 or max2 < min1:
                    return False
            
            # 所有轴上都有重叠，则两个多边形重叠
            return True
            
        except Exception as e:
            print(f"SAT算法错误: {e}")
            return False
    
    def updateOverlapWarning(self):
        """更新重叠警告信息"""
        try:
            overlapping_pairs = self.checkOverlappingBoxes()
            
            if overlapping_pairs:
                warning_msg = f"⚠️ 检测到 {len(overlapping_pairs)} 对重叠标注框"
                self.statusBar().showMessage(warning_msg, 10000)  # 显示10秒
                
                # 在状态栏添加永久的警告标签
                if not hasattr(self, 'overlapWarningLabel'):
                    self.overlapWarningLabel = QLabel()
                    self.overlapWarningLabel.setStyleSheet("""
                        QLabel {
                            color: #FF4444;
                            font-weight: bold;
                            background-color: rgba(255, 68, 68, 0.1);
                            border: 1px solid #FF4444;
                            border-radius: 4px;
                            padding: 2px 6px;
                        }
                    """)
                    self.statusBar().addPermanentWidget(self.overlapWarningLabel)
                
                self.overlapWarningLabel.setText(f"⚠️ {len(overlapping_pairs)}对重叠")
                self.overlapWarningLabel.setVisible(True)
                
                # 打印详细信息到控制台
                print(f"检测到重叠标注框:")
                for i, (idx1, idx2, shape1, shape2) in enumerate(overlapping_pairs):
                    label1 = getattr(shape1, 'label', '未命名')
                    label2 = getattr(shape2, 'label', '未命名')
                    print(f"  {i+1}. 标注框 {idx1+1}({label1}) 与 标注框 {idx2+1}({label2}) 重叠")
            else:
                # 没有重叠，隐藏警告
                if hasattr(self, 'overlapWarningLabel'):
                    self.overlapWarningLabel.setVisible(False)
                    
        except Exception as e:
            print(f"更新重叠警告错误: {e}")

    def adjustScrollToCenter(self, image_pos, target_zoom):
        """调整滚动条使指定的图像位置居中显示"""
        if not self.canvas.pixmap:
            return
            
        # 获取新的缩放比例
        new_scale = self.canvas.scale
        
        # 计算图像在画布中的位置（考虑缩放和偏移）
        offset = self.canvas.offsetToCenter()
        
        # 将图像坐标转换为画布坐标
        canvas_pos = (image_pos + offset) * new_scale
        
        # 获取滚动区域的中心点
        scroll_area = self.centralWidget()
        viewport_center = QPointF(
            scroll_area.viewport().width() / 2.0,
            scroll_area.viewport().height() / 2.0
        )
        
        # 计算需要滚动的偏移量
        scroll_offset = canvas_pos - viewport_center
        
        # 调整滚动条位置
        h_bar = self.scrollBars[Qt.Horizontal]
        v_bar = self.scrollBars[Qt.Vertical]
        
        # 设置新的滚动位置
        new_h_value = max(0, min(h_bar.maximum(), int(scroll_offset.x())))
        new_v_value = max(0, min(v_bar.maximum(), int(scroll_offset.y())))
        
        h_bar.setValue(new_h_value)
        v_bar.setValue(new_v_value)


class Settings(object):
    """Convenience dict-like wrapper around QSettings."""

    def __init__(self, types=None):
        self.data = QSettings()
        self.types = defaultdict(lambda: QVariant, types if types else {})

    def __setitem__(self, key, value):
        t = self.types[key]
        self.data.setValue(key,
                           t(value) if not isinstance(value, t) else value)

    def __getitem__(self, key):
        return self._cast(key, self.data.value(key))

    def get(self, key, default=None):
        return self._cast(key, self.data.value(key, default))

    def _cast(self, key, value):
        # XXX: Very nasty way of converting types to QVariant methods :P
        t = self.types.get(key)
        if t is not None and t != QVariant:
            if t is str:
                return ustr(value)
            else:
                try:
                    method = getattr(QVariant, re.sub(
                        '^Q', 'to', t.__name__, count=1))
                    return method(value)
                except AttributeError as e:
                    # print(e)
                    return value
        return value


def inverted(color):
    return QColor(*[255 - v for v in color.getRgb()])


def read(filename, default=None):
    try:
        with open(filename, 'rb') as f:
            return f.read()
    except:
        return default


def get_main_app(argv=[]):
    """
    Standard boilerplate Qt application code.
    Do everything but app.exec_() -- so that we can test the application in one thread
    """
    app = QApplication(argv)
    app.setApplicationName(__appname__)
    app.setWindowIcon(newIcon("app"))
    # Tzutalin 201705+: Accept extra agruments to change predefined class file
    # Usage : labelImg.py image predefClassFile
    win = MainWindow(argv[1] if len(argv) >= 2 else None,
                     argv[2] if len(argv) >= 3 else os.path.join('data', 'predefined_classes.txt'))
    win.show()
    return app, win


def main(argv=[]):
    '''construct main app and run it'''
    app, _win = get_main_app(argv)
    return app.exec_()

if __name__ == '__main__':
    sys.exit(main(sys.argv))
