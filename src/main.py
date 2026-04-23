import sys
from PyQt6.QtWidgets import QApplication

# 使用新版主窗口
from src.ui.main_window_v2 import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    # 设置应用程序信息
    app.setApplicationName('PDF转换器')
    app.setApplicationVersion('2.0.0')
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
