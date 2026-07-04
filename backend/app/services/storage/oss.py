"""
阿里云 OSS2 存储后端。
- 使用 oss2 官方 Python SDK（同步 API）
- 所有 SDK 调用包到 run_in_executor，避免阻塞 asyncio 事件循环
- OSS_OBJECT_KEY_PREFIX 可选，便于按租户/业务隔离
"""
import asyncio
import logging
from typing import Optional

import oss2

from app.services.storage.base import BaseStorage, StorageResult

logger = logging.getLogger(__name__)


class OssStorage(BaseStorage):
    def __init__(
        self,
        access_key_id: str,
        access_key_secret: str,
        endpoint: str,
        bucket: str,
        url_prefix: str,
        object_key_prefix: str = "",
    ):
        if not all([access_key_id, access_key_secret, endpoint, bucket, url_prefix]):
            raise ValueError(
                "OssStorage 缺少必填配置：OSS_ACCESS_KEY_ID / OSS_ACCESS_KEY_SECRET / "
                "OSS_ENDPOINT / OSS_BUCKET / OSS_URL_PREFIX 全部必填"
            )

        self.auth = oss2.Auth(access_key_id, access_key_secret)
        self.bucket_obj = oss2.Bucket(self.auth, endpoint, bucket)
        self.bucket_name = bucket
        self.url_prefix = url_prefix.rstrip("/")
        self.object_key_prefix = object_key_prefix.strip("/")
        if self.object_key_prefix:
            self.object_key_prefix += "/"
        logger.info(f"[OssStorage] initialized: bucket={bucket}, endpoint={endpoint}, prefix={self.object_key_prefix!r}")

    @property
    def backend_name(self) -> str:
        return "oss2"

    def _full_key(self, object_key: str) -> str:
        return f"{self.object_key_prefix}{object_key}"

    async def save(self, content: bytes, object_key: str, content_type: str = "application/octet-stream") -> StorageResult:
        full_key = self._full_key(object_key)
        headers = {"Content-Type": content_type}

        # oss2.put_object 是同步阻塞调用，包到 thread pool
        result = await asyncio.get_event_loop().run_in_executor(
            None, self.bucket_obj.put_object, full_key, content, headers
        )
        if result.status != 200:
            raise RuntimeError(f"OSS put_object failed: status={result.status}, request_id={result.request_id}")

        logger.info(f"[OssStorage] saved {len(content)} bytes to oss://{self.bucket_name}/{full_key}")
        public_url = f"{self.url_prefix}/{full_key}"
        return StorageResult(
            backend=self.backend_name,
            object_key=object_key,  # 入库时存原始 key（不含 prefix），便于跨 bucket 迁移
            public_url=public_url,
            oss_bucket=self.bucket_name,
            oss_object_key=full_key,
        )

    async def delete(self, object_key: str) -> bool:
        full_key = self._full_key(object_key)
        result = await asyncio.get_event_loop().run_in_executor(
            None, self.bucket_obj.delete_object, full_key
        )
        # oss2 在对象不存在时仍返回 204；视为成功删除
        return result.status in (200, 204)

    async def get_bytes(self, object_key: str) -> bytes:
        full_key = self._full_key(object_key)
        result = await asyncio.get_event_loop().run_in_executor(
            None, self.bucket_obj.get_object, full_key
        )
        try:
            return result.read()
        finally:
            if hasattr(result, "close"):
                # oss2 ObjectReadResult 支持 context manager / close
                try:
                    result.close()
                except Exception:
                    pass
