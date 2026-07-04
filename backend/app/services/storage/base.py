"""
文件存储抽象层。

定义 BaseStorage 接口 + StorageResult 数据类；具体后端（local / oss2）
各自实现该接口，运行时由 get_storage() 单例工厂根据 STORAGE_BACKEND 配置选择。
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


@dataclass
class StorageResult:
    """存储后端保存结果"""
    backend: str                     # 'local' | 'oss2'
    object_key: str                  # 存储内唯一 key（bucket 内路径 or 本地相对路径）
    public_url: str                  # 公网可访问的 URL（amis 表单用这个）
    # 冗余字段（按 backend 填充）
    local_path: Optional[str] = None     # 本地绝对磁盘路径（仅 local）
    oss_bucket: Optional[str] = None     # OSS bucket 名（仅 oss2）
    oss_object_key: Optional[str] = None # OSS object key（仅 oss2）


class BaseStorage(ABC):
    """存储后端抽象接口

    实现类需保证 save / delete / get_bytes 是协程（async def）。
    oss2 SDK 本身是同步的，实现类需用 run_in_executor 包装。
    """

    @property
    @abstractmethod
    def backend_name(self) -> str:
        """后端标识：'local' | 'oss2'"""

    @abstractmethod
    async def save(
        self,
        content: bytes,
        object_key: str,
        content_type: str = "application/octet-stream",
    ) -> StorageResult:
        """保存字节内容到存储后端，返回元数据

        Args:
            content: 文件二进制
            object_key: 存储内唯一 key（不含 prefix；prefix 由后端实现加）
            content_type: MIME type
        """

    @abstractmethod
    async def delete(self, object_key: str) -> bool:
        """删除对象；不存在返回 False"""

    @abstractmethod
    async def get_bytes(self, object_key: str) -> bytes:
        """读取对象字节内容（用于下载/代理）"""
