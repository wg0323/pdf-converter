# -*- mode: python ; coding: utf-8 -*-
import os

block_cipher = None

# OCR 增强包（ocr_addon）运行时需要的标准库模块闭包：
# paddle/paddleocr 启动时导入，但主程序未直接使用、PyInstaller 扫不到，
# 需显式打入冻结包（由开发环境导入 PPStructure 后扫描 sys.modules 生成）
OCR_ADDON_STDLIB = [
    'abc', 'argparse', 'array', 'ast', 'asyncio', 'asyncio.base_events', 'asyncio.base_futures', 'asyncio.base_subprocess',
    'asyncio.base_tasks', 'asyncio.constants', 'asyncio.coroutines', 'asyncio.events', 'asyncio.exceptions', 'asyncio.format_helpers', 'asyncio.futures', 'asyncio.locks',
    'asyncio.log', 'asyncio.mixins', 'asyncio.proactor_events', 'asyncio.protocols', 'asyncio.queues', 'asyncio.runners', 'asyncio.selector_events', 'asyncio.sslproto',
    'asyncio.staggered', 'asyncio.streams', 'asyncio.subprocess', 'asyncio.taskgroups', 'asyncio.tasks', 'asyncio.threads', 'asyncio.timeouts', 'asyncio.transports',
    'asyncio.trsock', 'asyncio.windows_events', 'asyncio.windows_utils', 'atexit', 'base64', 'bdb', 'binascii', 'bisect',
    'builtins', 'bz2', 'calendar', 'cmd', 'code', 'codecs', 'codeop', 'collections',
    'collections.abc', 'colorsys', 'concurrent', 'concurrent.futures', 'concurrent.futures._base', 'concurrent.futures.thread', 'configparser', 'contextlib',
    'contextvars', 'copy', 'copyreg', 'csv', 'ctypes', 'ctypes._endian', 'ctypes.wintypes', 'dataclasses',
    'datetime', 'decimal', 'difflib', 'dis', 'distutils', 'distutils._collections', 'distutils._functools', 'distutils._msvccompiler',
    'distutils.archive_util', 'distutils.ccompiler', 'distutils.cmd', 'distutils.command', 'distutils.command._framework_compat', 'distutils.command.bdist', 'distutils.command.build', 'distutils.command.build_ext',
    'distutils.command.build_scripts', 'distutils.command.install', 'distutils.command.py37compat', 'distutils.command.sdist', 'distutils.config', 'distutils.core', 'distutils.debug', 'distutils.dep_util',
    'distutils.dir_util', 'distutils.dist', 'distutils.errors', 'distutils.extension', 'distutils.fancy_getopt', 'distutils.file_util', 'distutils.filelist', 'distutils.log',
    'distutils.py39compat', 'distutils.spawn', 'distutils.sysconfig', 'distutils.text_file', 'distutils.util', 'email', 'email._encoded_words', 'email._header_value_parser',
    'email._parseaddr', 'email._policybase', 'email.base64mime', 'email.charset', 'email.encoders', 'email.errors', 'email.feedparser', 'email.header',
    'email.headerregistry', 'email.iterators', 'email.message', 'email.parser', 'email.quoprimime', 'email.utils', 'encodings', 'encodings.aliases',
    'encodings.ascii', 'encodings.big5', 'encodings.big5hkscs', 'encodings.cp037', 'encodings.cp1006', 'encodings.cp1026', 'encodings.cp1125', 'encodings.cp1140',
    'encodings.cp1250', 'encodings.cp1251', 'encodings.cp1252', 'encodings.cp1253', 'encodings.cp1254', 'encodings.cp1255', 'encodings.cp1256', 'encodings.cp1257',
    'encodings.cp1258', 'encodings.cp273', 'encodings.cp424', 'encodings.cp437', 'encodings.cp500', 'encodings.cp720', 'encodings.cp737', 'encodings.cp775',
    'encodings.cp850', 'encodings.cp852', 'encodings.cp855', 'encodings.cp856', 'encodings.cp857', 'encodings.cp858', 'encodings.cp860', 'encodings.cp861',
    'encodings.cp862', 'encodings.cp863', 'encodings.cp864', 'encodings.cp865', 'encodings.cp866', 'encodings.cp869', 'encodings.cp874', 'encodings.cp875',
    'encodings.cp932', 'encodings.cp949', 'encodings.cp950', 'encodings.euc_jis_2004', 'encodings.euc_jisx0213', 'encodings.euc_jp', 'encodings.euc_kr', 'encodings.gb18030',
    'encodings.gb2312', 'encodings.gbk', 'encodings.hp_roman8', 'encodings.hz', 'encodings.idna', 'encodings.iso2022_jp', 'encodings.iso2022_jp_1', 'encodings.iso2022_jp_2',
    'encodings.iso2022_jp_2004', 'encodings.iso2022_jp_3', 'encodings.iso2022_jp_ext', 'encodings.iso2022_kr', 'encodings.iso8859_10', 'encodings.iso8859_11', 'encodings.iso8859_13', 'encodings.iso8859_14',
    'encodings.iso8859_15', 'encodings.iso8859_16', 'encodings.iso8859_2', 'encodings.iso8859_3', 'encodings.iso8859_4', 'encodings.iso8859_5', 'encodings.iso8859_6', 'encodings.iso8859_7',
    'encodings.iso8859_8', 'encodings.iso8859_9', 'encodings.johab', 'encodings.koi8_r', 'encodings.koi8_t', 'encodings.koi8_u', 'encodings.kz1048', 'encodings.latin_1',
    'encodings.mac_cyrillic', 'encodings.mac_greek', 'encodings.mac_iceland', 'encodings.mac_latin2', 'encodings.mac_roman', 'encodings.mac_turkish', 'encodings.ptcp154', 'encodings.raw_unicode_escape',
    'encodings.shift_jis', 'encodings.shift_jis_2004', 'encodings.shift_jisx0213', 'encodings.tis_620', 'encodings.unicode_escape', 'encodings.utf_8', 'enum', 'errno',
    'fileinput', 'fnmatch', 'fractions', 'functools', 'gc', 'genericpath', 'getopt', 'gettext',
    'glob', 'gzip', 'hashlib', 'heapq', 'hmac', 'html', 'html.entities', 'html.parser',
    'http', 'http.client', 'http.cookiejar', 'http.cookies', 'importlib', 'importlib._abc', 'importlib._bootstrap', 'importlib._bootstrap_external',
    'importlib.abc', 'importlib.machinery', 'importlib.metadata', 'importlib.metadata._adapters', 'importlib.metadata._collections', 'importlib.metadata._functools', 'importlib.metadata._itertools', 'importlib.metadata._meta',
    'importlib.metadata._text', 'importlib.readers', 'importlib.resources', 'importlib.resources._adapters', 'importlib.resources._common', 'importlib.resources._itertools', 'importlib.resources._legacy', 'importlib.resources.abc',
    'importlib.resources.readers', 'importlib.util', 'inspect', 'io', 'ipaddress', 'itertools', 'json', 'json.decoder',
    'json.encoder', 'json.scanner', 'keyword', 'linecache', 'locale', 'logging', 'lzma', 'marshal',
    'math', 'mimetypes', 'mmap', 'msvcrt', 'multiprocessing', 'multiprocessing.context', 'multiprocessing.process', 'multiprocessing.reduction',
    'multiprocessing.util', 'nt', 'ntpath', 'nturl2path', 'numbers', 'opcode', 'operator', 'os',
    'os.path', 'pathlib', 'pdb', 'pickle', 'pkgutil', 'platform', 'plistlib', 'posixpath',
    'pprint', 'pydoc', 'pyexpat', 'pyexpat.errors', 'pyexpat.model', 'queue', 'quopri', 'random',
    're', 're._casefix', 're._compiler', 're._constants', 're._parser', 'reprlib', 'secrets', 'select',
    'selectors', 'shlex', 'shutil', 'signal', 'site', 'socket', 'sqlite3', 'sqlite3.dbapi2',
    'ssl', 'stat', 'string', 'stringprep', 'struct', 'subprocess', 'sys', 'sysconfig',
    'tarfile', 'tempfile', 'textwrap', 'threading', 'time', 'timeit', 'token', 'tokenize',
    'traceback', 'types', 'typing', 'unicodedata', 'unittest', 'unittest.case',
    'unittest.loader', 'unittest.main', 'unittest.mock', 'unittest.result', 'unittest.runner', 'unittest.signals', 'unittest.suite', 'unittest.util',
    'urllib', 'urllib.error', 'urllib.parse', 'urllib.request', 'urllib.response', 'uuid', 'warnings', 'wave',
    'weakref', 'winreg', 'xml', 'xml.etree', 'xml.etree.ElementPath', 'xml.etree.ElementTree', 'xml.parsers', 'xml.parsers.expat',
    'xml.parsers.expat.errors', 'xml.parsers.expat.model', 'zipfile', 'zipimport', 'zlib', 'zoneinfo', 'zoneinfo._common', 'zoneinfo._tzpath',
]

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
    ] + OCR_ADDON_STDLIB,
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
