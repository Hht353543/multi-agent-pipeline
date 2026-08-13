"""Checkpoint：按 step 持久化流水线状态，支持失败恢复续跑。"""

from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any


class CheckpointStore:
    """JSON 文件型 checkpoint 存储（线程安全）。"""

    def __init__(self, directory: str | Path) -> None:
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

    def _path(self, run_id: str) -> Path:
        return self.directory / f"{run_id}.checkpoint.json"

    def save(self, run_id: str, state: dict[str, Any]) -> None:
        with self._lock:
            self._path(run_id).write_text(
                json.dumps(state, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

    def load(self, run_id: str) -> dict[str, Any] | None:
        path = self._path(run_id)
        with self._lock:
            if not path.exists():
                return None
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                return data if isinstance(data, dict) else None
            except (json.JSONDecodeError, OSError):
                return None

    def delete(self, run_id: str) -> None:
        with self._lock:
            path = self._path(run_id)
            if path.exists():
                path.unlink()

    def list_runs(self) -> list[str]:
        with self._lock:
            return sorted(
                p.stem.replace(".checkpoint", "")
                for p in self.directory.glob("*.checkpoint.json")
            )


__all__ = ["CheckpointStore"]
