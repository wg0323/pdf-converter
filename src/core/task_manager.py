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
    task_log = pyqtSignal(str, str)        # task_id, 面向用户的日志文本
    all_tasks_finished = pyqtSignal()      # 所有任务完成
    queue_updated = pyqtSignal(int, int)   # pending_count, running_count
    
    # 最大并发任务数限制
    # 注意：底层转换库 pdf2docx / PyMuPDF(fitz) / PaddleOCR 均非线程安全，
    # 多个工作线程同时调用会触发C层崩溃（进程闪退）。因此串行执行，
    # 任务按队列逐个转换，从根本上避免原生库的并发访问。
    MAX_CONCURRENT_TASKS = 1
    
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
        custom_filename: Optional[str] = None
    ) -> str:
        """
        添加新任务到队列（不立即启动）

        Returns:
            task_id: 任务唯一ID
        """
        task_id = str(uuid.uuid4())[:12]  # 生成短ID（12字符降低碰撞风险）

        task = TaskItem(
            task_id=task_id,
            file_path=file_path,
            output_dir=output_dir,
            custom_filename=custom_filename
        )
        
        self.tasks[task_id] = task
        self.pending_queue.append(task_id)
        
        self.task_added.emit(task_id)
        self._update_queue_status()
        
        return task_id
    
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
        worker.log_message.connect(self._on_task_log)
        # 线程真正结束后再清理引用，避免运行中的QThread被GC销毁导致崩溃
        worker.finished.connect(lambda tid=task_id: self._cleanup_worker(tid))
        
        # 保存并启动
        self.workers[task_id] = worker
        self.running_tasks.add(task_id)
        
        self.task_started.emit(task_id)
        # 任务已从等待队列转入运行集合，立即刷新队列统计，
        # 否则界面会停留在"任务仍在等待中"的旧计数上
        self._update_queue_status()
        worker.start()
    
    def _cleanup_worker(self, task_id: str):
        """工作线程结束后的清理与调度（由 finished 信号触发，线程已安全退出）

        并发槽（running_tasks）的释放严格绑定线程生命周期：线程真正结束才移除，
        并在此之后再调度下一个任务。即便取消正在运行的任务，新任务也必须等旧线程
        退出才启动，从根本上杜绝两个线程并发 import/使用非线程安全的 paddle
        （并发导入会触发 paddle 内部循环导入并污染 sys.modules）。
        """
        worker = self.workers.pop(task_id, None)
        if worker is not None:
            # 释放转换器对象
            worker.word_converter = None
            worker.deleteLater()

        # 线程已退出，释放其占用的并发槽
        self.running_tasks.discard(task_id)
        self._update_queue_status()

        # 调度下一个等待中的任务（此刻已无其它工作线程在运行）
        if self.is_running:
            self._try_start_next_task()

        # 队列清空且无运行中线程，广播全部完成以恢复界面状态
        if not self.pending_queue and not self.running_tasks:
            self.is_running = False
            self.all_tasks_finished.emit()
    
    def _on_task_progress(self, task_id: str, status_message: str):
        """任务进度回调"""
        self.task_progress.emit(task_id, status_message)
    
    def _on_task_log(self, task_id: str, message: str):
        """任务日志回调（透传扫描版检测/OCR状态至界面）"""
        self.task_log.emit(task_id, message)
    
    def _on_task_finished(self, task_id: str, success: bool, message: str):
        """任务完成回调（业务层）：仅更新完成状态并向界面广播。

        并发槽释放与下一个任务的调度统一由 _cleanup_worker（线程真正结束后）
        负责，确保任意时刻至多一个工作线程在运行，杜绝并发导入 paddle。
        """
        self.completed_tasks.add(task_id)
        self.task_finished.emit(task_id, success, message)
        self._update_queue_status()
    
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
            # 任务正在运行：仅通知工作线程协作式取消，不在此释放并发槽、
            # 也不立即调度下一个任务。旧线程此刻可能仍在 import/使用 paddle，
            # 必须等它 finished 后由 _cleanup_worker 释放并发槽并启动下一个，
            # 否则新旧线程会并发导入 paddle 触发循环导入并污染 sys.modules。
            worker = self.workers[task_id]
            worker.cancel()

            if task_id in self.tasks:
                self.tasks[task_id].cancel()

            self.completed_tasks.add(task_id)
            self.task_cancelled.emit(task_id)
            self._update_queue_status()
            return True
        
        return False

    def remove_task(self, task_id: str) -> bool:
        """
        从队列中移除等待中的任务（不标记为取消）

        Args:
            task_id: 任务ID

        Returns:
            是否成功移除
        """
        if task_id in self.pending_queue:
            self.pending_queue.remove(task_id)
            if task_id in self.tasks:
                del self.tasks[task_id]
            self._update_queue_status()
            return True
        return False

    def cancel_all_tasks(self):
        """取消所有任务（不阻塞等待线程结束）"""
        self.is_running = False
        # 取消等待中的任务
        for task_id in self.pending_queue[:]:
            self.pending_queue.remove(task_id)
            if task_id in self.tasks:
                self.tasks[task_id].cancel()
            self.task_cancelled.emit(task_id)
        
        # 取消正在运行的任务（协作式，与 cancel_task 行为一致）
        for task_id in list(self.running_tasks):
            if task_id in self.workers:
                self.workers[task_id].cancel()
            if task_id in self.tasks:
                self.tasks[task_id].cancel()
            self.completed_tasks.add(task_id)
            self.task_cancelled.emit(task_id)

        self.running_tasks.clear()
        self._update_queue_status()

    def wait_all_workers(self, timeout_ms: int = 5000):
        """
        等待所有工作线程结束（仅供退出程序时调用）

        必须在进程退出前确保线程结束，否则运行中的QThread
        被销毁会导致崩溃。
        """
        for worker in list(self.workers.values()):
            if not worker.wait(timeout_ms):
                # 协作式取消未在超时内生效（如 OCR 单页推理耗时较长），
                # 强制终止线程兑底，避免仍在运行的 QThread 被销毁
                # 触发 Qt 致命崩溃（qFatal）
                worker.terminate()
                worker.wait(2000)
    
    def has_active_duplicate(self, file_path: str, output_dir: Optional[str]) -> bool:
        """检查是否已存在相同源文件与输出目录的未完成任务（避免并发写同一输出文件）"""
        for task in self.tasks.values():
            if (task.file_path == file_path and task.output_dir == output_dir
                    and task.status in (TaskStatus.PENDING, TaskStatus.RUNNING)):
                return True
        return False
    
    def update_pending_output_dir(self, output_dir: Optional[str]):
        """将新的输出目录同步到所有等待中的任务

        输出目录在添加任务时快照进 TaskItem，若用户先添加文件、后选目录，
        需要把新目录同步到已入队但尚未开始的任务，否则配置不生效。
        运行中/已完成任务的输出路径已确定，不做修改。
        """
        for task in self.tasks.values():
            if task.status == TaskStatus.PENDING:
                task.output_dir = output_dir
    
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
