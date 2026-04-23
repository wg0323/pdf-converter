from typing import List, Optional, Callable
from pathlib import Path
import os

from src.models.file_item import FileItem, FileStatus
from src.core.pdf_to_word import PDFToWordConverter
from src.core.pdf_to_markdown import PDFToMarkdownConverter


class ConversionResult:
    def __init__(self, file_item: FileItem, success: bool, message: str):
        self.file_item = file_item
        self.success = success
        self.message = message


class BatchConverter:
    def __init__(
        self,
        output_dir: Optional[str] = None,
        convert_to_word: bool = True,
        convert_to_markdown: bool = False,
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
        file_progress_callback: Optional[Callable[[FileItem, str], None]] = None
    ):
        """
        批量转换器
        
        Args:
            output_dir: 输出目录（None表示使用PDF文件所在目录）
            convert_to_word: 是否转换为Word
            convert_to_markdown: 是否转换为Markdown
            progress_callback: 总体进度回调(current, total, status)
            file_progress_callback: 单个文件进度回调(file_item, status)
        """
        self.output_dir = output_dir
        self.convert_to_word = convert_to_word
        self.convert_to_markdown = convert_to_markdown
        self.progress_callback = progress_callback
        self.file_progress_callback = file_progress_callback
        
        self.word_converter = PDFToWordConverter()
        self.markdown_converter = PDFToMarkdownConverter()
        
        self.is_cancelled = False
        self.results: List[ConversionResult] = []
    
    def convert_files(self, file_items: List[FileItem]) -> List[ConversionResult]:
        """
        批量转换文件
        
        Args:
            file_items: 要转换的文件列表
            
        Returns:
            转换结果列表
        """
        self.results = []
        total = len(file_items)
        
        for index, file_item in enumerate(file_items):
            if self.is_cancelled:
                break
            
            # 更新总体进度
            if self.progress_callback:
                self.progress_callback(index + 1, total, f"正在转换: {file_item.file_name}")
            
            # 转换单个文件
            result = self._convert_single_file(file_item)
            self.results.append(result)
            
            # 文件进度回调
            if self.file_progress_callback:
                status = "成功" if result.success else "失败"
                self.file_progress_callback(file_item, status)
        
        # 完成回调
        if self.progress_callback and not self.is_cancelled:
            self.progress_callback(total, total, "转换完成")
        
        return self.results
    
    def _convert_single_file(self, file_item: FileItem) -> ConversionResult:
        """转换单个文件"""
        file_item.status = FileStatus.CONVERTING
        
        try:
            success_count = 0
            messages = []
            
            # 确定输出目录
            output_dir = self.output_dir if self.output_dir else file_item.file_dir
            
            # 转换为Word
            if self.convert_to_word:
                output_word = file_item.get_output_path(output_dir, ".docx")
                success, msg = self.word_converter.convert(
                    file_item.file_path,
                    output_word
                )
                if success:
                    file_item.output_word = output_word
                    success_count += 1
                messages.append(f"Word: {msg}")
                
                if self.is_cancelled:
                    file_item.status = FileStatus.FAILED
                    return ConversionResult(file_item, False, "用户取消")
            
            # 转换为Markdown
            if self.convert_to_markdown:
                output_md = file_item.get_output_path(output_dir, ".md")
                success, msg = self.markdown_converter.convert(
                    file_item.file_path,
                    output_md
                )
                if success:
                    file_item.output_markdown = output_md
                    success_count += 1
                messages.append(f"Markdown: {msg}")
                
                if self.is_cancelled:
                    file_item.status = FileStatus.FAILED
                    return ConversionResult(file_item, False, "用户取消")
            
            # 判断总结果
            total_conversions = (1 if self.convert_to_word else 0) + (1 if self.convert_to_markdown else 0)
            if success_count == total_conversions:
                file_item.status = FileStatus.SUCCESS
                return ConversionResult(file_item, True, "; ".join(messages))
            elif success_count > 0:
                file_item.status = FileStatus.SUCCESS
                return ConversionResult(file_item, True, f"部分成功 - {'; '.join(messages)}")
            else:
                file_item.status = FileStatus.FAILED
                return ConversionResult(file_item, False, "; ".join(messages))
                
        except Exception as e:
            file_item.status = FileStatus.FAILED
            file_item.error_message = str(e)
            return ConversionResult(file_item, False, f"转换异常: {str(e)}")
    
    def cancel(self):
        """取消转换"""
        self.is_cancelled = True
        self.word_converter.cancel()
    
    def get_statistics(self) -> dict:
        """获取转换统计信息"""
        total = len(self.results)
        success = sum(1 for r in self.results if r.success)
        failed = total - success
        
        return {
            'total': total,
            'success': success,
            'failed': failed,
            'success_rate': success / total if total > 0 else 0
        }
