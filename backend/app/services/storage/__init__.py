"""
存储后端单例工厂。

参照 app/services/n8n_service.py:65 (get_n8n_service) 的模式：
- 首次调用时根据 settings.STORAGE_BACKEND 实例化对应后端
- 后续调用直接返回缓存的实例（OSS Bucket 客户端构造开销不小）
- STORAGE_BACKEND=oss2 但关键配置缺失 → 启动时立刻抛错（fail-fast）
"""
import logging
from typing import Optional

from app.config import settings
from app.services.storage.base import BaseStorage, StorageResult

logger = logging.getLogger(__name__)

_storage_instance: Optional[BaseStorage] = None


def get_storage() -> BaseStorage:
    """获取存储后端单例"""
    global _storage_instance
    if _storage_instance is None:
        backend = (settings.STORAGE_BACKEND or "local").lower()
        if backend == "local":
            from app.services.storage.local import LocalStorage
            _storage_instance = LocalStorage(
                base_dir=settings.LOCAL_STORAGE_DIR,
                url_prefix=settings.LOCAL_STORAGE_URL_PREFIX,
            )
        elif backend == "oss2":
            from app.services.storage.oss import OssStorage
            _storage_instance = OssStorage(
                access_key_id=settings.OSS_ACCESS_KEY_ID,
                access_key_secret=settings.OSS_ACCESS_KEY_SECRET,
                endpoint=settings.OSS_ENDPOINT,
                bucket=settings.OSS_BUCKET,
                url_prefix=settings.OSS_URL_PREFIX,
                object_key_prefix=settings.OSS_OBJECT_KEY_PREFIX,
            )
        else:
            raise ValueError(
                f"Unknown STORAGE_BACKEND={backend!r}. "
                f"支持: 'local' | 'oss2'"
            )
        logger.info(f"[storage] 初始化后端: {_storage_instance.backend_name}")
    return _storage_instance


def reset_storage() -> None:
    """测试用：重置单例（修改 settings 后强制重建）"""
    global _storage_instance
    _storage_instance = None


__all__ = ["BaseStorage", "StorageResult", "get_storage", "reset_storage"]
