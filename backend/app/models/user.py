from sqlalchemy import Column, String, Boolean
from app.models.base import BaseModel


class User(BaseModel):
    __tablename__ = "users"

    username = Column(String(50), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    email = Column(String(100))
    is_active = Column(Boolean, default=True)