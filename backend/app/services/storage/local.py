"""
本地文件系统存储后端。
- 写入 base_dir 下的子目录（按年/月分桶，避免单目录文件过多）
- 通过 FastAPI StaticFiles 对外暴露 url_prefix
"""
import asyncio
import logging
from pathlib import Path
from typing import Union

import aiofiles

from app.services.storage.base import BaseStorage, StorageResult

logger = logging.getLogger(__name__)


class LocalStorage(BaseStorage):
    def __init__(self, base_dir: Union[str, Path], url_prefix: str):
        self.base_dir = Path(base_dir).resolve()
        self.url_prefix = url_prefix.rstrip("/")
        self.base_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"[LocalStorage] initialized at {self.base_dir}, url_prefix={self.url_prefix}")

    @property
    def backend_name(self) -> str:
        return "local"

    def _resolve_path(self, object_key: str) -> Path:
        """object_key 是相对路径（含子目录，如 2026/06/abc.xlsx）"""
        # 防目录穿越：object_key 不允许以 / 开头或含 ..
        if object_key.startswith("/") or ".." in object_key.split("/"):
            raise ValueError(f"Invalid object_key: {object_key}")
        return self.base_dir / object_key

    async def save(self, content: bytes, object_key: str, content_type: str = "application/octet-stream") -> StorageResult:
        full_path = self._resolve_path(object_key)
        full_path.parent.mkdir(parents=True, exist_ok=True)

        # 同步写盘包成 async（避免阻塞事件循环）
        await asyncio.get_event_loop().run_in_executor(
            None, self._write_sync, full_path, content
        )
        logger.info(f"[LocalStorage] saved {len(content)} bytes to {full_path}")

        public_url = f"{self.url_prefix}/{object_key}"
        return StorageResult(
            backend=self.backend_name,
            object_key=object_key,
            public_url=public_url,
            local_path=str(full_path),
        )

    @staticmethod
    def _write_sync(path: Path, content: bytes) -> None:
        with open(path, "wb") as f:
            f.write(content)

    async def delete(self, object_key: str) -> bool:
        full_path = self._resolve_path(object_key)
        if not full_path.exists():
            return False
        await asyncio.get_event_loop().run_in_executor(None, full_path.unlink)
        return True

    async def get_bytes(self, object_key: str) -> bytes:
        full_path = self._resolve_path(object_key)
        if not full_path.exists():
            raise FileNotFoundError(f"Object not found: {object_key}")
        async with aiofiles.open(full_path, "rb") as f:
            return await f.read()
