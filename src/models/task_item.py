from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
from enum import Enum
import time


class TaskStatus(Enum):
    PENDING = "pending"      # 等待中
    RUNNING = "running"      # 转换中
    SUCCESS = "success"      # 成功
    FAILED = "failed"        # 失败
    CANCELLED = "cancelled"  # 已取消


@dataclass
class TaskItem:
    """转换任务项"""
    task_id: str                    # 任务唯一ID
    file_path: str                  # PDF文件路径
    status: TaskStatus = TaskStatus.PENDING
    output_word: Optional[str] = None
    error_message: Optional[str] = None
    
    # 时间统计
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    finished_at: Optional[float] = None
    
    # 输出设置
    output_dir: Optional[str] = None
    custom_filename: Optional[str] = None  # 自定义文件名（不含扩展名）
    
    @property
    def file_name(self) -> str:
        return Path(self.file_path).name
    
    @property
    def file_dir(self) -> str:
        return str(Path(self.file_path).parent)
    
    @property
    def base_name(self) -> str:
        """获取基础文件名（不含扩展名）"""
        return self.custom_filename if self.custom_filename else Path(self.file_path).stem
    
    @property
    def elapsed_time(self) -> float:
        """获取已用时间（秒）"""
        if self.started_at:
            if self.finished_at:
                return self.finished_at - self.started_at
            return time.time() - self.started_at
        return 0.0
    
    @property
    def elapsed_time_str(self) -> str:
        """获取格式化的时间字符串"""
        elapsed = self.elapsed_time
        if elapsed < 60:
            return f"{elapsed:.1f}秒"
        else:
            minutes = int(elapsed // 60)
            seconds = int(elapsed % 60)
            return f"{minutes}分{seconds}秒"
    
    def get_output_path(self, extension: str = ".docx") -> str:
        """获取输出文件路径（同名文件已存在时自动追加序号，避免静默覆盖）"""
        output_dir = self.output_dir if self.output_dir else self.file_dir
        path = Path(output_dir) / f"{self.base_name}{extension}"
        counter = 1
        while path.exists():
            path = Path(output_dir) / f"{self.base_name}({counter}){extension}"
            counter += 1
        return str(path)
    
    def start(self):
        """标记任务开始"""
        self.status = TaskStatus.RUNNING
        self.started_at = time.time()
    
    def finish(self, success: bool, error_msg: Optional[str] = None):
        """标记任务完成"""
        self.finished_at = time.time()
        if success:
            self.status = TaskStatus.SUCCESS
        else:
            self.status = TaskStatus.FAILED
            self.error_message = error_msg
    
    def cancel(self):
        """标记任务取消"""
        self.finished_at = time.time()
        self.status = TaskStatus.CANCELLED
