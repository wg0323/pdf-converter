import os
import sys
import time
from datetime import datetime
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QTableWidget, QTableWidgetItem, QCheckBox,
    QLabel, QFileDialog, QGroupBox, QMessageBox,
    QLineEdit, QAbstractItemView, QPlainTextEdit,
    QHeaderView
)
from PyQt6.QtCore import Qt, QTimer, QUrl
from PyQt6.QtGui import QDragEnterEvent, QDropEvent, QDesktopServices, QIcon, QPixmap

from src.models.task_item import TaskItem, TaskStatus
from src.core.task_manager import TaskManager


def _get_resource_dir() -> str:
    """获取资源目录路径（兼容开发环境和PyInstaller打包环境）"""
    if getattr(sys, 'frozen', False):
        # PyInstaller 打包环境
        base_dir = sys._MEIPASS
    else:
        # 开发环境
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(
            os.path.abspath(__file__))))
    return os.path.join(base_dir, 'resources', 'icons')





class MainWindow(QMainWindow):
    """主窗口 - 使用任务队列管理"""
    
    # 图标资源路径
    ICON_DIR = _get_resource_dir()
    
    def __init__(self):
        super().__init__()
        self.task_manager = TaskManager()
        self._is_converting = False
        self.setup_task_manager_signals()
        self.init_ui()
        self.setup_connections()
        self.apply_style()
        
        # 定时刷新任务列表
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.refresh_task_list)
        self.refresh_timer.start(500)  # 每500ms刷新一次
    
    def _load_icon(self, name: str) -> QIcon:
        """加载资源图标"""
        path = os.path.join(self.ICON_DIR, name)
        if os.path.exists(path):
            return QIcon(path)
        return QIcon()
    
    def setup_task_manager_signals(self):
        """连接任务管理器信号"""
        self.task_manager.task_added.connect(self.on_task_added)
        self.task_manager.task_started.connect(self.on_task_started)
        self.task_manager.task_progress.connect(self.on_task_progress)
        self.task_manager.task_finished.connect(self.on_task_finished)
        self.task_manager.task_cancelled.connect(self.on_task_cancelled)
        self.task_manager.all_tasks_finished.connect(self.on_all_tasks_finished)
        self.task_manager.queue_updated.connect(self.on_queue_updated)
    
    def init_ui(self):
        self.setWindowTitle('PDF转换器 v2.0')
        self.resize(1100, 800)
        self.setAcceptDrops(True)
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(12)
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        self.setup_control_section(main_layout)
        self.setup_task_list_section(main_layout)
        self.setup_log_section(main_layout)
    
    def setup_control_section(self, parent_layout):
        """控制面板"""
        control_group = QGroupBox('转换设置')
        control_layout = QVBoxLayout(control_group)
        
        # 第一行：文件操作和格式选择
        row1_layout = QHBoxLayout()
        
        # 文件操作按钮 - 使用 add.png 图标
        self.add_files_btn = QPushButton(' 添加 PDF 文件')
        self.add_files_btn.setIcon(self._load_icon('add.png'))
        self.add_files_btn.setObjectName('primary')
        row1_layout.addWidget(self.add_files_btn)
        
        # 删除选中任务按钮
        self.remove_selected_btn = QPushButton(' 删除选中')
        self.remove_selected_btn.setIcon(self._load_icon('delete.png'))
        self.remove_selected_btn.setEnabled(False)
        row1_layout.addWidget(self.remove_selected_btn)
        
        # 格式选择 - 仅 Word
        row1_layout.addWidget(QLabel('输出格式:'))
        self.word_checkbox = QCheckBox('Word (.docx)')
        self.word_checkbox.setChecked(True)
        row1_layout.addWidget(self.word_checkbox)
        
        row1_layout.addStretch()
        control_layout.addLayout(row1_layout)
        
        # 第二行：输出目录
        row2_layout = QHBoxLayout()
        row2_layout.addWidget(QLabel('输出目录:'))
        self.output_path_edit = QLineEdit()
        self.output_path_edit.setReadOnly(True)
        self.output_path_edit.setPlaceholderText('默认：与PDF文件相同目录')
        row2_layout.addWidget(self.output_path_edit)
        
        self.browse_output_btn = QPushButton(' 浏览')
        self.browse_output_btn.setIcon(self._load_icon('open.png'))
        row2_layout.addWidget(self.browse_output_btn)
        control_layout.addLayout(row2_layout)
        
        # 第三行：队列状态和开始按钮
        row3_layout = QHBoxLayout()
        self.queue_status_label = QLabel('队列: 等待中 0 | 运行中 0 | 已完成 0')
        self.queue_status_label.setStyleSheet('color: #409eff; font-weight: bold;')
        row3_layout.addWidget(self.queue_status_label)
        row3_layout.addStretch()
        
        # 开始转换按钮 - 使用 start.png 图标
        self.start_convert_btn = QPushButton(' 开始转换')
        self.start_convert_btn.setIcon(self._load_icon('start.png'))
        self.start_convert_btn.setObjectName('primary')
        self.start_convert_btn.setMinimumWidth(150)
        self.start_convert_btn.setEnabled(False)
        row3_layout.addWidget(self.start_convert_btn)
        
        # 清理已完成按钮
        self.clear_completed_btn = QPushButton(' 清理已完成')
        self.clear_completed_btn.setEnabled(False)
        row3_layout.addWidget(self.clear_completed_btn)
        
        # 打开输出目录按钮 - 使用 open.png 图标
        self.open_output_dir_btn = QPushButton(' 打开输出目录')
        self.open_output_dir_btn.setIcon(self._load_icon('open.png'))
        self.open_output_dir_btn.setEnabled(False)
        row3_layout.addWidget(self.open_output_dir_btn)
        
        control_layout.addLayout(row3_layout)
        
        parent_layout.addWidget(control_group)
    
    def setup_task_list_section(self, parent_layout):
        """任务列表"""
        task_group = QGroupBox('任务列表')
        task_layout = QVBoxLayout(task_group)
        
        # 提示标签
        hint_label = QLabel('提示：选中任务后可点击"删除选中"移除')
        hint_label.setStyleSheet('color: #909399; font-size: 12px;')
        task_layout.addWidget(hint_label)
        
        # 任务表格 - 3 列：任务名、状态、用时
        self.task_table = QTableWidget()
        self.task_table.setColumnCount(3)
        self.task_table.setHorizontalHeaderLabels([
            '任务名', '状态', '用时'
        ])
        self.task_table.horizontalHeader().setStretchLastSection(False)
        self.task_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.task_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        self.task_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        self.task_table.setColumnWidth(1, 100)
        self.task_table.setColumnWidth(2, 100)
        self.task_table.setMinimumHeight(300)
        self.task_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.task_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.task_table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        
        # 连接选择变化信号，用于更新删除按钮状态
        self.task_table.itemSelectionChanged.connect(self.on_selection_changed)
        
        task_layout.addWidget(self.task_table)
        
        parent_layout.addWidget(task_group)
    
    def setup_log_section(self, parent_layout):
        """日志区域"""
        log_group = QGroupBox('转换日志')
        log_layout = QVBoxLayout(log_group)
        
        self.log_text = QPlainTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumBlockCount(1000)
        self.log_text.setPlaceholderText('转换日志将显示在这里...')
        self.log_text.setMaximumHeight(150)
        log_layout.addWidget(self.log_text)
        
        log_button_layout = QHBoxLayout()
        self.clear_log_btn = QPushButton('清空日志')
        log_button_layout.addWidget(self.clear_log_btn)
        log_button_layout.addStretch()
        log_layout.addLayout(log_button_layout)
        
        parent_layout.addWidget(log_group)
    
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
        """)
    
    def setup_connections(self):
        """连接信号"""
        self.add_files_btn.clicked.connect(self.add_files)
        self.remove_selected_btn.clicked.connect(self.remove_selected_tasks)
        self.browse_output_btn.clicked.connect(self.browse_output_directory)
        self.start_convert_btn.clicked.connect(self.start_conversion)
        self.clear_log_btn.clicked.connect(self.clear_log)
        self.clear_completed_btn.clicked.connect(self.clear_completed_tasks)
        self.open_output_dir_btn.clicked.connect(self.open_output_directory)
    
    def _set_converting_state(self, is_converting: bool):
        """
        设置转换状态，控制按钮可用性
        
        转换进行中：禁用添加文件、删除选中、开始转换按钮
        转换完成后：恢复按钮可用性
        
        Args:
            is_converting: 是否正在转换中
        """
        self._is_converting = is_converting
        self.add_files_btn.setEnabled(not is_converting)
        self.start_convert_btn.setEnabled(not is_converting and self.task_manager.has_pending_tasks())
        self.remove_selected_btn.setEnabled(not is_converting and len(self.task_table.selectedItems()) > 0)
    
    def add_files(self):
        """添加文件"""
        # 转换进行中不允许添加
        if self._is_converting:
            return
        
        # 检查队列是否已满
        if self.task_manager.is_queue_full():
            QMessageBox.warning(self, '警告', '任务队列已满（最多20个任务），请等待部分任务完成后再添加。')
            return
        
        files, _ = QFileDialog.getOpenFileNames(
            self, '选择PDF文件', '', 'PDF文件 (*.pdf)'
        )
        
        if not files:
            return
        
        # 检查格式选择
        convert_to_word = self.word_checkbox.isChecked()
        
        if not convert_to_word:
            QMessageBox.warning(self, '警告', '请选择输出格式！')
            return
        
        output_dir = self.output_path_edit.text() or None
        
        added_count = 0
        for file_path in files:
            # 检查是否已达到任务上限
            if self.task_manager.is_queue_full():
                QMessageBox.warning(self, '警告', f'已添加 {added_count} 个任务，队列已满。')
                break
            
            self.task_manager.add_task(
                file_path=file_path,
                output_dir=output_dir,
                convert_to_word=True,
                convert_to_markdown=False,
                output_type="word"
            )
            added_count += 1
        
        if added_count > 0:
            self.add_log(f'已添加 {added_count} 个任务到转换队列（Word 格式）')
            self.start_convert_btn.setEnabled(True)
            self.open_output_dir_btn.setEnabled(True)
    
    def on_selection_changed(self):
        """任务列表选择变化时更新删除按钮状态"""
        if self._is_converting:
            return
        selected_rows = set()
        for item in self.task_table.selectedItems():
            selected_rows.add(item.row())
        # 只有选中了等待中的任务才能删除
        has_removable = False
        for row in selected_rows:
            item = self.task_table.item(row, 0)
            if item:
                task_id = item.data(Qt.ItemDataRole.UserRole)
                if task_id:
                    task = self.task_manager.get_task(task_id)
                    if task and task.status == TaskStatus.PENDING:
                        has_removable = True
                        break
        self.remove_selected_btn.setEnabled(has_removable)
    
    def remove_selected_tasks(self):
        """删除选中的等待中任务"""
        if self._is_converting:
            return
        
        rows_to_remove = []
        selected_rows = set()
        for item in self.task_table.selectedItems():
            selected_rows.add(item.row())
        
        for row in selected_rows:
            item = self.task_table.item(row, 0)
            if item:
                task_id = item.data(Qt.ItemDataRole.UserRole)
                if task_id:
                    task = self.task_manager.get_task(task_id)
                    # 只能删除等待中的任务
                    if task and task.status == TaskStatus.PENDING:
                        rows_to_remove.append(row)
                        # 从任务管理器中移除
                        if task_id in self.task_manager.pending_queue:
                            self.task_manager.pending_queue.remove(task_id)
                        if task_id in self.task_manager.tasks:
                            del self.task_manager.tasks[task_id]
                        self.add_log(f'已删除任务: {task.file_name}')
        
        # 按行号倒序删除，避免索引变化
        for row in sorted(rows_to_remove, reverse=True):
            self.task_table.removeRow(row)
        
        self.remove_selected_btn.setEnabled(False)
        
        # 如果没有等待中的任务了，禁用开始按钮
        if not self.task_manager.has_pending_tasks() and self.task_table.rowCount() == 0:
            self.start_convert_btn.setEnabled(False)
    
    def browse_output_directory(self):
        """选择输出目录"""
        directory = QFileDialog.getExistingDirectory(self, '选择输出目录', '')
        if directory:
            self.output_path_edit.setText(directory)
    
    def start_conversion(self):
        """开始转换所有等待中的任务"""
        if self._is_converting:
            return
        
        if not self.task_manager.has_pending_tasks():
            QMessageBox.information(self, '提示', '没有等待中的任务')
            return
        
        # 清空日志区
        self.log_text.clear()
        
        self.add_log('=' * 50)
        self.add_log('开始批量转换')
        self.add_log(f'待转换任务数: {self.task_manager.get_pending_count()}')
        self.add_log('=' * 50)
        
        # 禁用相关按钮，防止转换期间操作
        self._set_converting_state(True)
        self.start_convert_btn.setText(' 转换中...')
        
        # 启动所有等待中的任务
        self.task_manager.start_all_pending()
    
    def open_output_directory(self):
        """打开输出目录"""
        output_dir = self.output_path_edit.text()
        if not output_dir:
            # 获取第一个任务的输出目录
            tasks = self.task_manager.get_all_tasks()
            if tasks:
                output_dir = tasks[0].file_dir
        
        if output_dir and os.path.exists(output_dir):
            QDesktopServices.openUrl(QUrl.fromLocalFile(output_dir))
        else:
            QMessageBox.warning(self, '警告', '输出目录不存在！')
    
    # ============ 任务管理器回调 ============
    
    def on_task_added(self, task_id: str):
        """任务添加回调 - 新任务插入到第一行"""
        task = self.task_manager.get_task(task_id)
        if not task:
            return
        
        # 插入到第一行（最新任务排最前）
        row = 0
        self.task_table.insertRow(row)
        
        # 任务名 + 输出类型（不可编辑）
        type_text = "Word"
        display_name = f"{task.file_name} → {type_text}"
        name_item = QTableWidgetItem(display_name)
        name_item.setFlags(name_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        name_item.setData(Qt.ItemDataRole.UserRole, task_id)  # 存储 task_id
        name_item.setData(Qt.ItemDataRole.UserRole + 1, type_text)  # 存储原始输出类型
        self.task_table.setItem(row, 0, name_item)
        
        # 状态
        status_item = QTableWidgetItem('等待中')
        status_item.setForeground(Qt.GlobalColor.gray)
        self.task_table.setItem(row, 1, status_item)
        
        # 用时
        self.task_table.setItem(row, 2, QTableWidgetItem('-'))
        
        self.add_log(f'添加任务：{task.file_name} → {type_text}')
    
    def on_task_started(self, task_id: str):
        """任务开始回调"""
        self.update_task_row(task_id)
        task = self.task_manager.get_task(task_id)
        if task:
            self.add_log(f'开始转换: {task.file_name}')
    
    def on_task_progress(self, task_id: str, message: str):
        """任务进度回调"""
        self.update_task_row(task_id)
    
    def on_task_finished(self, task_id: str, success: bool, message: str):
        """任务完成回调"""
        self.update_task_row(task_id)
        task = self.task_manager.get_task(task_id)
        if task:
            if success:
                self.add_log(f'完成: {task.file_name} - 用时 {task.elapsed_time_str}')
            else:
                self.add_log(f'失败: {task.file_name} - {message}', 'ERROR')
        
        self.clear_completed_btn.setEnabled(True)
    
    def on_task_cancelled(self, task_id: str):
        """任务取消回调"""
        self.update_task_row(task_id)
        task = self.task_manager.get_task(task_id)
        if task:
            self.add_log(f'已取消: {task.file_name}', 'WARNING')
    
    def on_all_tasks_finished(self):
        """所有任务完成回调"""
        self.add_log('=' * 50)
        self.add_log('所有任务已完成！')
        
        # 统计
        tasks = self.task_manager.get_all_tasks()
        success_count = sum(1 for t in tasks if t.status == TaskStatus.SUCCESS)
        total = len([t for t in tasks if t.status != TaskStatus.CANCELLED])
        self.add_log(f'统计: 成功 {success_count}/{total}')
        
        # 恢复按钮状态
        self._set_converting_state(False)
        self.start_convert_btn.setText(' 开始转换')
        self.start_convert_btn.setEnabled(self.task_manager.has_pending_tasks())
    
    def on_queue_updated(self, pending: int, running: int):
        """队列状态更新"""
        completed = self.task_manager.get_completed_count()
        self.queue_status_label.setText(
            f'队列: 等待中 {pending} | 运行中 {running} | 已完成 {completed}'
        )
        
        # 仅在非转换状态下更新开始按钮状态
        if not self._is_converting:
            has_pending = pending > 0
            self.start_convert_btn.setEnabled(has_pending)
            if not has_pending:
                self.start_convert_btn.setText(' 开始转换')
    
    def update_task_row(self, task_id: str):
        """更新任务行显示，已完成的任务移到后面"""
        row = -1
        for i in range(self.task_table.rowCount()):
            item = self.task_table.item(i, 0)
            if item and item.data(Qt.ItemDataRole.UserRole) == task_id:
                row = i
                break
        
        if row < 0:
            return
        
        task = self.task_manager.get_task(task_id)
        if not task:
            return
        
        # 更新状态 - 显示"转换中"、"失败"、"完成"
        if task.status == TaskStatus.RUNNING:
            status_text = '转换中'
            status_color = Qt.GlobalColor.blue
        elif task.status == TaskStatus.SUCCESS:
            status_text = '完成'
            status_color = Qt.GlobalColor.darkGreen
        elif task.status == TaskStatus.FAILED:
            status_text = '失败'
            status_color = Qt.GlobalColor.red
        elif task.status == TaskStatus.CANCELLED:
            status_text = '取消'
            status_color = Qt.GlobalColor.gray
        else:  # PENDING
            status_text = '等待中'
            status_color = Qt.GlobalColor.gray
        
        status_item = QTableWidgetItem(status_text)
        status_item.setForeground(status_color)
        self.task_table.setItem(row, 1, status_item)
        
        # 更新用时
        if task.status in [TaskStatus.RUNNING, TaskStatus.SUCCESS, TaskStatus.FAILED, TaskStatus.CANCELLED]:
            self.task_table.setItem(row, 2, QTableWidgetItem(task.elapsed_time_str))
        
        # 任务完成后移到表格底部
        if task.status in [TaskStatus.SUCCESS, TaskStatus.FAILED, TaskStatus.CANCELLED]:
            self._move_row_to_bottom(row)
    
    def _move_row_to_bottom(self, source_row: int):
        """将指定行移动到表格底部"""
        target_row = self.task_table.rowCount() - 1
        if source_row == target_row or source_row < 0:
            return

        # 先保存该行所有单元格的数据
        row_data = []
        for col in range(self.task_table.columnCount()):
            item = self.task_table.item(source_row, col)
            if item:
                new_item = QTableWidgetItem(item.text())
                new_item.setFlags(item.flags())
                # 复制 UserRole 数据
                data = item.data(Qt.ItemDataRole.UserRole)
                if data:
                    new_item.setData(Qt.ItemDataRole.UserRole, data)
                data2 = item.data(Qt.ItemDataRole.UserRole + 1)
                if data2:
                    new_item.setData(Qt.ItemDataRole.UserRole + 1, data2)
                # 复制前景色
                if item.foreground():
                    new_item.setForeground(item.foreground())
                row_data.append(new_item)
            else:
                row_data.append(None)

        # 阻止信号，避免 cellChanged 触发
        self.task_table.blockSignals(True)
        # 先插入新行到底部
        self.task_table.insertRow(self.task_table.rowCount())
        # 将数据填入新行
        new_row = self.task_table.rowCount() - 1
        for col, item in enumerate(row_data):
            if item:
                self.task_table.setItem(new_row, col, item)
        # 删除旧行
        self.task_table.removeRow(source_row)
        self.task_table.blockSignals(False)
    
    def clear_completed_tasks(self):
        """清理已完成的任务"""
        rows_to_remove = []
        for i in range(self.task_table.rowCount() - 1, -1, -1):
            item = self.task_table.item(i, 0)
            if item:
                task_id = item.data(Qt.ItemDataRole.UserRole)
                if task_id:
                    task = self.task_manager.get_task(task_id)
                    if task and task.status in [TaskStatus.SUCCESS, TaskStatus.FAILED, TaskStatus.CANCELLED]:
                        rows_to_remove.append(i)
        
        for row in rows_to_remove:
            self.task_table.removeRow(row)
        
        self.task_manager.clear_completed_tasks()
        self.clear_completed_btn.setEnabled(False)
        self.add_log('已清理已完成的任务')
        
        # 如果没有任务了，禁用开始按钮
        if self.task_table.rowCount() == 0:
            self.start_convert_btn.setEnabled(False)
    
    def refresh_task_list(self):
        """刷新任务列表（更新运行中任务的用时）"""
        for i in range(self.task_table.rowCount()):
            item = self.task_table.item(i, 0)
            if item:
                task_id = item.data(Qt.ItemDataRole.UserRole)
                if task_id:
                    task = self.task_manager.get_task(task_id)
                    if task and task.status == TaskStatus.RUNNING:
                        self.task_table.setItem(i, 2, QTableWidgetItem(task.elapsed_time_str))
    
    # ============ 其他方法 ============
    
    def dragEnterEvent(self, event: QDragEnterEvent):
        if self._is_converting:
            return
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
    
    def dropEvent(self, event: QDropEvent):
        """拖拽添加文件"""
        if self._is_converting:
            return
        
        if self.task_manager.is_queue_full():
            QMessageBox.warning(self, '警告', '任务队列已满，请等待部分任务完成后再添加。')
            return
        
        files = [url.toLocalFile() for url in event.mimeData().urls()]
        pdf_files = [f for f in files if f.lower().endswith('.pdf')]
        
        if not pdf_files:
            return
        
        convert_to_word = self.word_checkbox.isChecked()
        output_dir = self.output_path_edit.text() or None
        
        if not convert_to_word:
            QMessageBox.warning(self, '警告', '请选择输出格式！')
            return
        
        added_count = 0
        for file_path in pdf_files:
            if self.task_manager.is_queue_full():
                QMessageBox.warning(self, '警告', f'已添加 {added_count} 个任务，队列已满。')
                break
            
            self.task_manager.add_task(
                file_path=file_path,
                output_dir=output_dir,
                convert_to_word=True,
                convert_to_markdown=False,
                output_type="word"
            )
            added_count += 1
        
        if added_count > 0:
            self.add_log(f'通过拖拽添加 {added_count} 个任务（Word 格式）')
            self.start_convert_btn.setEnabled(True)
            self.open_output_dir_btn.setEnabled(True)
    
    def add_log(self, message: str, level: str = 'INFO'):
        """添加日志"""
        timestamp = datetime.now().strftime('%H:%M:%S')
        log_entry = f"[{timestamp}] [{level}] {message}"
        self.log_text.appendPlainText(log_entry)
        scrollbar = self.log_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
    
    def clear_log(self):
        """清空日志"""
        self.log_text.clear()
        self.add_log('日志已清空')
    
    def closeEvent(self, event):
        """关闭窗口时取消所有任务"""
        if self.task_manager.has_running_tasks():
            reply = QMessageBox.question(
                self, '确认',
                '还有任务正在运行，确定要退出吗？',
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.No:
                event.ignore()
                return
        
        self.task_manager.cancel_all_tasks()
        self.refresh_timer.stop()
        event.accept()
