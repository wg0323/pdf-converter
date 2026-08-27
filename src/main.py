import os
import sys
import faulthandler
import traceback
import multiprocessing
from datetime import datetime


def _crash_log_path() -> str:
    """崩溃日志路径：打包环境放exe同级目录，开发环境放项目根目录"""
    if getattr(sys, 'frozen', False):
        base_dir = os.path.dirname(sys.executable)
    else:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_dir, 'crash_log.txt')


# 保持文件对象在进程生命周期内存活，供 faulthandler 写入C层崩溃堆栈
_crash_log_file = None


def _log_uncaught_exception(exc_type, exc_value, exc_tb):
    """记录未捕获的Python异常，避免静默闪退无迹可循"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    _crash_log_file.write(f"\n===== 未捕获异常 {timestamp} =====\n")
    traceback.print_exception(exc_type, exc_value, exc_tb, file=_crash_log_file)
    _crash_log_file.flush()
    sys.__excepthook__(exc_type, exc_value, exc_tb)


def _setup_crash_logging():
    """初始化崩溃日志与异常钩子（仅主进程执行）

    必须在 main() 内调用：Windows 下 multiprocessing 使用 spawn 方式，
    子进程会重新执行本模块的模块级代码，若在模块级打开日志文件并注册
    钩子，子进程会重复打开崩溃日志、重复 enable faulthandler。
    """
    global _crash_log_file
    _crash_log_file = open(_crash_log_path(), 'a', encoding='utf-8')
    # 捕获段错误等原生崩溃（如 pdf2docx/PaddleOCR 底层C库崩溃）
    faulthandler.enable(file=_crash_log_file)
    sys.excepthook = _log_uncaught_exception


def main():
    _setup_crash_logging()

    # 延迟导入：避免 spawn 子进程重新执行模块级代码时连带加载整套 Qt UI
    from PyQt6.QtWidgets import QApplication
    from src.ui.main_window_v2 import MainWindow

    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    # 设置应用程序信息
    app.setApplicationName('PDF转换器')
    app.setApplicationVersion('4.0.0')
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())


if __name__ == '__main__':
    # PyInstaller 打包后使用 multiprocessing 必须调用，否则子进程会重复启动主程序
    multiprocessing.freeze_support()
    main()
