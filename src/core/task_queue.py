"""
异步任务队列 (v7.0) — 无需 Redis/Celery

设计: 多线程 + 优先级队列, 解耦 UI / 数据 / 回测
"""

import threading, queue, time, uuid, traceback
from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable, Optional, Dict, Any
from enum import Enum


class TaskPriority(Enum):
    HIGH = 0
    NORMAL = 1
    LOW = 2


class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"


@dataclass
class Task:
    id: str
    name: str
    fn: Callable
    args: tuple = ()
    kwargs: dict = field(default_factory=dict)
    priority: TaskPriority = TaskPriority.NORMAL
    status: TaskStatus = TaskStatus.PENDING
    result: Any = None
    error: str = ""
    created_at: str = ""
    started_at: str = ""
    finished_at: str = ""


class TaskQueue:
    """轻量异步任务队列"""

    def __init__(self, workers: int = 3):
        self._queue = queue.PriorityQueue()
        self._workers = workers
        self._threads: list[threading.Thread] = []
        self._results: Dict[str, Task] = {}
        self._lock = threading.Lock()
        self._running = False

    def start(self):
        self._running = True
        for i in range(self._workers):
            t = threading.Thread(target=self._worker, name=f"TaskWorker-{i}",
                                daemon=True)
            t.start()
            self._threads.append(t)

    def stop(self):
        self._running = False

    _counter = 0

    def submit(self, name: str, fn: Callable, *args,
               priority: TaskPriority = TaskPriority.NORMAL,
               **kwargs) -> str:
        """提交任务, 返回 task_id"""
        task_id = str(uuid.uuid4())[:8]
        task = Task(
            id=task_id, name=name, fn=fn,
            args=args, kwargs=kwargs,
            priority=priority,
            created_at=datetime.now().strftime("%H:%M:%S"),
        )
        TaskQueue._counter += 1
        self._queue.put((task.priority.value, TaskQueue._counter, task))
        with self._lock:
            self._results[task_id] = task
        return task_id

    def submit_chain(self, tasks: list[tuple]) -> list:
        """
        链式提交: [(name1, fn1), (name2, fn2), ...]
        返回 task_id 列表
        """
        ids = []
        for name, fn in tasks:
            tid = self.submit(name, fn)
            ids.append(tid)
        return ids

    def get_result(self, task_id: str) -> Optional[Task]:
        with self._lock:
            return self._results.get(task_id)

    def wait(self, task_id: str, timeout: float = 60) -> Task:
        """等待任务完成"""
        deadline = time.time() + timeout
        while time.time() < deadline:
            task = self.get_result(task_id)
            if task and task.status in (TaskStatus.SUCCESS, TaskStatus.FAILED):
                return task
            time.sleep(0.1)
        return Task(id=task_id, name="timeout", fn=lambda: None,
                   status=TaskStatus.FAILED, error="超时")

    def status(self) -> dict:
        with self._lock:
            counts = {s: 0 for s in TaskStatus}
            for t in self._results.values():
                counts[t.status] = counts.get(t.status, 0) + 1
            return {
                "total": len(self._results),
                "by_status": {s.value: c for s, c in counts.items()},
                "queue_size": self._queue.qsize(),
                "workers": self._workers,
            }

    def _worker(self):
        while self._running:
            try:
                _, _, task = self._queue.get(timeout=1)
            except queue.Empty:
                continue

            task.status = TaskStatus.RUNNING
            task.started_at = datetime.now().strftime("%H:%M:%S")

            try:
                task.result = task.fn(*task.args, **task.kwargs)
                task.status = TaskStatus.SUCCESS
            except Exception as e:
                task.error = str(e)
                task.status = TaskStatus.FAILED
                traceback.print_exc()

            task.finished_at = datetime.now().strftime("%H:%M:%S")
            self._queue.task_done()


# 全局实例
task_queue = TaskQueue(workers=3)
task_queue.start()
