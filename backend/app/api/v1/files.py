"""
文件上传 / 元数据 / 下载 端点。

设计要点：
- POST /upload 接受 multipart/form-data，字段名固定为 "file"（amis 默认）
- 响应格式遵循 amis 约定：{ "status": 0, "data": { "value": "<url>", "file_id": "...", ... } }
- 内部用 get_storage() 工厂选择后端；Upload 行 同步落 UploadedFile 表
- 多租户隔离：所有读路径都按 tenant_id 过滤；file_uuid 唯一但跨租户不冲突
- GET /download 通过 storage 后端读取并流式返回；支持 Content-Disposition 让浏览器下载
"""
import logging
import uuid
from datetime import datetime
from pathlib import PurePosixPath
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.config import settings
from app.database import get_db
from app.api.deps import get_current_user_tenant
from app.models import UploadedFile
from app.schemas.file import UploadedFileResponse, AmisUploadResponse, AmisUploadData
from app.services.storage import get_storage

logger = logging.getLogger(__name__)

router = APIRouter()


def _build_object_key(original_filename: str, file_uuid: str) -> str:
    """按 年/月/uuid+ext 组织路径，避免单目录文件过多

    - 不保留原始文件名（防注入 / 路径冲突）
    - 保留扩展名（前端预览时 mime 探测更准）
    """
    ext = PurePosixPath(original_filename).suffix.lower()  # ".xlsx"
    now = datetime.utcnow()
    return f"{now.year:04d}/{now.month:02d}/{file_uuid}{ext}"


@router.post("/upload", response_model=AmisUploadResponse)
async def upload_file(
    file: UploadFile = File(..., description="amis input-file 上传的二进制"),
    db: AsyncSession = Depends(get_db),
    ctx = Depends(get_current_user_tenant),
):
    """amis input-file receiver 端点

    接受 multipart/form-data，字段名必须为 'file'。
    返回 amis 格式响应，data.value 写入表单字段（公网 URL）。
    """

    # 1. 读取内容（限制大小由 Content-Length header + 显式长度检查双重保护）
    content = await file.read()
    if len(content) > settings.MAX_UPLOAD_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"文件超过 {settings.MAX_UPLOAD_SIZE // (1024*1024)} MB 上限",
        )
    if len(content) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="空文件",
        )

    # 2. 构造 object_key
    file_uuid = str(uuid.uuid4())
    original = file.filename or "upload.bin"
    object_key = _build_object_key(original, file_uuid)

    # 3. 调存储后端保存
    storage = get_storage()
    try:
        result = await storage.save(
            content=content,
            object_key=object_key,
            content_type=file.content_type or "application/octet-stream",
        )
    except Exception as e:
        logger.exception(f"[upload] storage save failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"存储后端保存失败: {type(e).__name__}",
        )

    # 4. 落 UploadedFile 元数据
    db_file = UploadedFile(
        file_uuid=file_uuid,
        tenant_id=ctx.tenant_id,
        user_id=ctx.user_id,
        original_filename=original,
        content_type=file.content_type,
        size_bytes=len(content),
        storage_backend=result.backend,
        object_key=result.object_key,
        local_path=result.local_path,
        public_url=result.public_url,
        oss_bucket=result.oss_bucket,
        oss_object_key=result.oss_object_key,
    )
    db.add(db_file)
    await db.commit()
    await db.refresh(db_file)

    logger.info(
        f"[upload] tenant={ctx.tenant_id} user={ctx.user_id} file_uuid={file_uuid} "
        f"backend={result.backend} size={len(content)}"
    )

    return AmisUploadResponse(
        status=0,
        msg="ok",
        data=AmisUploadData(
            value=result.public_url,
            file_id=file_uuid,
            name=original,
            size=len(content),
            url=result.public_url,
        ),
    )


@router.get("/{file_uuid}/metadata", response_model=UploadedFileResponse)
async def get_file_metadata(
    file_uuid: str,
    db: AsyncSession = Depends(get_db),
    ctx = Depends(get_current_user_tenant),
):
    """查文件元数据（多租户隔离：跨租户 file_uuid 一律 404）"""
    result = await db.execute(
        select(UploadedFile).where(
            UploadedFile.file_uuid == file_uuid,
            UploadedFile.tenant_id == ctx.tenant_id,
        )
    )
    db_file = result.scalar_one_or_none()
    if not db_file:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="文件不存在")
    return db_file


@router.delete("/{file_uuid}")
async def delete_file(
    file_uuid: str,
    db: AsyncSession = Depends(get_db),
    ctx = Depends(get_current_user_tenant),
):
    """物理删除文件（多租户隔离）

    顺序：先 storage.delete（找不到不报错），再删 UploadedFile 行
    - FileAttachment 通过 FK ON DELETE CASCADE 自动级联清
    - 即便 storage 失败（OSS 临时不可达），仍删 DB 行：
      至少前端能立刻清掉引用，磁盘垃圾可后台回收

    响应遵循 amis 约定：{ status, msg, data: { file_id } }
    """
    result = await db.execute(
        select(UploadedFile).where(
            UploadedFile.file_uuid == file_uuid,
            UploadedFile.tenant_id == ctx.tenant_id,
        )
    )
    db_file = result.scalar_one_or_none()
    if not db_file:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="文件不存在")

    object_key = db_file.object_key
    backend = db_file.storage_backend

    # 1. 物理删存储
    storage = get_storage()
    try:
        await storage.delete(object_key)
    except FileNotFoundError:
        logger.warning(f"[delete] storage already missing: {object_key}")
    except Exception as e:
        # 不阻断：DB 行还要删，否则前端看着有文件但下不动
        logger.exception(f"[delete] storage.delete failed (file_uuid={file_uuid}, backend={backend}): {e}")

    # 2. 删 DB 行（FileAttachment 级联清）
    await db.delete(db_file)
    await db.commit()

    logger.info(
        f"[delete] tenant={ctx.tenant_id} file_uuid={file_uuid} backend={backend} key={object_key}"
    )

    return {"status": 0, "msg": "ok", "data": {"file_id": file_uuid}}


@router.get("/{file_uuid}/download")
async def download_file(
    file_uuid: str,
    db: AsyncSession = Depends(get_db),
    ctx = Depends(get_current_user_tenant),
):
    """流式下载文件（从 storage 后端读取）

    - Local 模式：直接 FileResponse 也行，但统一走 storage 层便于将来切到 OSS 不改 endpoint
    - OSS 模式：从 bucket 拉字节再回传；可选加 302 跳 OSS 公开 URL 优化
    """
    result = await db.execute(
        select(UploadedFile).where(
            UploadedFile.file_uuid == file_uuid,
            UploadedFile.tenant_id == ctx.tenant_id,
        )
    )
    db_file = result.scalar_one_or_none()
    if not db_file:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="文件不存在")

    storage = get_storage()
    try:
        content = await storage.get_bytes(db_file.object_key)
    except FileNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="文件已丢失")
    except Exception as e:
        logger.exception(f"[download] storage read failed: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="存储读取失败")

    # 用 ASCII 安全的 filename（中文 / 特殊字符走 RFC 5987）
    from urllib.parse import quote
    safe_name = quote(db_file.original_filename)

    return StreamingResponse(
        iter([content]),
        media_type=db_file.content_type or "application/octet-stream",
        headers={
            "Content-Disposition": (
                f"attachment; filename={safe_name!r};"
                f" filename*=UTF-8''{safe_name}"
            ),
            "Content-Length": str(len(content)),
        },
    )
