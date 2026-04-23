from PyQt6.QtCore import QThread, pyqtSignal
from typing import Optional

from src.models.task_item import TaskItem, TaskStatus
from src.core.pdf_to_word import PDFToWordConverter
from src.core.pdf_to_markdown import PDFToMarkdownConverter


class SingleTaskWorker(QThread):
    """单个任务的转换工作线程"""
    
    # 信号
    progress_updated = pyqtSignal(str, str)  # task_id, status_message
    task_finished = pyqtSignal(str, bool, str)  # task_id, success, message
    
    def __init__(self, task: TaskItem):
        super().__init__()
        self.task = task
        self.word_converter: Optional[PDFToWordConverter] = None
        self.markdown_converter: Optional[PDFToMarkdownConverter] = None
        self._is_cancelled = False
    
    def run(self):
        """执行任务"""
        self.task.start()
        self.progress_updated.emit(self.task.task_id, "开始转换...")
        
        try:
            # 只处理一种输出类型
            if self.task.output_type == "word":
                self._convert_to_word()
            elif self.task.output_type == "markdown":
                self._convert_to_markdown()
            else:
                self.task.finish(False, f"未知的输出类型: {self.task.output_type}")
                self.task_finished.emit(self.task.task_id, False, "未知输出类型")
                
        except Exception as e:
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
        if success:
            self.task.output_word = output_word
            self.progress_updated.emit(self.task.task_id, "Word转换完成")
            self.task.finish(True)
            self.task_finished.emit(self.task.task_id, True, "Word转换成功")
        else:
            self.progress_updated.emit(self.task.task_id, f"Word转换失败: {msg}")
            self.task.finish(False, msg)
            self.task_finished.emit(self.task.task_id, False, f"Word转换失败: {msg}")
    
    def _convert_to_markdown(self):
        """转换为Markdown"""
        self.progress_updated.emit(self.task.task_id, "正在转换为Markdown...")
        self.markdown_converter = PDFToMarkdownConverter()
        
        # 获取输出文件夹路径
        output_folder = self.task.get_markdown_folder_path()
        
        success, msg = self.markdown_converter.convert(
            self.task.file_path,
            output_folder,
            base_name=self.task.base_name
        )
        if success:
            self.task.output_markdown = output_folder
            self.progress_updated.emit(self.task.task_id, "Markdown转换完成")
            self.task.finish(True)
            self.task_finished.emit(self.task.task_id, True, "Markdown转换成功")
        else:
            self.progress_updated.emit(self.task.task_id, f"Markdown转换失败: {msg}")
            self.task.finish(False, msg)
            self.task_finished.emit(self.task.task_id, False, f"Markdown转换失败: {msg}")
    
    def cancel(self):
        """取消任务"""
        self._is_cancelled = True
        if self.word_converter:
            self.word_converter.cancel()
        if self.markdown_converter:
            if hasattr(self.markdown_converter, 'cancel'):
                self.markdown_converter.cancel()
