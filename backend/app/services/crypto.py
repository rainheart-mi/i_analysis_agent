"""
对称加密工具（Fernet）。

用途：N8NEnvironment.password_enc 列存的是 Fernet 加密后的密文。
key 派生：base64(sha256(settings.SECRET_KEY)) — Fernet 要求 32-byte url-safe base64 key。

库依赖：cryptography（已通过 python-jose[cryptography] 间接安装，requirements.txt:7）
"""
import base64
import hashlib

from cryptography.fernet import Fernet

from app.config import settings


def _derive_key() -> bytes:
    """把 SECRET_KEY 派生为 Fernet 需要的 32-byte url-safe base64 key。

    SHA-256 固定输出 32 字节；base64 编码后 Fernet 接受。
    不直接用 SECRET_KEY.encode()：长度 / 字符集可能不满足 Fernet 要求。
    """
    digest = hashlib.sha256(settings.SECRET_KEY.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest)


def encrypt_password(plain: str) -> str:
    """明文 password → Fernet 令牌（url-safe base64 字符串）。"""
    if not plain:
        return ""
    return Fernet(_derive_key()).encrypt(plain.encode("utf-8")).decode("utf-8")


def decrypt_password(token: str) -> str:
    """Fernet 令牌 → 明文 password。空字符串/None 直接返回。"""
    if not token:
        return ""
    return Fernet(_derive_key()).decrypt(token.encode("utf-8")).decode("utf-8")
