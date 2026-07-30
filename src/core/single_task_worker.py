from PyQt6.QtCore import QThread, pyqtSignal
from typing import Optional

from src.models.task_item import TaskItem, TaskStatus
from src.core.pdf_to_word import PDFToWordConverter


class SingleTaskWorker(QThread):
    """单个任务的转换工作线程"""
    
    # 信号
    progress_updated = pyqtSignal(str, str)  # task_id, status_message
    task_finished = pyqtSignal(str, bool, str)  # task_id, success, message
    
    def __init__(self, task: TaskItem):
        super().__init__()
        self.task = task
        self.word_converter: Optional[PDFToWordConverter] = None
        self._is_cancelled = False
    
    def run(self):
        """执行任务"""
        # 任务启动前已被取消，直接结束
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
        self.word_converter = PDFToWordConverter()
        output_word = self.task.get_output_path(".docx")
        success, msg = self.word_converter.convert(
            self.task.file_path,
            output_word
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
        self._is_cancelled = True
        if self.word_converter:
            self.word_converter.cancel()
