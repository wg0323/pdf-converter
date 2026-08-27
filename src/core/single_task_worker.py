import threading

from PyQt6.QtCore import QThread, pyqtSignal
from typing import Optional

from src.models.task_item import TaskItem, TaskStatus
from src.core.pdf_to_word import PDFToWordConverter


class SingleTaskWorker(QThread):
    """单个任务的转换工作线程"""
    
    # 信号
    progress_updated = pyqtSignal(str, str)  # task_id, status_message
    task_finished = pyqtSignal(str, bool, str)  # task_id, success, message
    log_message = pyqtSignal(str, str)  # task_id, 面向用户的日志文本
    
    def __init__(self, task: TaskItem):
        super().__init__()
        self.task = task
        self.word_converter: Optional[PDFToWordConverter] = None
        self._is_cancelled = False
        # 保护“检查取消标志”与“发布 word_converter”的配对原子性，
        # 消除取消请求因赋值时序窗口而丢失的竞态
        self._cancel_lock = threading.Lock()
    
    def run(self):
        """执行任务"""
        # 任务启动前已被取消，直接结束。
        # task.start() 与取消标志同锁，避免取消后被迟到的 start()
        # 覆盖回 RUNNING 状态
        with self._cancel_lock:
            if self._is_cancelled:
                return
            self.task.start()

        self.progress_updated.emit(self.task.task_id, "开始转换...")
        
        try:
            self._convert_to_word()
        except Exception as e:
            if self._is_cancelled:
                return
            self.task.finish(False, str(e))
            self.task_finished.emit(self.task.task_id, False, f"转换异常: {str(e)}")
    
    def _convert_to_word(self):
        """转换为Word"""
        self.progress_updated.emit(self.task.task_id, "正在转换为Word...")
        converter = PDFToWordConverter()
        # 在锁内检查取消并发布 converter：取消已到则不再启动转换，
        # 确保 cancel() 一定能拿到 converter 去终止 pdf2docx 子进程
        with self._cancel_lock:
            if self._is_cancelled:
                return
            self.word_converter = converter
        output_word = self.task.get_output_path(".docx")
        success, msg = converter.convert(
            self.task.file_path,
            output_word,
            log_callback=lambda m: self.log_message.emit(self.task.task_id, m)
        )
        # 被取消的任务状态由 TaskManager 维护，此处不再覆盖、不再发完成信号
        if self._is_cancelled:
            return
        if success:
            self.task.output_word = output_word
            self.progress_updated.emit(self.task.task_id, "Word转换完成")
            self.task.finish(True)
            self.task_finished.emit(self.task.task_id, True, "Word转换成功")
        else:
            self.progress_updated.emit(self.task.task_id, f"Word转换失败: {msg}")
            self.task.finish(False, msg)
            self.task_finished.emit(self.task.task_id, False, f"Word转换失败: {msg}")
    
    def cancel(self):
        """取消任务（协作式，仅设置标志位，线程安全）"""
        with self._cancel_lock:
            self._is_cancelled = True
            converter = self.word_converter
        if converter:
            converter.cancel()
