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
        'pdfplumber',
        'PyQt6.sip',
        'docx',
        'docx.shared',
        'src.models.task_item',
        'src.ui.styles.main_window_style',
        'src.core.task_manager',
        'src.core.single_task_worker',
        'src.core.pdf_to_word',
        'src.core.pdf_to_markdown',
        'src.ui.main_window_v2',
        # PaddleOCR 相关依赖（可选，如果安装了则打包）
        'paddleocr',
        'paddle',
        'paddle.dataset',
        'shapely',
        'pyclipper',
        'lmdb',
        'scipy',
        'skimage',
        'imgaug',
        'albumentations',
        'rapidfuzz',
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
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='PDFConverter',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='resources/icons/app.ico' if os.path.exists('resources/icons/app.ico') else None,
)
