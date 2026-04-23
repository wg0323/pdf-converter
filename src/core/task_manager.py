from typing import List, Dict, Optional, Callable
from PyQt6.QtCore import QObject, pyqtSignal
import uuid

from src.models.task_item import TaskItem, TaskStatus
from src.core.single_task_worker import SingleTaskWorker


class TaskManager(QObject):
    """任务管理器 - 管理多个并发转换任务"""
    
    # 信号
    task_added = pyqtSignal(str)           # task_id
    task_started = pyqtSignal(str)         # task_id
    task_progress = pyqtSignal(str, str)   # task_id, status_message
    task_finished = pyqtSignal(str, bool, str)  # task_id, success, message
    task_cancelled = pyqtSignal(str)       # task_id
    all_tasks_finished = pyqtSignal()      # 所有任务完成
    queue_updated = pyqtSignal(int, int)   # pending_count, running_count
    
    # 最大并发任务数限制
    MAX_CONCURRENT_TASKS = 3
    
    def __init__(self):
        super().__init__()
        self.tasks: Dict[str, TaskItem] = {}
        self.workers: Dict[str, SingleTaskWorker] = {}
        self.pending_queue: List[str] = []  # 等待中的任务ID队列
        self.running_tasks: set = set()      # 正在运行的任务ID
        self.completed_tasks: set = set()    # 已完成的任务ID
        self.is_running = False              # 是否正在批量处理
    
    def add_task(
        self,
        file_path: str,
        output_dir: Optional[str] = None,
        convert_to_word: bool = True,
        convert_to_markdown: bool = False,
        custom_filename: Optional[str] = None,
        output_type: str = "word"
    ) -> str:
        """
        添加新任务到队列（不立即启动）
        
        Returns:
            task_id: 任务唯一ID
        """
        task_id = str(uuid.uuid4())[:8]  # 生成短ID
        
        task = TaskItem(
            task_id=task_id,
            file_path=file_path,
            output_dir=output_dir,
            convert_to_word=convert_to_word,
            convert_to_markdown=convert_to_markdown,
            custom_filename=custom_filename,
            output_type=output_type
        )
        
        self.tasks[task_id] = task
        self.pending_queue.append(task_id)
        
        self.task_added.emit(task_id)
        self._update_queue_status()
        
        return task_id
    
    def update_task_filename(self, task_id: str, custom_filename: str):
        """更新任务的自定义文件名"""
        if task_id in self.tasks:
            self.tasks[task_id].custom_filename = custom_filename
    
    def start_all_pending(self):
        """启动所有等待中的任务"""
        self.is_running = True
        # 尝试启动任务，直到达到并发限制
        while self._try_start_next_task():
            pass
    
    def _try_start_next_task(self) -> bool:
        """尝试启动下一个等待中的任务"""
        # 检查是否已达到最大并发数
        if len(self.running_tasks) >= self.MAX_CONCURRENT_TASKS:
            return False
        
        # 从队列中取出一个任务
        while self.pending_queue:
            task_id = self.pending_queue.pop(0)
            task = self.tasks.get(task_id)
            
            if task and task.status == TaskStatus.PENDING:
                self._start_task(task_id)
                return True
        
        self._update_queue_status()
        return False
    
    def _start_task(self, task_id: str):
        """启动指定任务"""
        if task_id not in self.tasks:
            return
        
        task = self.tasks[task_id]
        
        # 创建工作线程
        worker = SingleTaskWorker(task)
        
        # 连接信号
        worker.progress_updated.connect(self._on_task_progress)
        worker.task_finished.connect(self._on_task_finished)
        
        # 保存并启动
        self.workers[task_id] = worker
        self.running_tasks.add(task_id)
        
        self.task_started.emit(task_id)
        worker.start()
    
    def _on_task_progress(self, task_id: str, status_message: str):
        """任务进度回调"""
        self.task_progress.emit(task_id, status_message)
    
    def _on_task_finished(self, task_id: str, success: bool, message: str):
        """任务完成回调"""
        if task_id in self.running_tasks:
            self.running_tasks.remove(task_id)
            self.completed_tasks.add(task_id)
        
        # 清理工作线程（修复内存泄漏）
        if task_id in self.workers:
            worker = self.workers[task_id]
            # 清理转换器对象，释放内存
            if hasattr(worker, 'word_converter') and worker.word_converter:
                worker.word_converter = None
            if hasattr(worker, 'markdown_converter') and worker.markdown_converter:
                worker.markdown_converter = None
            # 等待线程结束
            worker.wait(2000)  # 增加等待时间
            # 删除worker引用
            del self.workers[task_id]
            # 强制垃圾回收
            import gc
            gc.collect()
        
        self.task_finished.emit(task_id, success, message)
        self._update_queue_status()
        
        # 尝试启动下一个任务
        if self.is_running:
            self._try_start_next_task()
        
        # 检查是否所有任务都完成了
        if not self.pending_queue and not self.running_tasks:
            self.is_running = False
            self.all_tasks_finished.emit()
    
    def cancel_task(self, task_id: str) -> bool:
        """取消指定任务"""
        if task_id in self.pending_queue:
            # 任务还在等待队列中，直接移除
            self.pending_queue.remove(task_id)
            if task_id in self.tasks:
                self.tasks[task_id].cancel()
            self.task_cancelled.emit(task_id)
            self._update_queue_status()
            return True
        
        elif task_id in self.running_tasks and task_id in self.workers:
            # 任务正在运行，需要取消工作线程
            worker = self.workers[task_id]
            worker.cancel()
            worker.wait(2000)  # 等待2秒让线程结束
            
            if task_id in self.tasks:
                self.tasks[task_id].cancel()
            
            self.running_tasks.remove(task_id)
            self.completed_tasks.add(task_id)
            del self.workers[task_id]
            
            self.task_cancelled.emit(task_id)
            self._update_queue_status()
            
            # 尝试启动下一个任务
            if self.is_running:
                self._try_start_next_task()
            
            # 检查是否所有任务都完成了
            if not self.pending_queue and not self.running_tasks:
                self.is_running = False
                self.all_tasks_finished.emit()
            
            return True
        
        return False
    
    def cancel_all_tasks(self):
        """取消所有任务"""
        self.is_running = False
        # 取消等待中的任务
        for task_id in self.pending_queue[:]:
            self.pending_queue.remove(task_id)
            if task_id in self.tasks:
                self.tasks[task_id].cancel()
            self.task_cancelled.emit(task_id)
        
        # 取消正在运行的任务
        for task_id in list(self.running_tasks):
            if task_id in self.workers:
                worker = self.workers[task_id]
                worker.cancel()
        
        self._update_queue_status()
    
    def get_task(self, task_id: str) -> Optional[TaskItem]:
        """获取任务信息"""
        return self.tasks.get(task_id)
    
    def get_all_tasks(self) -> List[TaskItem]:
        """获取所有任务"""
        return list(self.tasks.values())
    
    def get_pending_count(self) -> int:
        """获取等待中任务数"""
        return len(self.pending_queue)
    
    def get_running_count(self) -> int:
        """获取运行中任务数"""
        return len(self.running_tasks)
    
    def get_completed_count(self) -> int:
        """获取已完成任务数"""
        return len(self.completed_tasks)
    
    def is_queue_full(self) -> bool:
        """检查队列是否已满（任务数是否超过限制）"""
        total_tasks = len(self.tasks)
        # 限制总任务数为20个
        return total_tasks >= 20
    
    def has_pending_tasks(self) -> bool:
        """检查是否有等待中的任务"""
        return len(self.pending_queue) > 0
    
    def has_running_tasks(self) -> bool:
        """检查是否有正在运行的任务"""
        return len(self.running_tasks) > 0
    
    def clear_completed_tasks(self):
        """清理已完成的任务"""
        for task_id in list(self.completed_tasks):
            if task_id in self.tasks:
                del self.tasks[task_id]
        self.completed_tasks.clear()
    
    def _update_queue_status(self):
        """更新队列状态信号"""
        self.queue_updated.emit(self.get_pending_count(), self.get_running_count())
