from typing import List, Optional
from PyQt6.QtCore import QThread, pyqtSignal

from src.models.file_item import FileItem, FileStatus
from src.core.converter import BatchConverter, ConversionResult


class ConverterWorker(QThread):
    """转换工作线程"""
    
    # 信号定义
    progress_updated = pyqtSignal(int, int, str)  # 当前进度, 总数, 状态信息
    file_started = pyqtSignal(FileItem)  # 文件开始转换
    file_finished = pyqtSignal(FileItem, bool, str)  # 文件, 是否成功, 消息
    conversion_finished = pyqtSignal(list)  # 所有结果列表
    conversion_cancelled = pyqtSignal()  # 转换被取消
    
    def __init__(
        self,
        file_items: List[FileItem],
        output_dir: Optional[str] = None,
        convert_to_word: bool = True,
        convert_to_markdown: bool = False
    ):
        super().__init__()
        self.file_items = file_items
        self.output_dir = output_dir
        self.convert_to_word = convert_to_word
        self.convert_to_markdown = convert_to_markdown
        
        self.batch_converter = None
        self.is_running = False
    
    def run(self):
        """执行转换"""
        self.is_running = True
        
        try:
            self.batch_converter = BatchConverter(
                output_dir=self.output_dir,
                convert_to_word=self.convert_to_word,
                convert_to_markdown=self.convert_to_markdown,
                progress_callback=self._on_progress,
                file_progress_callback=self._on_file_progress
            )
            
            results = self.batch_converter.convert_files(self.file_items)
            
            if self.batch_converter.is_cancelled:
                self.conversion_cancelled.emit()
            else:
                self.conversion_finished.emit(results)
                
        except Exception as e:
            # 发生异常时，标记所有未完成的任务为失败
            for item in self.file_items:
                if item.status == FileStatus.CONVERTING:
                    item.status = FileStatus.FAILED
                    item.error_message = str(e)
            self.conversion_finished.emit([])
        
        finally:
            self.is_running = False
    
    def _on_progress(self, current: int, total: int, status: str):
        """进度回调"""
        self.progress_updated.emit(current, total, status)
    
    def _on_file_progress(self, file_item: FileItem, status: str):
        """单个文件进度回调"""
        success = (status == "成功")
        message = file_item.error_message if not success else "转换成功"
        self.file_finished.emit(file_item, success, message)
    
    def cancel(self):
        """取消转换"""
        if self.batch_converter:
            self.batch_converter.cancel()
    
    def get_statistics(self) -> dict:
        """获取统计信息"""
        if self.batch_converter:
            return self.batch_converter.get_statistics()
        return {'total': 0, 'success': 0, 'failed': 0, 'success_rate': 0}
