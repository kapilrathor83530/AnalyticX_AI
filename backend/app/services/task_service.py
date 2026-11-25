import threading
import uuid
from typing import Any, Callable, Dict


_TASKS: Dict[str, Dict[str, Any]] = {}
_LOCK = threading.Lock()


def start_task(func: Callable, *args, **kwargs) -> str:
    task_id = uuid.uuid4().hex
    with _LOCK:
        _TASKS[task_id] = {"status": "pending", "result": None, "error": None}

    def runner():
        with _LOCK:
            _TASKS[task_id]["status"] = "running"
        try:
            result = func(*args, **kwargs)
            with _LOCK:
                _TASKS[task_id]["status"] = "done"
                _TASKS[task_id]["result"] = result
        except Exception as exc:
            with _LOCK:
                _TASKS[task_id]["status"] = "error"
                _TASKS[task_id]["error"] = str(exc)

    threading.Thread(target=runner, daemon=True).start()
    return task_id


def get_task(task_id: str) -> Dict[str, Any]:
    with _LOCK:
        return _TASKS.get(task_id) or {"status": "missing"}
