# -*- mode: python ; coding: utf-8 -*-
import os

block_cipher = None

a = Analysis(
    ['src/main.py'],
    pathex=['src'],
    binaries=[],
    datas=[
        ('resources/icons', 'resources/icons'),
    ],
    hiddenimports=[
        'pdf2docx',
        'PyQt6.sip',
        'docx',
        'docx.shared',
        'src.models.task_item',
        'src.ui.styles.main_window_style',
        'src.core.task_manager',
        'src.core.single_task_worker',
        'src.core.pdf_to_word',
        'src.ui.main_window_v2',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # 排除不必要的模块以减小体积
        'matplotlib',
        'tkinter',
        'IPython',
        'jupyter',
        'notebook',
        'sphinx',
        'pytest',
        'setuptools',
        'pip',
        # PaddleOCR 不再打包（体积/打包时间最大来源）；
        # 代码内为函数内懒导入，缺失时扫描版PDF自动降级为图片模式
        'paddleocr',
        'paddle',
        'paddlex',
        'shapely',
        'pyclipper',
        'lmdb',
        'scipy',
        'skimage',
        'albumentations',
        'rapidfuzz',
        # 间接拉入但本项目及 pdf2docx 均不使用
        'pandas',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='PDFConverter',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='resources/icons/app.ico' if os.path.exists('resources/icons/app.ico') else None,
)

# 目录模式（onedir）：启动无需自解压到临时目录，大幅提升启动速度；
# UPX 禁用：避免构建时逐个压缩 DLL 与运行时解压开销
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='PDFConverter',
)
