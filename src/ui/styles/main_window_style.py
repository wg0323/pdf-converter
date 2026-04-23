"""
主窗口样式表 - Element Plus 风格
"""

MAIN_WINDOW_STYLE = """
QMainWindow {
    background-color: #f5f7fa;
}

QGroupBox {
    font-size: 14px;
    font-weight: bold;
    color: #303133;
    border: 1px solid #dcdfe6;
    border-radius: 8px;
    margin-top: 12px;
    padding-top: 20px;
    background-color: #ffffff;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 15px;
    padding: 0 8px;
    color: #409eff;
}

QPushButton {
    background-color: #ffffff;
    color: #606266;
    border: 1px solid #dcdfe6;
    border-radius: 6px;
    padding: 8px 16px;
    font-size: 13px;
    font-weight: 500;
    min-width: 100px;
}

QPushButton:hover {
    background-color: #f5f7fa;
    border-color: #c0c4cc;
    color: #409eff;
}

QPushButton:pressed {
    background-color: #ecf5ff;
}

QPushButton:disabled {
    background-color: #f5f7fa;
    color: #c0c4cc;
    border-color: #e4e7ed;
}

QPushButton#primary {
    background-color: #409eff;
    color: #ffffff;
    border: 1px solid #409eff;
    font-weight: bold;
}

QPushButton#primary:hover {
    background-color: #66b1ff;
    border-color: #66b1ff;
}

QPushButton#primary:pressed {
    background-color: #3a8ee6;
}

QPushButton#primary:disabled {
    background-color: #a0cfff;
    border-color: #a0cfff;
}

QLineEdit {
    border: 1px solid #dcdfe6;
    border-radius: 6px;
    padding: 8px 12px;
    font-size: 13px;
    background-color: #ffffff;
    color: #606266;
}

QCheckBox {
    font-size: 13px;
    color: #606266;
    spacing: 8px;
}

QLabel {
    font-size: 13px;
    color: #606266;
}

QTableWidget {
    border: 1px solid #dcdfe6;
    border-radius: 6px;
    background-color: #ffffff;
    gridline-color: #ebeef5;
    font-size: 13px;
}

QTableWidget::item {
    padding: 8px;
    border: none;
}

QTableWidget::item:selected {
    background-color: #ecf5ff;
    color: #409eff;
    border: none;
}

QHeaderView::section {
    background-color: #f5f7fa;
    color: #606266;
    padding: 8px;
    border: none;
    border-bottom: 2px solid #e4e7ed;
    font-weight: bold;
}

QPlainTextEdit {
    border: 1px solid #dcdfe6;
    border-radius: 6px;
    background-color: #fafafa;
    padding: 10px;
    font-family: 'Consolas', 'Monaco', monospace;
    font-size: 12px;
    color: #606266;
}
"""
