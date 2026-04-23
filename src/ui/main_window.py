import os
import time
from datetime import datetime
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QListWidget, QListWidgetItem, QCheckBox,
    QLabel, QFileDialog, QProgressBar, QGroupBox, QMessageBox,
    QLineEdit, QAbstractItemView, QGraphicsOpacityEffect,
    QPlainTextEdit
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QUrl
from PyQt6.QtGui import QDragEnterEvent, QDropEvent, QDesktopServices

from src.models.file_item import FileItem, FileStatus
from src.core.converter_worker import ConverterWorker


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.worker = None
        self.file_items = []
        self.conversion_start_time = None
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_elapsed_time)
        self.init_ui()
        self.setup_connections()
        self.apply_style()

    def init_ui(self):
        self.setWindowTitle('PDF转换器')
        self.resize(850, 650)
        self.setAcceptDrops(True)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(16)
        main_layout.setContentsMargins(20, 20, 20, 20)

        self.setup_file_section(main_layout)
        self.setup_output_section(main_layout)
        self.setup_format_section(main_layout)
        self.setup_progress_section(main_layout)
        self.setup_log_section(main_layout)
        self.setup_button_section(main_layout)
        
        # 遮罩层（转换时禁用界面）
        self.overlay = QGraphicsOpacityEffect(self)
        self.overlay.setOpacity(1.0)

    def apply_style(self):
        self.setStyleSheet("""
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
            
            QListWidget {
                border: 1px solid #dcdfe6;
                border-radius: 6px;
                background-color: #ffffff;
                padding: 8px;
                font-size: 13px;
                color: #606266;
            }
            
            QListWidget::item {
                padding: 8px;
                border-radius: 4px;
                margin: 2px 0;
            }
            
            QListWidget::item:selected {
                background-color: #ecf5ff;
                color: #409eff;
                border: none;
            }
            
            QListWidget::item:hover {
                background-color: #f5f7fa;
            }
            
            QPushButton {
                background-color: #ffffff;
                color: #606266;
                border: 1px solid #dcdfe6;
                border-radius: 6px;
                padding: 10px 20px;
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
                background-color: #ffffff;
                color: #c0c4cc;
                border-color: #ebeef5;
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
            
            QPushButton#danger {
                background-color: #ffffff;
                color: #f56c6c;
                border: 1px solid #fbc4c4;
            }
            
            QPushButton#danger:hover {
                background-color: #fef0f0;
                border-color: #f56c6c;
            }
            
            QLineEdit {
                border: 1px solid #dcdfe6;
                border-radius: 6px;
                padding: 10px 15px;
                font-size: 13px;
                background-color: #ffffff;
                color: #606266;
            }
            
            QLineEdit:hover {
                border-color: #c0c4cc;
            }
            
            QLineEdit:focus {
                border-color: #409eff;
            }
            
            QLineEdit:disabled {
                background-color: #f5f7fa;
                border-color: #e4e7ed;
                color: #a8abb2;
            }
            
            QCheckBox {
                font-size: 13px;
                color: #606266;
                spacing: 8px;
            }
            
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
                border: 1px solid #dcdfe6;
                border-radius: 4px;
                background-color: #ffffff;
            }
            
            QCheckBox::indicator:checked {
                background-color: #409eff;
                border-color: #409eff;
            }
            
            QCheckBox::indicator:hover {
                border-color: #409eff;
            }
            
            QLabel {
                font-size: 13px;
                color: #606266;
                background-color: transparent;
            }
            
            QProgressBar {
                border: 1px solid #e4e7ed;
                border-radius: 10px;
                text-align: center;
                background-color: #f5f7fa;
                height: 20px;
                font-size: 12px;
                color: #606266;
            }
            
            QProgressBar::chunk {
                background-color: #409eff;
                border-radius: 9px;
            }
            
            QPlainTextEdit {
                border: 1px solid #dcdfe6;
                border-radius: 6px;
                background-color: #fafafa;
                padding: 10px;
                font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
                font-size: 12px;
                color: #606266;
            }
            
            QPlainTextEdit:focus {
                border-color: #409eff;
            }
        """)

    def setup_file_section(self, parent_layout):
        file_group = QGroupBox('PDF文件列表')
        file_layout = QVBoxLayout(file_group)
        file_layout.setSpacing(12)

        self.file_list = QListWidget()
        self.file_list.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.file_list.setMinimumHeight(200)
        self.file_list.setAlternatingRowColors(True)
        file_layout.addWidget(self.file_list)

        file_button_layout = QHBoxLayout()
        file_button_layout.setSpacing(10)
        
        self.add_files_btn = QPushButton('➕ 添加文件')
        self.add_files_btn.setObjectName('primary')
        
        self.remove_files_btn = QPushButton('➖ 移除选中')
        self.remove_files_btn.setObjectName('danger')
        
        self.clear_files_btn = QPushButton('🗑️ 清空全部')
        
        file_button_layout.addWidget(self.add_files_btn)
        file_button_layout.addWidget(self.remove_files_btn)
        file_button_layout.addWidget(self.clear_files_btn)
        file_button_layout.addStretch()
        file_layout.addLayout(file_button_layout)

        parent_layout.addWidget(file_group)

    def setup_output_section(self, parent_layout):
        output_group = QGroupBox('输出目录')
        output_layout = QHBoxLayout(output_group)
        output_layout.setSpacing(12)

        self.output_path_edit = QLineEdit()
        self.output_path_edit.setReadOnly(True)
        self.output_path_edit.setPlaceholderText('默认：与PDF文件相同目录')
        output_layout.addWidget(self.output_path_edit)

        self.browse_output_btn = QPushButton('📁 浏览')
        self.browse_output_btn.setMaximumWidth(120)
        output_layout.addWidget(self.browse_output_btn)

        parent_layout.addWidget(output_group)

    def setup_format_section(self, parent_layout):
        format_group = QGroupBox('输出格式')
        format_layout = QHBoxLayout(format_group)
        format_layout.setSpacing(20)

        self.word_checkbox = QCheckBox('Word文档 (.docx)')
        self.word_checkbox.setChecked(True)
        
        self.markdown_checkbox = QCheckBox('Markdown文件 (.md)')
        self.markdown_checkbox.setChecked(False)
        
        self.both_label = QLabel('💡 至少选择一种格式')
        self.both_label.setStyleSheet('color: #909399; font-size: 12px;')

        format_layout.addWidget(self.word_checkbox)
        format_layout.addWidget(self.markdown_checkbox)
        format_layout.addStretch()
        format_layout.addWidget(self.both_label)

        parent_layout.addWidget(format_group)

    def setup_progress_section(self, parent_layout):
        progress_group = QGroupBox('转换进度')
        progress_layout = QVBoxLayout(progress_group)
        progress_layout.setSpacing(10)

        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat('%p% 完成')
        progress_layout.addWidget(self.progress_bar)

        status_layout = QHBoxLayout()
        self.status_label = QLabel('⏳ 就绪')
        self.status_label.setStyleSheet('font-weight: bold; color: #67c23a;')
        status_layout.addWidget(self.status_label)
        
        self.time_label = QLabel('')
        self.time_label.setStyleSheet('color: #909399;')
        status_layout.addWidget(self.time_label)
        status_layout.addStretch()
        progress_layout.addLayout(status_layout)

        parent_layout.addWidget(progress_group)

    def setup_log_section(self, parent_layout):
        log_group = QGroupBox('📋 转换日志')
        log_layout = QVBoxLayout(log_group)
        log_layout.setSpacing(10)

        self.log_text = QPlainTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumBlockCount(1000)  # 限制最大行数
        self.log_text.setPlaceholderText('转换日志将显示在这里...')
        log_layout.addWidget(self.log_text)

        log_button_layout = QHBoxLayout()
        self.clear_log_btn = QPushButton('🧹 清空日志')
        self.open_output_dir_btn = QPushButton('📂 打开输出目录')
        self.open_output_dir_btn.setEnabled(False)
        
        log_button_layout.addWidget(self.clear_log_btn)
        log_button_layout.addStretch()
        log_button_layout.addWidget(self.open_output_dir_btn)
        log_layout.addLayout(log_button_layout)

        parent_layout.addWidget(log_group)

    def setup_button_section(self, parent_layout):
        button_layout = QHBoxLayout()
        button_layout.setSpacing(12)
        button_layout.addStretch()

        self.convert_btn = QPushButton('🚀 开始转换')
        self.convert_btn.setObjectName('primary')
        self.convert_btn.setMinimumWidth(180)
        self.convert_btn.setEnabled(False)
        self.convert_btn.setStyleSheet('font-size: 14px; padding: 12px 30px;')
        button_layout.addWidget(self.convert_btn)

        parent_layout.addLayout(button_layout)

    def setup_connections(self):
        self.add_files_btn.clicked.connect(self.add_files)
        self.remove_files_btn.clicked.connect(self.remove_selected_files)
        self.clear_files_btn.clicked.connect(self.clear_files)
        self.browse_output_btn.clicked.connect(self.browse_output_directory)
        self.convert_btn.clicked.connect(self.start_conversion)
        self.word_checkbox.stateChanged.connect(self.update_convert_button)
        self.markdown_checkbox.stateChanged.connect(self.update_convert_button)
        self.clear_log_btn.clicked.connect(self.clear_log)
        self.open_output_dir_btn.clicked.connect(self.open_output_directory)

    def add_files(self):
        files, _ = QFileDialog.getOpenFileNames(
            self,
            '选择PDF文件',
            '',
            'PDF文件 (*.pdf)'
        )
        if files:
            for file in files:
                if file not in [self.file_list.item(i).text() for i in range(self.file_list.count())]:
                    self.file_list.addItem(file)
            self.update_file_items()
            self.update_convert_button()

    def remove_selected_files(self):
        for item in self.file_list.selectedItems():
            self.file_list.takeItem(self.file_list.row(item))
        self.update_file_items()
        self.update_convert_button()

    def clear_files(self):
        self.file_list.clear()
        self.file_items.clear()
        self.update_convert_button()

    def browse_output_directory(self):
        directory = QFileDialog.getExistingDirectory(
            self,
            '选择输出目录',
            ''
        )
        if directory:
            self.output_path_edit.setText(directory)

    def update_file_items(self):
        """更新文件项列表"""
        self.file_items = []
        for i in range(self.file_list.count()):
            file_path = self.file_list.item(i).text()
            self.file_items.append(FileItem(file_path=file_path))

    def update_convert_button(self):
        has_files = self.file_list.count() > 0
        has_format = self.word_checkbox.isChecked() or self.markdown_checkbox.isChecked()
        self.convert_btn.setEnabled(has_files and has_format)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        files = [url.toLocalFile() for url in event.mimeData().urls()]
        pdf_files = [f for f in files if f.lower().endswith('.pdf')]
        for file in pdf_files:
            if file not in [self.file_list.item(i).text() for i in range(self.file_list.count())]:
                self.file_list.addItem(file)
        self.update_file_items()
        self.update_convert_button()

    def start_conversion(self):
        """开始转换"""
        if not self.file_items:
            self.update_file_items()
        
        if not self.file_items:
            QMessageBox.warning(self, '警告', '请先添加PDF文件！')
            return
        
        # 检查格式选择
        convert_to_word = self.word_checkbox.isChecked()
        convert_to_markdown = self.markdown_checkbox.isChecked()
        
        if not convert_to_word and not convert_to_markdown:
            QMessageBox.warning(self, '警告', '请至少选择一种输出格式！')
            return
        
        # 获取输出目录
        output_dir = self.output_path_edit.text() or None
        
        # 清空日志并记录开始信息
        self.log_text.clear()
        self.add_log('=' * 50)
        self.add_log('开始批量转换')
        self.add_log(f'待转换文件数: {len(self.file_items)}')
        self.add_log(f'输出格式: {"Word" if convert_to_word else ""}{" + " if convert_to_word and convert_to_markdown else ""}{"Markdown" if convert_to_markdown else ""}')
        self.add_log(f'输出目录: {output_dir if output_dir else "与PDF文件相同目录"}')
        self.add_log('=' * 50)
        
        # 启用打开输出目录按钮
        self.open_output_dir_btn.setEnabled(True)
        
        # 重置状态
        for item in self.file_items:
            item.status = FileStatus.PENDING
            item.error_message = None
        
        # 更新UI
        self.set_ui_enabled(False)
        self.progress_bar.setValue(0)
        self.status_label.setText('🔄 正在转换...')
        self.status_label.setStyleSheet('font-weight: bold; color: #409eff;')
        self.convert_btn.setText('⏹️ 取消转换')
        self.convert_btn.clicked.disconnect()
        self.convert_btn.clicked.connect(self.cancel_conversion)
        
        # 启动计时器
        self.conversion_start_time = time.time()
        self.timer.start(1000)  # 每秒更新一次
        
        # 创建工作线程
        self.worker = ConverterWorker(
            file_items=self.file_items,
            output_dir=output_dir,
            convert_to_word=convert_to_word,
            convert_to_markdown=convert_to_markdown
        )
        
        # 连接信号
        self.worker.progress_updated.connect(self.on_progress_updated)
        self.worker.file_finished.connect(self.on_file_finished)
        self.worker.conversion_finished.connect(self.on_conversion_finished)
        self.worker.conversion_cancelled.connect(self.on_conversion_cancelled)
        
        # 启动转换
        self.worker.start()

    def cancel_conversion(self):
        """取消转换"""
        if self.worker and self.worker.isRunning():
            self.add_log('正在取消转换...', 'WARNING')
            self.worker.cancel()
            self.status_label.setText('⏸️ 正在取消...')
            self.status_label.setStyleSheet('font-weight: bold; color: #e6a23c;')

    def on_progress_updated(self, current, total, status):
        """进度更新回调"""
        progress = int((current / total) * 100) if total > 0 else 0
        self.progress_bar.setValue(progress)
        self.status_label.setText(f'🔄 {status} ({current}/{total})')

    def on_file_finished(self, file_item, success, message):
        """单个文件完成回调"""
        # 更新列表项显示
        for i in range(self.file_list.count()):
            list_item = self.file_list.item(i)
            if list_item.text() == file_item.file_path or list_item.text().startswith(('✅', '❌')) and file_item.file_name in list_item.text():
                if success:
                    list_item.setText(f'✅ {file_item.file_name}')
                    list_item.setForeground(Qt.GlobalColor.darkGreen)
                    self.add_log(f'✓ {file_item.file_name} - 转换成功', 'SUCCESS')
                else:
                    list_item.setText(f'❌ {file_item.file_name}')
                    list_item.setForeground(Qt.GlobalColor.red)
                    self.add_log(f'✗ {file_item.file_name} - 转换失败: {message}', 'ERROR')
                break

    def on_conversion_finished(self, results):
        """转换完成回调"""
        self.timer.stop()
        self.set_ui_enabled(True)
        
        # 更新按钮
        self.convert_btn.setText('🚀 开始转换')
        self.convert_btn.clicked.disconnect()
        self.convert_btn.clicked.connect(self.start_conversion)
        
        # 统计结果
        success_count = sum(1 for r in results if r.success)
        total_count = len(results)
        
        # 记录日志
        self.add_log('=' * 50)
        self.add_log(f'转换完成！成功: {success_count}/{total_count}')
        if self.conversion_start_time:
            elapsed = time.time() - self.conversion_start_time
            self.add_log(f'总用时: {elapsed:.1f}秒')
        self.add_log('=' * 50)
        
        if success_count == total_count:
            self.status_label.setText(f'✅ 全部完成！({success_count}/{total_count})')
            self.status_label.setStyleSheet('font-weight: bold; color: #67c23a;')
            QMessageBox.information(self, '完成', f'所有文件转换成功！\n共转换 {total_count} 个文件')
        elif success_count > 0:
            self.status_label.setText(f'⚠️ 部分完成 ({success_count}/{total_count})')
            self.status_label.setStyleSheet('font-weight: bold; color: #e6a23c;')
            QMessageBox.warning(self, '部分完成', f'部分文件转换成功。\n成功: {success_count}/{total_count}')
        else:
            self.status_label.setText(f'❌ 转换失败')
            self.status_label.setStyleSheet('font-weight: bold; color: #f56c6c;')
            QMessageBox.critical(self, '失败', '所有文件转换失败！')

    def on_conversion_cancelled(self):
        """转换取消回调"""
        self.timer.stop()
        self.set_ui_enabled(True)
        self.progress_bar.setValue(0)
        self.status_label.setText('⏹️ 已取消')
        self.status_label.setStyleSheet('font-weight: bold; color: #909399;')
        
        self.add_log('转换已取消', 'WARNING')
        
        self.convert_btn.setText('🚀 开始转换')
        self.convert_btn.clicked.disconnect()
        self.convert_btn.clicked.connect(self.start_conversion)

    def update_elapsed_time(self):
        """更新已用时间"""
        if self.conversion_start_time:
            elapsed = time.time() - self.conversion_start_time
            minutes = int(elapsed // 60)
            seconds = int(elapsed % 60)
            self.time_label.setText(f'⏱️ 已用时间: {minutes:02d}:{seconds:02d}')

    def set_ui_enabled(self, enabled):
        """设置UI启用/禁用状态"""
        self.add_files_btn.setEnabled(enabled)
        self.remove_files_btn.setEnabled(enabled)
        self.clear_files_btn.setEnabled(enabled)
        self.browse_output_btn.setEnabled(enabled)
        self.word_checkbox.setEnabled(enabled)
        self.markdown_checkbox.setEnabled(enabled)
        self.file_list.setEnabled(enabled)
        self.output_path_edit.setEnabled(enabled)
        self.clear_log_btn.setEnabled(enabled)
        
        # 遮罩效果
        if not enabled:
            self.centralWidget().setGraphicsEffect(self.overlay)
            self.overlay.setOpacity(0.7)
        else:
            self.centralWidget().setGraphicsEffect(None)
    
    def add_log(self, message: str, level: str = 'INFO'):
        """添加日志消息"""
        timestamp = datetime.now().strftime('%H:%M:%S')
        log_entry = f"[{timestamp}] [{level}] {message}"
        self.log_text.appendPlainText(log_entry)
        
        # 滚动到底部
        scrollbar = self.log_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
    
    def clear_log(self):
        """清空日志"""
        self.log_text.clear()
        self.add_log('日志已清空', 'INFO')
    
    def open_output_directory(self):
        """打开输出目录"""
        output_dir = self.output_path_edit.text()
        if not output_dir:
            # 如果没有指定输出目录，使用第一个PDF文件所在目录
            if self.file_items:
                output_dir = self.file_items[0].file_dir
        
        if output_dir and os.path.exists(output_dir):
            QDesktopServices.openUrl(QUrl.fromLocalFile(output_dir))
        else:
            QMessageBox.warning(self, '警告', '输出目录不存在！')
