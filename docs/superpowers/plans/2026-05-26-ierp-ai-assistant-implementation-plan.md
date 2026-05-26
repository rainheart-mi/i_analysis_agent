# IERP AI Assistant 工作流配置系统实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**目标:** 构建一个企业级 AI 助手系统，通过可视化配置将 N8N 工作流与 AI 对话界面连接，实现"对话驱动式"的 ERP 操作体验。

**架构概述:** 后端采用 FastAPI + SQLAlchemy + PostgreSQL，提供工作流配置的 CRUD API + N8N 执行引擎；前端采用 Vue 3 + Element Plus，通过 JSON Schema 动态渲染意图澄清表单和生成物表单（支持表格）。

**技术栈:**
- 后端: Python 3.11+ / FastAPI / SQLAlchemy / PostgreSQL / Pydantic
- 前端: Vue 3 + Vite + Element Plus + Pinia + Vue Router
- 数据库: PostgreSQL
- 文件存储: JSON Schema 文件（本地文件系统）
- 认证: JWT (python-jose + passlib)

---

## 文件结构

### 后端文件结构

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py                    # FastAPI 入口
│   ├── config.py                  # 配置管理
│   ├── database.py                # 数据库连接
│   ├── router.py                  # API 路由聚合
│   ├── api/
│   │   ├── __init__.py
│   │   └── v1/
│   │       ├── __init__.py
│   │       ├── auth.py           # 认证 API
│   │       ├── environments.py   # N8N 环境 API
│   │       ├── workflows.py       # 工作流路由 API
│   │       ├── mappings.py       # 节点映射 API
│   │       └── execute.py        # 工作流执行 API
│   ├── models/
│   │   ├── __init__.py
│   │   ├── base.py               # SQLAlchemy Base
│   │   ├── user.py               # 用户模型
│   │   ├── environment.py        # N8N 环境模型
│   │   ├── workflow.py           # 工作流路由模型
│   │   └── mapping.py            # 节点映射模型
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── auth.py               # 认证 Schema
│   │   ├── environment.py       # 环境 Schema
│   │   ├── workflow.py          # 工作流 Schema
│   │   └── mapping.py           # 映射 Schema
│   └── services/
│       ├── __init__.py
│       ├── n8n_service.py        # N8N API 调用服务
│       └── auth_service.py       # 认证服务
├── schemas/                       # JSON Schema 文件存储
│   ├── intent_forms/
│   └── artifact_forms/
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_auth.py
│   ├── test_environments.py
│   ├── test_workflows.py
│   └── test_mappings.py
├── requirements.txt
├── Dockerfile
└── README.md
```

### 前端文件结构

```
frontend/
├── public/
├── src/
│   ├── api/
│   │   ├── index.js              # API 统一导出
│   │   ├── auth.js               # 认证 API
│   │   ├── workflow.js           # 工作流 API
│   │   └── n8n.js                # N8N 环境 API
│   ├── assets/
│   │   └── styles/
│   │       └── main.scss         # 全局样式
│   ├── components/
│   │   ├── layout/
│   │   │   ├── AppLayout.vue     # 三栏布局容器
│   │   │   ├── Sidebar.vue      # 左侧菜单栏
│   │   │   └── Header.vue       # 顶部导航
│   │   └── common/
│   │       └── EmptyState.vue   # 空状态组件
│   ├── composables/
│   │   └── useSchemaForm.js     # Schema 表单渲染逻辑
│   ├── router/
│   │   └── index.js             # 路由配置
│   ├── store/
│   │   ├── index.js             # Pinia 入口
│   │   ├── user.js              # 用户状态
│   │   ├── workflow.js          # 工作流状态
│   │   └── chat.js              # 对话状态
│   ├── utils/
│   │   ├── schemaParser.js      # JSON Schema 解析器
│   │   └── formatters.js       # 格式化工具（货币、颜色）
│   ├── views/
│   │   ├── login/
│   │   │   └── Login.vue        # 登录页
│   │   ├── dashboard/
│   │   │   └── Dashboard.vue    # 中控仪表盘
│   │   ├── workflow-config/
│   │   │   ├── index.vue        # 配置管理首页
│   │   │   ├── EnvironmentList.vue   # N8N环境列表
│   │   │   ├── WorkflowRoutes.vue    # 工作流路由列表
│   │   │   └── NodeMappings.vue      # 节点映射配置
│   │   └── ai-assistant/
│   │       ├── AIAssistant.vue       # AI 助手主界面
│   │       ├── ChatPanel.vue         # 右侧对话面板
│   │       ├── WorkflowSelector.vue  # 工作流选择器
│   │       ├── ChatMessage.vue      # 消息气泡
│   │       ├── CanvasArea.vue       # 中央画布区域
│   │       └── DynamicForm.vue      # 动态表单渲染器
│   ├── App.vue
│   └── main.js
├── .env
├── .env.development
├── index.html
├── package.json
├── vite.config.js
└── README.md
```

---

## 任务清单

### Phase 1: 后端基础架构

#### Task 1: 后端项目初始化

**Files:**
- Create: `backend/requirements.txt`
- Create: `backend/app/__init__.py`
- Create: `backend/app/main.py`
- Create: `backend/app/config.py`
- Create: `backend/app/database.py`

- [ ] **Step 1: 创建 requirements.txt**

```txt
fastapi==0.109.2
uvicorn[standard]==0.27.1
sqlalchemy==2.0.25
asyncpg==0.29.0
pydantic==2.6.1
pydantic-settings==2.1.0
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
python-multipart==0.0.9
httpx==0.26.0
alembic==1.13.1
```

- [ ] **Step 2: 创建 app/config.py**

```python
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    APP_NAME: str = "IERP AI Assistant"
    DEBUG: bool = True
    
    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/ierp"
    
    # JWT
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # N8N
    N8N_DEFAULT_TIMEOUT: int = 60
    
    # Schema Files
    SCHEMA_BASE_PATH: str = "./schemas"
    
    class Config:
        env_file = ".env"


@lru_cache
def get_settings():
    return Settings()


settings = get_settings()
```

- [ ] **Step 3: 创建 app/database.py**

```python
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from app.config import settings


engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    pool_pre_ping=True,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    pass


async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
```

- [ ] **Step 4: 创建 app/main.py**

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.router import api_router


app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")


@app.get("/health")
async def health_check():
    return {"status": "ok"}
```

- [ ] **Step 5: 创建 app/router.py**

```python
from fastapi import APIRouter
from app.api.v1 import auth, environments, workflows, mappings, execute


api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["认证"])
api_router.include_router(environments.router, prefix="/n8n-environments", tags=["N8N环境"])
api_router.include_router(workflows.router, prefix="/workflows", tags=["工作流路由"])
api_router.include_router(mappings.router, prefix="/mappings", tags=["节点映射"])
api_router.include_router(execute.router, prefix="/execute", tags=["工作流执行"])
```

---

#### Task 2: 数据库模型定义

**Files:**
- Create: `backend/app/models/base.py`
- Create: `backend/app/models/user.py`
- Create: `backend/app/models/environment.py`
- Create: `backend/app/models/workflow.py`
- Create: `backend/app/models/mapping.py`
- Create: `backend/app/models/__init__.py`

- [ ] **Step 1: 创建 app/models/base.py**

```python
import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime
from app.database import Base


class BaseModel(Base):
    __abstract__ = True
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
```

- [ ] **Step 2: 创建 app/models/user.py**

```python
from sqlalchemy import Column, String, Boolean
from app.models.base import BaseModel


class User(BaseModel):
    __tablename__ = "users"
    
    username = Column(String(50), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    email = Column(String(100))
    is_active = Column(Boolean, default=True)
```

- [ ] **Step 3: 创建 app/models/environment.py**

```python
from sqlalchemy import Column, String, Boolean
from app.models.base import BaseModel


class N8NEnvironment(BaseModel):
    __tablename__ = "n8n_environments"
    
    name = Column(String(100), nullable=False)
    base_url = Column(String(500), nullable=False)
    api_key = Column(String(255))
    is_active = Column(Boolean, default=True)
```

- [ ] **Step 4: 创建 app/models/workflow.py**

```python
from sqlalchemy import Column, String, Boolean, Integer, Text, ForeignKey
from sqlalchemy.orm import relationship
from app.models.base import BaseModel


class WorkflowRoute(BaseModel):
    __tablename__ = "workflow_routes"
    
    environment_id = Column(String(36), ForeignKey("n8n_environments.id"), nullable=False)
    title = Column(String(200), nullable=False)
    description = Column(Text)
    n8n_workflow_id = Column(String(100))
    is_active = Column(Boolean, default=True)
    sort_order = Column(Integer, default=0)
    
    environment = relationship("N8NEnvironment")
    node_mappings = relationship("WorkflowNodeMapping", back_populates="route", cascade="all, delete-orphan")
```

- [ ] **Step 5: 创建 app/models/mapping.py**

```python
from sqlalchemy import Column, String, Text, ForeignKey, JSON
from sqlalchemy.orm import relationship
from app.models.base import BaseModel


class WorkflowNodeMapping(BaseModel):
    __tablename__ = "workflow_node_mappings"
    
    route_id = Column(String(36), ForeignKey("workflow_routes.id", ondelete="CASCADE"), nullable=False)
    node_id = Column(String(100), nullable=False)
    node_name = Column(String(200))
    intent_schema_path = Column(String(500))
    artifact_schema_path = Column(String(500))
    input_mapping = Column(JSON)
    output_mapping = Column(JSON)
    
    route = relationship("WorkflowRoute", back_populates="node_mappings")
```

- [ ] **Step 6: 创建 app/models/__init__.py**

```python
from app.models.base import BaseModel
from app.models.user import User
from app.models.environment import N8NEnvironment
from app.models.workflow import WorkflowRoute
from app.models.mapping import WorkflowNodeMapping

__all__ = ["BaseModel", "User", "N8NEnvironment", "WorkflowRoute", "WorkflowNodeMapping"]
```

---

#### Task 3: Pydantic Schemas 定义

**Files:**
- Create: `backend/app/schemas/auth.py`
- Create: `backend/app/schemas/environment.py`
- Create: `backend/app/schemas/workflow.py`
- Create: `backend/app/schemas/mapping.py`
- Create: `backend/app/schemas/__init__.py`

- [ ] **Step 1: 创建 app/schemas/auth.py**

```python
from pydantic import BaseModel, Field
from typing import Optional


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1)
    password: str = Field(..., min_length=1)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenRefreshRequest(BaseModel):
    refresh_token: str


class UserResponse(BaseModel):
    id: str
    username: str
    email: Optional[str]
    is_active: bool
    
    class Config:
        from_attributes = True
```

- [ ] **Step 2: 创建 app/schemas/environment.py**

```python
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class N8NEnvironmentBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    base_url: str = Field(..., max_length=500)
    api_key: Optional[str] = None
    is_active: bool = True


class N8NEnvironmentCreate(N8NEnvironmentBase):
    pass


class N8NEnvironmentUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=100)
    base_url: Optional[str] = Field(None, max_length=500)
    api_key: Optional[str] = None
    is_active: Optional[bool] = None


class N8NEnvironmentResponse(N8NEnvironmentBase):
    id: str
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class N8NEnvironmentTestResponse(BaseModel):
    success: bool
    message: str
```

- [ ] **Step 3: 创建 app/schemas/workflow.py**

```python
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class WorkflowRouteBase(BaseModel):
    environment_id: str
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    n8n_workflow_id: Optional[str] = None
    is_active: bool = True
    sort_order: int = 0


class WorkflowRouteCreate(WorkflowRouteBase):
    pass


class WorkflowRouteUpdate(BaseModel):
    environment_id: Optional[str] = None
    title: Optional[str] = Field(None, max_length=200)
    description: Optional[str] = None
    n8n_workflow_id: Optional[str] = None
    is_active: Optional[bool] = None
    sort_order: Optional[int] = None


class WorkflowRouteResponse(WorkflowRouteBase):
    id: str
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class WorkflowRouteListResponse(BaseModel):
    items: List[WorkflowRouteResponse]
    total: int
```

- [ ] **Step 4: 创建 app/schemas/mapping.py**

```python
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime


class WorkflowNodeMappingBase(BaseModel):
    route_id: str
    node_id: str = Field(..., min_length=1)
    node_name: Optional[str] = None
    intent_schema_path: Optional[str] = None
    artifact_schema_path: Optional[str] = None
    input_mapping: Optional[Dict[str, Any]] = None
    output_mapping: Optional[Dict[str, Any]] = None


class WorkflowNodeMappingCreate(WorkflowNodeMappingBase):
    pass


class WorkflowNodeMappingUpdate(BaseModel):
    route_id: Optional[str] = None
    node_id: Optional[str] = None
    node_name: Optional[str] = None
    intent_schema_path: Optional[str] = None
    artifact_schema_path: Optional[str] = None
    input_mapping: Optional[Dict[str, Any]] = None
    output_mapping: Optional[Dict[str, Any]] = None


class WorkflowNodeMappingResponse(WorkflowNodeMappingBase):
    id: str
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class WorkflowNodeMappingListResponse(BaseModel):
    items: List[WorkflowNodeMappingResponse]
    total: int
```

- [ ] **Step 5: 创建 app/schemas/__init__.py**

```python
from app.schemas.auth import LoginRequest, TokenResponse, TokenRefreshRequest, UserResponse
from app.schemas.environment import (
    N8NEnvironmentCreate, N8NEnvironmentUpdate, 
    N8NEnvironmentResponse, N8NEnvironmentTestResponse
)
from app.schemas.workflow import (
    WorkflowRouteCreate, WorkflowRouteUpdate,
    WorkflowRouteResponse, WorkflowRouteListResponse
)
from app.schemas.mapping import (
    WorkflowNodeMappingCreate, WorkflowNodeMappingUpdate,
    WorkflowNodeMappingResponse, WorkflowNodeMappingListResponse
)

__all__ = [
    "LoginRequest", "TokenResponse", "TokenRefreshRequest", "UserResponse",
    "N8NEnvironmentCreate", "N8NEnvironmentUpdate", 
    "N8NEnvironmentResponse", "N8NEnvironmentTestResponse",
    "WorkflowRouteCreate", "WorkflowRouteUpdate",
    "WorkflowRouteResponse", "WorkflowRouteListResponse",
    "WorkflowNodeMappingCreate", "WorkflowNodeMappingUpdate",
    "WorkflowNodeMappingResponse", "WorkflowNodeMappingListResponse",
]
```

---

### Phase 2: 后端 API 实现

#### Task 4: 认证 API 实现

**Files:**
- Create: `backend/app/services/auth_service.py`
- Create: `backend/app/api/v1/auth.py`
- Create: `backend/tests/test_auth.py`

- [ ] **Step 1: 创建 app/services/auth_service.py**

```python
from datetime import datetime, timedelta
from typing import Optional
from jose import jwt, JWTError
from passlib.context import CryptContext
from app.config import settings


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_refresh_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_token(token: str) -> Optional[dict]:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError:
        return None
```

- [ ] **Step 2: 创建 app/api/v1/auth.py**

```python
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models.user import User
from app.schemas.auth import LoginRequest, TokenResponse, TokenRefreshRequest, UserResponse
from app.services.auth_service import (
    verify_password, create_access_token, 
    create_refresh_token, decode_token, get_password_hash
)


router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.username == request.username))
    user = result.scalar_one_or_none()
    
    if not user or not verify_password(request.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误"
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="用户已被禁用"
        )
    
    access_token = create_access_token(data={"sub": user.id, "username": user.username})
    refresh_token = create_refresh_token(data={"sub": user.id})
    
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(request: TokenRefreshRequest, db: AsyncSession = Depends(get_db)):
    payload = decode_token(request.refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="无效的刷新令牌")
    
    result = await db.execute(select(User).where(User.id == payload["sub"]))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户不存在或已禁用")
    
    access_token = create_access_token(data={"sub": user.id, "username": user.username})
    new_refresh_token = create_refresh_token(data={"sub": user.id})
    
    return TokenResponse(access_token=access_token, refresh_token=new_refresh_token)


@router.get("/me", response_model=UserResponse)
async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
):
    payload = decode_token(token)
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="无效的令牌")
    
    result = await db.execute(select(User).where(User.id == payload["sub"]))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户不存在")
    
    return user
```

---

#### Task 5: N8N 环境 API 实现

**Files:**
- Create: `backend/app/api/v1/environments.py`
- Create: `backend/tests/test_environments.py`

- [ ] **Step 1: 创建 app/api/v1/environments.py**

```python
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from app.database import get_db
from app.models.environment import N8NEnvironment
from app.schemas.environment import (
    N8NEnvironmentCreate, N8NEnvironmentUpdate,
    N8NEnvironmentResponse, N8NEnvironmentTestResponse
)


router = APIRouter()


@router.get("", response_model=List[N8NEnvironmentResponse])
async def list_environments(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(N8NEnvironment).order_by(N8NEnvironment.created_at.desc()))
    return result.scalars().all()


@router.post("", response_model=N8NEnvironmentResponse, status_code=status.HTTP_201_CREATED)
async def create_environment(
    env: N8NEnvironmentCreate,
    db: AsyncSession = Depends(get_db)
):
    db_env = N8NEnvironment(**env.model_dump())
    db.add(db_env)
    await db.flush()
    await db.refresh(db_env)
    return db_env


@router.get("/{env_id}", response_model=N8NEnvironmentResponse)
async def get_environment(env_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(N8NEnvironment).where(N8NEnvironment.id == env_id))
    env = result.scalar_one_or_none()
    if not env:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="环境不存在")
    return env


@router.put("/{env_id}", response_model=N8NEnvironmentResponse)
async def update_environment(
    env_id: str,
    env_update: N8NEnvironmentUpdate,
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(N8NEnvironment).where(N8NEnvironment.id == env_id))
    env = result.scalar_one_or_none()
    if not env:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="环境不存在")
    
    update_data = env_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(env, key, value)
    
    await db.flush()
    await db.refresh(env)
    return env


@router.delete("/{env_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_environment(env_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(N8NEnvironment).where(N8NEnvironment.id == env_id))
    env = result.scalar_one_or_none()
    if not env:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="环境不存在")
    
    await db.delete(env)
    return None


@router.post("/{env_id}/test", response_model=N8NEnvironmentTestResponse)
async def test_environment(env_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(N8NEnvironment).where(N8NEnvironment.id == env_id))
    env = result.scalar_one_or_none()
    if not env:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="环境不存在")
    
    # TODO: 实现实际的 N8N 连接测试
    return N8NEnvironmentTestResponse(success=True, message="连接成功")
```

---

#### Task 6: 工作流路由 API 实现

**Files:**
- Create: `backend/app/api/v1/workflows.py`
- Create: `backend/tests/test_workflows.py`

- [ ] **Step 1: 创建 app/api/v1/workflows.py**

```python
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from typing import List
import json
from pathlib import Path
from app.database import get_db
from app.models.workflow import WorkflowRoute
from app.models.mapping import WorkflowNodeMapping
from app.schemas.workflow import (
    WorkflowRouteCreate, WorkflowRouteUpdate,
    WorkflowRouteResponse, WorkflowRouteListResponse
)
from app.config import settings


router = APIRouter()


@router.get("", response_model=WorkflowRouteListResponse)
async def list_workflows(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    # Count total
    count_result = await db.execute(select(func.count()).select_from(WorkflowRoute))
    total = count_result.scalar()
    
    # Get items
    result = await db.execute(
        select(WorkflowRoute)
        .options(selectinload(WorkflowRoute.node_mappings))
        .order_by(WorkflowRoute.sort_order, WorkflowRoute.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    items = result.scalars().all()
    
    return WorkflowRouteListResponse(items=items, total=total)


@router.post("", response_model=WorkflowRouteResponse, status_code=status.HTTP_201_CREATED)
async def create_workflow(
    workflow: WorkflowRouteCreate,
    db: AsyncSession = Depends(get_db)
):
    db_workflow = WorkflowRoute(**workflow.model_dump())
    db.add(db_workflow)
    await db.flush()
    await db.refresh(db_workflow)
    return db_workflow


@router.get("/{workflow_id}", response_model=WorkflowRouteResponse)
async def get_workflow(workflow_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(WorkflowRoute)
        .options(selectinload(WorkflowRoute.node_mappings))
        .where(WorkflowRoute.id == workflow_id)
    )
    workflow = result.scalar_one_or_none()
    if not workflow:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="工作流不存在")
    return workflow


@router.put("/{workflow_id}", response_model=WorkflowRouteResponse)
async def update_workflow(
    workflow_id: str,
    workflow_update: WorkflowRouteUpdate,
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(WorkflowRoute).where(WorkflowRoute.id == workflow_id))
    workflow = result.scalar_one_or_none()
    if not workflow:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="工作流不存在")
    
    update_data = workflow_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(workflow, key, value)
    
    await db.flush()
    await db.refresh(workflow)
    return workflow


@router.delete("/{workflow_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_workflow(workflow_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(WorkflowRoute).where(WorkflowRoute.id == workflow_id))
    workflow = result.scalar_one_or_none()
    if not workflow:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="工作流不存在")
    
    await db.delete(workflow)
    return None


@router.get("/{workflow_id}/intents")
async def get_intent_schema(workflow_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(WorkflowRoute)
        .options(selectinload(WorkflowRoute.node_mappings))
        .where(WorkflowRoute.id == workflow_id)
    )
    workflow = result.scalar_one_or_none()
    if not workflow:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="工作流不存在")
    
    if not workflow.node_mappings:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="未配置节点映射")
    
    mapping = workflow.node_mappings[0]
    if not mapping.intent_schema_path:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="未配置意图表单")
    
    schema_path = Path(settings.SCHEMA_BASE_PATH) / mapping.intent_schema_path
    if not schema_path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Schema文件不存在: {schema_path}")
    
    with open(schema_path, "r", encoding="utf-8") as f:
        schema = json.load(f)
    
    return schema


@router.get("/{workflow_id}/artifacts")
async def get_artifact_schema(workflow_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(WorkflowRoute)
        .options(selectinload(WorkflowRoute.node_mappings))
        .where(WorkflowRoute.id == workflow_id)
    )
    workflow = result.scalar_one_or_none()
    if not workflow:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="工作流不存在")
    
    if not workflow.node_mappings:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="未配置节点映射")
    
    mapping = workflow.node_mappings[0]
    if not mapping.artifact_schema_path:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="未配置生成物表单")
    
    schema_path = Path(settings.SCHEMA_BASE_PATH) / mapping.artifact_schema_path
    if not schema_path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Schema文件不存在: {schema_path}")
    
    with open(schema_path, "r", encoding="utf-8") as f:
        schema = json.load(f)
    
    return schema
```

---

#### Task 7: 节点映射 API 实现

**Files:**
- Create: `backend/app/api/v1/mappings.py`
- Create: `backend/tests/test_mappings.py`

- [ ] **Step 1: 创建 app/api/v1/mappings.py**

```python
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List
from app.database import get_db
from app.models.mapping import WorkflowNodeMapping
from app.models.workflow import WorkflowRoute
from app.schemas.mapping import (
    WorkflowNodeMappingCreate, WorkflowNodeMappingUpdate,
    WorkflowNodeMappingResponse, WorkflowNodeMappingListResponse
)


router = APIRouter()


@router.get("/workflow/{route_id}", response_model=WorkflowNodeMappingListResponse)
async def list_mappings_by_route(
    route_id: str,
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(WorkflowNodeMapping)
        .where(WorkflowNodeMapping.route_id == route_id)
        .order_by(WorkflowNodeMapping.created_at)
    )
    items = result.scalars().all()
    return WorkflowNodeMappingListResponse(items=list(items), total=len(items))


@router.post("/workflow/{route_id}", response_model=WorkflowNodeMappingResponse, status_code=status.HTTP_201_CREATED)
async def create_mapping(
    route_id: str,
    mapping: WorkflowNodeMappingCreate,
    db: AsyncSession = Depends(get_db)
):
    # Verify route exists
    route_result = await db.execute(select(WorkflowRoute).where(WorkflowRoute.id == route_id))
    if not route_result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="工作流不存在")
    
    db_mapping = WorkflowNodeMapping(**mapping.model_dump())
    db.add(db_mapping)
    await db.flush()
    await db.refresh(db_mapping)
    return db_mapping


@router.put("/{mapping_id}", response_model=WorkflowNodeMappingResponse)
async def update_mapping(
    mapping_id: str,
    mapping_update: WorkflowNodeMappingUpdate,
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(WorkflowNodeMapping).where(WorkflowNodeMapping.id == mapping_id)
    )
    mapping = result.scalar_one_or_none()
    if not mapping:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="映射不存在")
    
    update_data = mapping_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(mapping, key, value)
    
    await db.flush()
    await db.refresh(mapping)
    return mapping


@router.delete("/{mapping_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_mapping(mapping_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(WorkflowNodeMapping).where(WorkflowNodeMapping.id == mapping_id)
    )
    mapping = result.scalar_one_or_none()
    if not mapping:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="映射不存在")
    
    await db.delete(mapping)
    return None
```

---

#### Task 8: 工作流执行 API 实现

**Files:**
- Create: `backend/app/services/n8n_service.py`
- Create: `backend/app/api/v1/execute.py`

- [ ] **Step 1: 创建 app/services/n8n_service.py**

```python
import httpx
from typing import Dict, Any, Optional
from app.config import settings


class N8NService:
    def __init__(self, base_url: str, api_key: Optional[str] = None):
        self.base_url = base_url.rstrip("/")
        self.headers = {}
        if api_key:
            self.headers["X-N8N-API-Key"] = api_key
    
    async def execute_workflow(
        self,
        workflow_id: str,
        node_id: str,
        inputs: Dict[str, Any],
        timeout: int = settings.N8N_DEFAULT_TIMEOUT
    ) -> Dict[str, Any]:
        """触发 N8N 工作流执行"""
        url = f"{self.base_url}/webhook/{workflow_id}"
        
        async with httpx.AsyncClient(timeout=timeout) as client:
            try:
                response = await client.post(
                    url,
                    json=inputs,
                    headers=self.headers
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                raise Exception(f"N8N API 错误: {e.response.status_code} - {e.response.text}")
            except Exception as e:
                raise Exception(f"N8N 调用失败: {str(e)}")
    
    async def test_connection(self) -> bool:
        """测试 N8N 连接"""
        url = f"{self.base_url}/rest"
        async with httpx.AsyncClient(timeout=10) as client:
            try:
                response = await client.get(url, headers=self.headers)
                return response.status_code == 200
            except Exception:
                return False


def get_n8n_service(base_url: str, api_key: Optional[str] = None) -> N8NService:
    return N8NService(base_url, api_key)
```

- [ ] **Step 2: 创建 app/api/v1/execute.py**

```python
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from pydantic import BaseModel
from typing import Dict, Any
import uuid
from app.database import get_db
from app.models.workflow import WorkflowRoute
from app.models.environment import N8NEnvironment
from app.models.mapping import WorkflowNodeMapping
from app.services.n8n_service import get_n8n_service


router = APIRouter()


class ExecuteRequest(BaseModel):
    user_id: str
    inputs: Dict[str, Any]


class ExecuteResponse(BaseModel):
    task_id: str
    status: str
    message: str


@router.post("/{workflow_id}", response_model=ExecuteResponse)
async def execute_workflow(
    workflow_id: str,
    request: ExecuteRequest,
    db: AsyncSession = Depends(get_db)
):
    # Get workflow with environment and mapping
    result = await db.execute(
        select(WorkflowRoute)
        .options(selectinload(WorkflowRoute.environment))
        .options(selectinload(WorkflowRoute.node_mappings))
        .where(WorkflowRoute.id == workflow_id)
    )
    workflow = result.scalar_one_or_none()
    if not workflow:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="工作流不存在")
    
    if not workflow.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="工作流已禁用")
    
    if not workflow.node_mappings:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="未配置节点映射")
    
    mapping = workflow.node_mappings[0]
    environment = workflow.environment
    
    # Create n8n service
    n8n_service = get_n8n_service(environment.base_url, environment.api_key)
    
    # Generate task id
    task_id = str(uuid.uuid4())
    
    # Apply input mapping if configured
    final_inputs = request.inputs
    if mapping.input_mapping:
        final_inputs = {k: request.inputs.get(v) for k, v in mapping.input_mapping.items()}
    
    try:
        result_data = await n8n_service.execute_workflow(
            workflow_id=workflow.n8n_workflow_id,
            node_id=mapping.node_id,
            inputs=final_inputs
        )
        return ExecuteResponse(
            task_id=task_id,
            status="completed",
            message="工作流执行成功"
        )
    except Exception as e:
        return ExecuteResponse(
            task_id=task_id,
            status="failed",
            message=f"工作流执行失败: {str(e)}"
        )


@router.get("/{workflow_id}/status/{task_id}")
async def get_execution_status(
    workflow_id: str,
    task_id: str,
    db: AsyncSession = Depends(get_db)
):
    # TODO: 实现任务状态查询（可使用 Redis 或数据库存储任务状态）
    return {
        "task_id": task_id,
        "status": "completed",
        "message": "任务状态查询功能待实现"
    }


@router.post("/{workflow_id}/preview")
async def preview_workflow(
    workflow_id: str,
    request: ExecuteRequest,
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(WorkflowRoute)
        .options(selectinload(WorkflowRoute.node_mappings))
        .where(WorkflowRoute.id == workflow_id)
    )
    workflow = result.scalar_one_or_none()
    if not workflow:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="工作流不存在")
    
    if not workflow.node_mappings:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="未配置节点映射")
    
    mapping = workflow.node_mappings[0]
    
    # Preview the mapped inputs
    preview_inputs = request.inputs
    if mapping.input_mapping:
        preview_inputs = {k: request.inputs.get(v) for k, v in mapping.input_mapping.items()}
    
    return {
        "workflow_id": workflow_id,
        "node_id": mapping.node_id,
        "mapped_inputs": preview_inputs,
        "message": "预览信息"
    }
```

---

### Phase 3: 前端基础架构

#### Task 9: 前端项目初始化

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/vite.config.js`
- Create: `frontend/index.html`
- Create: `frontend/.env`
- Create: `frontend/src/main.js`
- Create: `frontend/src/App.vue`

- [ ] **Step 1: 创建 frontend/package.json**

```json
{
  "name": "ierp-ai-assistant-frontend",
  "version": "1.0.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "vue": "^3.4.21",
    "vue-router": "^4.3.0",
    "pinia": "^2.1.7",
    "element-plus": "^2.6.1",
    "@element-plus/icons-vue": "^2.3.1",
    "axios": "^1.6.7",
    "dayjs": "^1.11.10"
  },
  "devDependencies": {
    "@vitejs/plugin-vue": "^5.0.4",
    "vite": "^5.1.4",
    "sass": "^1.71.1"
  }
}
```

- [ ] **Step 2: 创建 frontend/vite.config.js**

```javascript
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import path from 'path'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src')
    }
  },
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true
      }
    }
  }
})
```

- [ ] **Step 3: 创建 frontend/.env**

```
VITE_API_BASE_URL=http://localhost:8000/api/v1
```

- [ ] **Step 4: 创建 frontend/src/main.js**

```javascript
import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import * as ElementPlusIconsVue from '@element-plus/icons-vue'
import App from './App.vue'
import router from './router'

const app = createApp(App)

// Register all icons
for (const [key, component] of Object.entries(ElementPlusIconsVue)) {
  app.component(key, component)
}

app.use(createPinia())
app.use(router)
app.use(ElementPlus)

app.mount('#app')
```

- [ ] **Step 5: 创建 frontend/src/App.vue**

```vue
<template>
  <router-view />
</template>

<script setup>
</script>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

html, body, #app {
  height: 100%;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
}
</style>
```

- [ ] **Step 6: 创建 frontend/src/router/index.js**

```javascript
import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/login/Login.vue')
  },
  {
    path: '/',
    component: () => import('@/components/layout/AppLayout.vue'),
    children: [
      {
        path: '',
        name: 'Dashboard',
        component: () => import('@/views/dashboard/Dashboard.vue')
      },
      {
        path: 'workflow-config',
        name: 'WorkflowConfig',
        component: () => import('@/views/workflow-config/index.vue')
      },
      {
        path: 'ai-assistant',
        name: 'AIAssistant',
        component: () => import('@/views/ai-assistant/AIAssistant.vue')
      }
    ]
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
```

---

#### Task 10: API 和 Store 基础

**Files:**
- Create: `frontend/src/api/index.js`
- Create: `frontend/src/api/auth.js`
- Create: `frontend/src/api/workflow.js`
- Create: `frontend/src/store/index.js`
- Create: `frontend/src/store/user.js`
- Create: `frontend/src/store/workflow.js`
- Create: `frontend/src/store/chat.js`

- [ ] **Step 1: 创建 frontend/src/api/index.js**

```javascript
import axios from 'axios'
import { ElMessage } from 'element-plus'

const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json'
  }
})

// Request interceptor
apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => Promise.reject(error)
)

// Response interceptor
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('access_token')
      window.location.href = '/login'
    }
    ElMessage.error(error.response?.data?.detail || '请求失败')
    return Promise.reject(error)
  }
)

export default apiClient
```

- [ ] **Step 2: 创建 frontend/src/api/auth.js**

```javascript
import apiClient from './index'

export const authApi = {
  login(username, password) {
    return apiClient.post('/auth/login', { username, password })
  },
  
  refreshToken(refreshToken) {
    return apiClient.post('/auth/refresh', { refresh_token: refreshToken })
  },
  
  getCurrentUser() {
    return apiClient.get('/auth/me')
  }
}
```

- [ ] **Step 3: 创建 frontend/src/api/workflow.js**

```javascript
import apiClient from './index'

export const workflowApi = {
  // Environments
  getEnvironments() {
    return apiClient.get('/n8n-environments')
  },
  
  createEnvironment(data) {
    return apiClient.post('/n8n-environments', data)
  },
  
  updateEnvironment(id, data) {
    return apiClient.put(`/n8n-environments/${id}`, data)
  },
  
  deleteEnvironment(id) {
    return apiClient.delete(`/n8n-environments/${id}`)
  },
  
  testEnvironment(id) {
    return apiClient.post(`/n8n-environments/${id}/test`)
  },
  
  // Workflows
  getWorkflows() {
    return apiClient.get('/workflows')
  },
  
  createWorkflow(data) {
    return apiClient.post('/workflows', data)
  },
  
  updateWorkflow(id, data) {
    return apiClient.put(`/workflows/${id}`, data)
  },
  
  deleteWorkflow(id) {
    return apiClient.delete(`/workflows/${id}`)
  },
  
  getIntentSchema(workflowId) {
    return apiClient.get(`/workflows/${workflowId}/intents`)
  },
  
  getArtifactSchema(workflowId) {
    return apiClient.get(`/workflows/${workflowId}/artifacts`)
  },
  
  // Mappings
  getMappings(routeId) {
    return apiClient.get(`/mappings/workflow/${routeId}`)
  },
  
  createMapping(routeId, data) {
    return apiClient.post(`/mappings/workflow/${routeId}`, data)
  },
  
  updateMapping(id, data) {
    return apiClient.put(`/mappings/${id}`, data)
  },
  
  deleteMapping(id) {
    return apiClient.delete(`/mappings/${id}`)
  },
  
  // Execute
  executeWorkflow(workflowId, data) {
    return apiClient.post(`/execute/${workflowId}`, data)
  },
  
  getExecutionStatus(workflowId, taskId) {
    return apiClient.get(`/execute/${workflowId}/status/${taskId}`)
  }
}
```

- [ ] **Step 4: 创建 frontend/src/store/user.js**

```javascript
import { defineStore } from 'pinia'
import { authApi } from '@/api/auth'

export const useUserStore = defineStore('user', {
  state: () => ({
    user: null,
    accessToken: localStorage.getItem('access_token'),
    refreshToken: localStorage.getItem('refresh_token')
  }),
  
  getters: {
    isLoggedIn: (state) => !!state.accessToken
  },
  
  actions: {
    async login(username, password) {
      const res = await authApi.login(username, password)
      this.accessToken = res.data.access_token
      this.refreshToken = res.data.refresh_token
      localStorage.setItem('access_token', res.data.access_token)
      localStorage.setItem('refresh_token', res.data.refresh_token)
      await this.fetchCurrentUser()
    },
    
    async fetchCurrentUser() {
      try {
        const res = await authApi.getCurrentUser()
        this.user = res.data
      } catch (e) {
        this.logout()
      }
    },
    
    logout() {
      this.user = null
      this.accessToken = null
      this.refreshToken = null
      localStorage.removeItem('access_token')
      localStorage.removeItem('refresh_token')
    }
  }
})
```

- [ ] **Step 5: 创建 frontend/src/store/workflow.js**

```javascript
import { defineStore } from 'pinia'
import { workflowApi } from '@/api/workflow'

export const useWorkflowStore = defineStore('workflow', {
  state: () => ({
    environments: [],
    workflows: [],
    currentWorkflow: null,
    currentIntentSchema: null,
    currentArtifactSchema: null,
    mappings: []
  }),
  
  actions: {
    async fetchEnvironments() {
      const res = await workflowApi.getEnvironments()
      this.environments = res.data
    },
    
    async fetchWorkflows() {
      const res = await workflowApi.getWorkflows()
      this.workflows = res.data.items
    },
    
    async fetchWorkflow(id) {
      const res = await workflowApi.getWorkflows()
      // Find by id if already fetched
      this.currentWorkflow = this.workflows.find(w => w.id === id)
    },
    
    async fetchIntentSchema(workflowId) {
      const res = await workflowApi.getIntentSchema(workflowId)
      this.currentIntentSchema = res.data
      return res.data
    },
    
    async fetchArtifactSchema(workflowId) {
      const res = await workflowApi.getArtifactSchema(workflowId)
      this.currentArtifactSchema = res.data
      return res.data
    },
    
    async executeWorkflow(workflowId, data) {
      return await workflowApi.executeWorkflow(workflowId, data)
    }
  }
})
```

- [ ] **Step 6: 创建 frontend/src/store/chat.js**

```javascript
import { defineStore } from 'pinia'

export const useChatStore = defineStore('chat', {
  state: () => ({
    messages: [],
    selectedWorkflow: null,
    isLoading: false
  }),
  
  actions: {
    addMessage(message) {
      this.messages.push({
        id: Date.now(),
        ...message,
        timestamp: new Date().toISOString()
      })
    },
    
    setSelectedWorkflow(workflow) {
      this.selectedWorkflow = workflow
    },
    
    clearMessages() {
      this.messages = []
    }
  }
})
```

---

### Phase 4: 前端核心组件

#### Task 11: 布局组件实现

**Files:**
- Create: `frontend/src/components/layout/AppLayout.vue`
- Create: `frontend/src/components/layout/Sidebar.vue`
- Create: `frontend/src/components/layout/Header.vue`

- [ ] **Step 1: 创建 frontend/src/components/layout/AppLayout.vue**

```vue
<template>
  <el-container class="app-layout">
    <el-aside width="240px">
      <sidebar />
    </el-aside>
    <el-container>
      <el-header>
        <header-bar />
      </el-header>
      <el-main>
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup>
import Sidebar from './Sidebar.vue'
import HeaderBar from './Header.vue'
</script>

<style scoped>
.app-layout {
  height: 100vh;
}

.el-aside {
  background: #1a1a2e;
  color: #fff;
}

.el-header {
  background: #fff;
  border-bottom: 1px solid #e4e4e7;
  display: flex;
  align-items: center;
  padding: 0 20px;
}

.el-main {
  background: #f4f4f5;
  padding: 20px;
}
</style>
```

- [ ] **Step 2: 创建 frontend/src/components/layout/Sidebar.vue**

```vue
<template>
  <div class="sidebar">
    <div class="logo">
      <span class="logo-text">IERP</span>
    </div>
    <el-menu
      :default-active="$route.path"
      router
      background-color="#1a1a2e"
      text-color="#a1a1aa"
      active-text-color="#667eea"
    >
      <el-menu-item index="/">
        <el-icon><Odometer /></el-icon>
        <span>中控仪表盘</span>
      </el-menu-item>
      <el-menu-item index="/ai-assistant">
        <el-icon><ChatDotRound /></el-icon>
        <span>AI 助手</span>
      </el-menu-item>
      <el-menu-item index="/workflow-config">
        <el-icon><Setting /></el-icon>
        <span>工作流配置</span>
      </el-menu-item>
    </el-menu>
  </div>
</template>

<script setup>
import { Odometer, ChatDotRound, Setting } from '@element-plus/icons-vue'
</script>

<style scoped>
.sidebar {
  height: 100%;
}

.logo {
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-bottom: 1px solid rgba(255,255,255,0.1);
}

.logo-text {
  font-size: 1.5rem;
  font-weight: 700;
  background: linear-gradient(90deg, #667eea, #764ba2);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}

.el-menu {
  border-right: none;
}
</style>
```

- [ ] **Step 3: 创建 frontend/src/components/layout/Header.vue**

```vue
<template>
  <div class="header-bar">
    <div class="left">
      <el-select v-model="selectedStore" placeholder="选择门店" size="default">
        <el-option label="上海门店" value="shanghai" />
        <el-option label="北京门店" value="beijing" />
      </el-select>
      <el-tag type="success" effect="plain" size="small">生产环境</el-tag>
    </div>
    <div class="right">
      <el-dropdown @command="handleCommand">
        <span class="user-info">
          <el-avatar size="small" :style="{ background: '#667eea' }">
            {{ userStore.user?.username?.[0]?.toUpperCase() || 'U' }}
          </el-avatar>
          <span>{{ userStore.user?.username || '用户' }}</span>
        </span>
        <template #dropdown>
          <el-dropdown-menu>
            <el-dropdown-item command="logout">退出登录</el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useUserStore } from '@/store/user'
import { useRouter } from 'vue-router'

const userStore = useUserStore()
const router = useRouter()
const selectedStore = ref('shanghai')

const handleCommand = (command) => {
  if (command === 'logout') {
    userStore.logout()
    router.push('/login')
  }
}
</script>

<style scoped>
.header-bar {
  width: 100%;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.right {
  display: flex;
  align-items: center;
}

.user-info {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
}
</style>
```

---

#### Task 12: 动态表单渲染器 (核心组件)

**Files:**
- Create: `frontend/src/views/ai-assistant/DynamicForm.vue`
- Create: `frontend/src/utils/schemaParser.js`
- Create: `frontend/src/composables/useSchemaForm.js`

- [ ] **Step 1: 创建 frontend/src/utils/schemaParser.js**

```javascript
/**
 * JSON Schema 解析工具
 * 将 JSON Schema 转换为 Element Plus 表单配置
 */

export function parseSchema(schema) {
  if (!schema || !schema.properties) {
    return []
  }
  
  return Object.entries(schema.properties).map(([key, prop]) => ({
    prop: key,
    label: prop.title || key,
    ...parseProperty(key, prop, schema)
  }))
}

function parseProperty(key, prop, schema) {
  const base = {
    required: schema.required?.includes(key) || false
  }
  
  // Handle ui:widget
  const widget = prop['ui:widget']
  const options = prop['ui:options'] || {}
  
  switch (widget) {
    case 'table':
      return { component: 'table', config: { ...prop, ...options } }
    case 'summary-grid':
      return { component: 'summary-grid', config: { ...prop, ...options } }
    case 'insight-box':
      return { component: 'insight-box', config: { ...prop, ...options } }
    case 'date-range-picker':
      return { component: 'el-date-picker', props: { type: 'daterange', ...options } }
    case 'date-picker':
      return { component: 'el-date-picker', props: { type: 'date', ...options } }
    case 'select':
      return { component: 'el-select', props: { ...options } }
    case 'switch':
      return { component: 'el-switch' }
    case 'radio':
      return { component: 'el-radio-group', props: { ...options } }
    case 'checkbox':
      return { component: 'el-checkbox-group', props: { ...options } }
    case 'input-number':
      return { component: 'el-input-number', props: { ...options } }
    case 'color-picker':
      return { component: 'el-color-picker', props: { ...options } }
    case 'slider':
      return { component: 'el-slider', props: { ...options } }
    case 'upload':
      return { component: 'el-upload', props: { ...options } }
    default:
      // Auto-detect based on type and format
      if (prop.type === 'array' && prop.items?.enum) {
        return { component: 'el-select', props: { multiple: true, ...options } }
      }
      if (prop.format === 'date-range') {
        return { component: 'el-date-picker', props: { type: 'daterange', ...options } }
      }
      if (prop.format === 'date') {
        return { component: 'el-date-picker', props: { type: 'date', ...options } }
      }
      if (prop.type === 'boolean') {
        return { component: 'el-switch' }
      }
      if (prop.type === 'number' || prop.type === 'integer') {
        return { component: 'el-input-number', props: { ...options } }
      }
      if (prop.enum) {
        return { component: 'el-select', props: { ...options } }
      }
      if (prop.format === 'textarea') {
        return { component: 'el-input', props: { type: 'textarea', ...options } }
      }
      return { component: 'el-input', props: { ...options } }
  }
}

/**
 * 格式化货币显示
 */
export function formatCurrency(value) {
  if (value === null || value === undefined) return '-'
  return new Intl.NumberFormat('zh-CN', {
    style: 'currency',
    currency: 'CNY'
  }).format(value)
}

/**
 * 格式化达成率颜色
 */
export function getRateColor(rate) {
  if (rate >= 100) return '#10B981'
  if (rate >= 80) return '#F59E0B'
  return '#EF4444'
}

/**
 * 格式化趋势箭头
 */
export function formatTrend(value) {
  if (!value) return ''
  if (value > 0) return `↑${Math.abs(value).toFixed(1)}%`
  if (value < 0) return `↓${Math.abs(value).toFixed(1)}%`
  return '-'
}
```

- [ ] **Step 2: 创建 frontend/src/composables/useSchemaForm.js**

```javascript
import { ref, computed } from 'vue'
import { parseSchema } from '@/utils/schemaParser'

export function useSchemaForm(schemaRef) {
  const formData = ref({})
  const formRules = ref({})
  
  const formItems = computed(() => {
    if (!schemaRef.value) return []
    return parseSchema(schemaRef.value)
  })
  
  const initFormData = (data = {}) => {
    const initial = {}
    formItems.value.forEach(item => {
      if (item.config?.default !== undefined) {
        initial[item.prop] = item.config.default
      }
    })
    formData.value = { ...initial, ...data }
  }
  
  const validate = () => {
    // Basic validation logic
    return true
  }
  
  const getSubmitData = () => {
    return { ...formData.value }
  }
  
  return {
    formData,
    formRules,
    formItems,
    initFormData,
    validate,
    getSubmitData
  }
}
```

- [ ] **Step 3: 创建 frontend/src/views/ai-assistant/DynamicForm.vue**

```vue
<template>
  <div class="dynamic-form">
    <el-form
      ref="formRef"
      :model="formData"
      :rules="formRules"
      label-position="top"
    >
      <template v-for="item in formItems" :key="item.prop">
        <!-- 表格组件 -->
        <template v-if="item.component === 'table'">
          <div class="form-section">
            <h3 class="section-title">{{ item.config.title }}</h3>
            <el-table
              :data="formData[item.prop] || []"
              border
              stripe
              style="width: 100%"
            >
              <el-table-column
                v-for="(col, colKey) in getTableColumns(item.config)"
                :key="colKey"
                :prop="colKey"
                :label="col.title"
                :width="col.width"
              >
                <template #default="{ row }">
                  <component
                    :is="getTableCellComponent(col)"
                    :row="row"
                    :col="col"
                    :value="row[colKey]"
                  />
                </template>
              </el-table-column>
            </el-table>
          </div>
        </template>
        
        <!-- 汇总网格组件 -->
        <template v-else-if="item.component === 'summary-grid'">
          <div class="summary-grid">
            <el-card
              v-for="(metric, idx) in formData[item.prop] || []"
              :key="idx"
              class="summary-card"
              :body-style="{ padding: '20px', textAlign: 'center' }"
            >
              <div class="metric-label">{{ metric.label }}</div>
              <div class="metric-value" :style="{ color: getMetricColor(metric.color) }">
                {{ metric.value }}
              </div>
            </el-card>
          </div>
        </template>
        
        <!-- 洞察框组件 -->
        <template v-else-if="item.component === 'insight-box'">
          <el-alert
            v-for="(insight, idx) in formData[item.prop] || []"
            :key="idx"
            :title="insight"
            type="info"
            :closable="false"
            show-icon
            class="insight-item"
          />
        </template>
        
        <!-- 标准表单项 -->
        <template v-else>
          <el-form-item :label="item.label" :prop="item.prop" :required="item.required">
            <el-input
              v-if="item.component === 'el-input'"
              v-model="formData[item.prop]"
              v-bind="item.props"
            />
            <el-select
              v-else-if="item.component === 'el-select'"
              v-model="formData[item.prop]"
              v-bind="item.props"
            >
              <el-option
                v-for="opt in getEnumOptions(item)"
                :key="opt.value"
                :label="opt.label"
                :value="opt.value"
              />
            </el-select>
            <el-switch
              v-else-if="item.component === 'el-switch'"
              v-model="formData[item.prop]"
            />
            <el-date-picker
              v-else-if="item.component === 'el-date-picker'"
              v-model="formData[item.prop]"
              v-bind="item.props"
            />
            <el-input-number
              v-else-if="item.component === 'el-input-number'"
              v-model="formData[item.prop]"
              v-bind="item.props"
            />
            <component
              v-else-if="item.component === 'custom'"
              :is="item.component"
              v-model="formData[item.prop]"
              v-bind="item.props"
            />
          </el-form-item>
        </template>
      </template>
    </el-form>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'
import { parseSchema, formatCurrency, getRateColor, formatTrend } from '@/utils/schemaParser'

const props = defineProps({
  schema: {
    type: Object,
    default: null
  },
  modelValue: {
    type: Object,
    default: () => ({})
  }
})

const emit = defineEmits(['update:modelValue'])

const formRef = ref(null)
const formData = ref({})

watch(
  () => props.modelValue,
  (val) => {
    formData.value = { ...val }
  },
  { immediate: true, deep: true }
)

watch(
  formData,
  (val) => {
    emit('update:modelValue', val)
  },
  { deep: true }
)

const formItems = ref([])

watch(
  () => props.schema,
  (schema) => {
    if (schema) {
      formItems.value = parseSchema(schema)
      // Initialize with defaults
      const defaults = {}
      formItems.value.forEach(item => {
        if (item.config?.default !== undefined) {
          defaults[item.prop] = item.config.default
        }
      })
      formData.value = { ...defaults, ...formData.value }
    }
  },
  { immediate: true }
)

const getEnumOptions = (item) => {
  if (!item.config?.items?.enum) return []
  return item.config.items.enum.map(val => ({
    value: val,
    label: val
  }))
}

const getTableColumns = (config) => {
  if (!config.items?.properties) return {}
  return config.items.properties
}

const getTableCellComponent = (col) => {
  // Returns the appropriate component for table cell
  if (col['ui:widget'] === 'rate-color') return 'RateColorCell'
  if (col['ui:widget'] === 'trend-arrow') return 'TrendArrowCell'
  if (col['ui:widget'] === 'currency') return 'CurrencyCell'
  if (col['ui:widget'] === 'link') return 'LinkCell'
  return 'TextCell'
}

const getMetricColor = (color) => {
  const colorMap = {
    blue: '#667eea',
    green: '#10B981',
    yellow: '#F59E0B',
    red: '#EF4444'
  }
  return colorMap[color] || '#667eea'
}
</script>

<style scoped>
.dynamic-form {
  padding: 20px;
}

.form-section {
  margin-bottom: 24px;
}

.section-title {
  font-size: 1.1rem;
  color: #e2e8f0;
  margin-bottom: 12px;
  padding-left: 12px;
  border-left: 4px solid #667eea;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 16px;
  margin-bottom: 24px;
}

.summary-card {
  background: rgba(255,255,255,0.05);
  border-radius: 12px;
}

.metric-label {
  color: #94a3b8;
  font-size: 0.9rem;
  margin-bottom: 8px;
}

.metric-value {
  font-size: 1.8rem;
  font-weight: 700;
}

.insight-item {
  margin-bottom: 12px;
}
</style>
```

---

#### Task 13: AI 助手主界面

**Files:**
- Create: `frontend/src/views/ai-assistant/AIAssistant.vue`
- Create: `frontend/src/views/ai-assistant/ChatPanel.vue`
- Create: `frontend/src/views/ai-assistant/WorkflowSelector.vue`
- Create: `frontend/src/views/ai-assistant/ChatMessage.vue`
- Create: `frontend/src/views/ai-assistant/CanvasArea.vue`

- [ ] **Step 1: 创建 frontend/src/views/ai-assistant/AIAssistant.vue**

```vue
<template>
  <div class="ai-assistant">
    <!-- 中央画布区域 -->
    <div class="canvas-area">
      <canvas-area
        :workflow="chatStore.selectedWorkflow"
        :intent-schema="workflowStore.currentIntentSchema"
        :artifact-schema="workflowStore.currentArtifactSchema"
        :execution-result="executionResult"
        @submit="handleFormSubmit"
      />
    </div>
    
    <!-- 右侧对话面板 -->
    <div class="chat-panel">
      <chat-panel
        :workflows="workflowStore.workflows"
        :messages="chatStore.messages"
        @select-workflow="handleSelectWorkflow"
        @send-message="handleSendMessage"
      />
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useChatStore } from '@/store/chat'
import { useWorkflowStore } from '@/store/workflow'
import { useUserStore } from '@/store/user'
import CanvasArea from './CanvasArea.vue'
import ChatPanel from './ChatPanel.vue'

const chatStore = useChatStore()
const workflowStore = useWorkflowStore()
const userStore = useUserStore()

const executionResult = ref(null)

// Load initial data
workflowStore.fetchWorkflows()

const handleSelectWorkflow = async (workflow) => {
  chatStore.setSelectedWorkflow(workflow)
  await workflowStore.fetchIntentSchema(workflow.id)
}

const handleFormSubmit = async (formData) => {
  if (!chatStore.selectedWorkflow) return
  
  chatStore.addMessage({
    type: 'user',
    content: '提交表单'
  })
  
  try {
    const res = await workflowStore.executeWorkflow(chatStore.selectedWorkflow.id, {
      user_id: userStore.user.id,
      inputs: formData
    })
    
    executionResult.value = res.data
    
    await workflowStore.fetchArtifactSchema(chatStore.selectedWorkflow.id)
    
    chatStore.addMessage({
      type: 'ai',
      content: '工作流执行完成'
    })
  } catch (e) {
    chatStore.addMessage({
      type: 'ai',
      content: `执行失败: ${e.message}`
    })
  }
}

const handleSendMessage = (message) => {
  chatStore.addMessage({
    type: 'user',
    content: message
  })
}
</script>

<style scoped>
.ai-assistant {
  height: calc(100vh - 100px);
  display: flex;
  gap: 16px;
}

.canvas-area {
  flex: 1;
  background: #fff;
  border-radius: 8px;
  overflow: hidden;
}

.chat-panel {
  width: 360px;
  flex-shrink: 0;
}
</style>
```

- [ ] **Step 2: 创建 frontend/src/views/ai-assistant/ChatPanel.vue**

```vue
<template>
  <div class="chat-panel">
    <div class="chat-header">
      <h3>AI 助手</h3>
    </div>
    
    <!-- 工作流选择器 -->
    <div class="workflow-selector">
      <el-select
        v-model="selectedWorkflowId"
        placeholder="选择工作流"
        filterable
        @change="handleWorkflowChange"
      >
        <el-option
          v-for="wf in workflows"
          :key="wf.id"
          :label="wf.title"
          :value="wf.id"
        >
          <div class="workflow-option">
            <span>{{ wf.title }}</span>
            <span class="workflow-desc">{{ wf.description }}</span>
          </div>
        </el-option>
      </el-select>
    </div>
    
    <!-- 消息列表 -->
    <div class="messages" ref="messagesRef">
      <div v-if="messages.length === 0" class="empty-state">
        <el-empty description="选择一个工作流开始对话" :image-size="80" />
      </div>
      <chat-message
        v-for="msg in messages"
        :key="msg.id"
        :message="msg"
      />
    </div>
    
    <!-- 输入框 -->
    <div class="chat-input">
      <el-input
        v-model="inputMessage"
        placeholder="输入消息，Enter发送，Shift+Enter换行"
        type="textarea"
        :rows="2"
        @keydown.enter.exact.prevent="handleSend"
      />
      <el-button type="primary" @click="handleSend" :disabled="!inputMessage.trim()">
        <el-icon><Promotion /></el-icon>
      </el-button>
    </div>
  </div>
</template>

<script setup>
import { ref, nextTick } from 'vue'
import ChatMessage from './ChatMessage.vue'
import { Promotion } from '@element-plus/icons-vue'

const props = defineProps({
  workflows: {
    type: Array,
    default: () => []
  },
  messages: {
    type: Array,
    default: () => []
  }
})

const emit = defineEmits(['select-workflow', 'send-message'])

const selectedWorkflowId = ref(null)
const inputMessage = ref('')
const messagesRef = ref(null)

const handleWorkflowChange = (workflowId) => {
  const workflow = props.workflows.find(w => w.id === workflowId)
  if (workflow) {
    emit('select-workflow', workflow)
  }
}

const handleSend = () => {
  if (!inputMessage.value.trim()) return
  emit('send-message', inputMessage.value)
  inputMessage.value = ''
  
  nextTick(() => {
    if (messagesRef.value) {
      messagesRef.value.scrollTop = messagesRef.value.scrollHeight
    }
  })
}
</script>

<style scoped>
.chat-panel {
  height: 100%;
  display: flex;
  flex-direction: column;
  background: #fff;
  border-radius: 8px;
}

.chat-header {
  padding: 16px;
  border-bottom: 1px solid #e4e4e7;
}

.chat-header h3 {
  margin: 0;
  font-size: 1rem;
  color: #1a1a2e;
}

.workflow-selector {
  padding: 12px 16px;
  border-bottom: 1px solid #e4e4e7;
}

.workflow-option {
  display: flex;
  flex-direction: column;
}

.workflow-desc {
  font-size: 0.75rem;
  color: #94a3b8;
}

.messages {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
}

.empty-state {
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
}

.chat-input {
  padding: 12px 16px;
  border-top: 1px solid #e4e4e7;
  display: flex;
  gap: 8px;
  align-items: flex-end;
}

.chat-input .el-textarea {
  flex: 1;
}
</style>
```

- [ ] **Step 3: 创建 frontend/src/views/ai-assistant/ChatMessage.vue**

```vue
<template>
  <div class="chat-message" :class="[`message-${message.type}`]">
    <div class="message-avatar">
      <el-avatar :size="32" :style="avatarStyle">
        {{ message.type === 'user' ? userStore.user?.username?.[0]?.toUpperCase() : 'AI' }}
      </el-avatar>
    </div>
    <div class="message-content">
      <div class="message-bubble">
        <template v-if="message.type === 'user'">
          {{ message.content }}
        </template>
        <template v-else>
          <div class="ai-response">
            <p>{{ message.content }}</p>
            <template v-if="message.formData">
              <dynamic-form
                :schema="message.formData"
                v-model="message.formDataValues"
              />
            </template>
          </div>
        </template>
      </div>
      <div class="message-time">
        {{ formatTime(message.timestamp) }}
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useUserStore } from '@/store/user'
import DynamicForm from './DynamicForm.vue'

const props = defineProps({
  message: {
    type: Object,
    required: true
  }
})

const userStore = useUserStore()

const avatarStyle = computed(() => ({
  background: props.message.type === 'user' ? '#3B5998' : '#64748b'
}))

const formatTime = (timestamp) => {
  if (!timestamp) return ''
  return new Date(timestamp).toLocaleTimeString('zh-CN', {
    hour: '2-digit',
    minute: '2-digit'
  })
}
</script>

<style scoped>
.chat-message {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
}

.message-user {
  flex-direction: row-reverse;
}

.message-ai {
  flex-direction: row;
}

.message-content {
  max-width: 80%;
}

.message-user .message-content {
  align-items: flex-end;
}

.message-bubble {
  padding: 12px 16px;
  border-radius: 12px;
  word-break: break-word;
}

.message-user .message-bubble {
  background: #3B5998;
  color: #fff;
}

.message-ai .message-bubble {
  background: #f4f4f5;
  color: #1a1a2e;
}

.message-time {
  font-size: 0.7rem;
  color: #94a3b8;
  margin-top: 4px;
}

.ai-response {
  min-width: 200px;
}

.ai-response p {
  margin: 0 0 8px 0;
}
</style>
```

- [ ] **Step 4: 创建 frontend/src/views/ai-assistant/CanvasArea.vue**

```vue
<template>
  <div class="canvas-area">
    <!-- 空状态 -->
    <div v-if="!workflow" class="empty-state">
      <el-empty description="选择一个工作流开始分析" :image-size="100" />
    </div>
    
    <!-- 意图澄清表单 -->
    <template v-else-if="intentSchema && !executionResult">
      <div class="canvas-header">
        <h2>{{ workflow.title }}</h2>
        <p>{{ workflow.description }}</p>
      </div>
      <dynamic-form
        ref="intentFormRef"
        :schema="intentSchema"
        v-model="intentFormData"
      />
      <div class="canvas-actions">
        <el-button @click="handleReset">重置</el-button>
        <el-button type="primary" @click="handleSubmit">执行工作流</el-button>
      </div>
    </template>
    
    <!-- 生成物表单预览 -->
    <template v-else-if="executionResult && artifactSchema">
      <div class="canvas-header">
        <h2>执行结果</h2>
      </div>
      <dynamic-form
        :schema="artifactSchema"
        :model-value="artifactFormData"
        readonly
      />
      <div class="canvas-actions">
        <el-button @click="handleBack">返回表单</el-button>
        <el-button type="primary">导出结果</el-button>
      </div>
    </template>
    
    <!-- 执行中状态 -->
    <template v-else-if="isExecuting">
      <div class="loading-state">
        <el-icon class="is-loading" :size="48"><Loading /></el-icon>
        <p>工作流执行中...</p>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'
import DynamicForm from './DynamicForm.vue'
import { Loading } from '@element-plus/icons-vue'

const props = defineProps({
  workflow: Object,
  intentSchema: Object,
  artifactSchema: Object,
  executionResult: Object
})

const emit = defineEmits(['submit'])

const intentFormRef = ref(null)
const intentFormData = ref({})
const artifactFormData = ref({})
const isExecuting = ref(false)

watch(
  () => props.artifactSchema,
  (schema) => {
    if (schema) {
      artifactFormData.value = { ...props.executionResult }
    }
  }
)

const handleSubmit = () => {
  isExecuting.value = true
  emit('submit', intentFormData.value)
}

const handleReset = () => {
  intentFormData.value = {}
}

const handleBack = () => {
  intentFormData.value = {}
  artifactFormData.value = {}
}
</script>

<style scoped>
.canvas-area {
  height: 100%;
  overflow-y: auto;
  padding: 24px;
}

.empty-state {
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
}

.canvas-header {
  margin-bottom: 24px;
}

.canvas-header h2 {
  margin: 0 0 8px 0;
  font-size: 1.5rem;
  color: #1a1a2e;
}

.canvas-header p {
  margin: 0;
  color: #64748b;
}

.canvas-actions {
  margin-top: 24px;
  display: flex;
  gap: 12px;
  justify-content: flex-end;
}

.loading-state {
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 16px;
  color: #64748b;
}
</style>
```

- [ ] **Step 5: 创建 frontend/src/views/ai-assistant/WorkflowSelector.vue**

```vue
<template>
  <div class="workflow-selector">
    <el-select
      v-model="selectedId"
      placeholder="请选择工作流"
      filterable
      @change="handleChange"
    >
      <el-option-group
        v-for="group in groupedWorkflows"
        :key="group.label"
        :label="group.label"
      >
        <el-option
          v-for="wf in group.options"
          :key="wf.id"
          :label="wf.title"
          :value="wf.id"
        >
          <div class="workflow-option-content">
            <div class="workflow-title">{{ wf.title }}</div>
            <div class="workflow-desc">{{ wf.description }}</div>
          </div>
        </el-option>
      </el-option-group>
    </el-select>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'

const props = defineProps({
  workflows: {
    type: Array,
    default: () => []
  }
})

const emit = defineEmits(['change'])

const selectedId = ref(null)

const groupedWorkflows = computed(() => {
  const active = props.workflows.filter(w => w.is_active)
  return [
    {
      label: '可用工作流',
      options: active
    }
  ]
})

const handleChange = (workflowId) => {
  const workflow = props.workflows.find(w => w.id === workflowId)
  emit('change', workflow)
}
</script>

<style scoped>
.workflow-option-content {
  padding: 4px 0;
}

.workflow-title {
  font-weight: 500;
}

.workflow-desc {
  font-size: 0.8rem;
  color: #94a3b8;
}
</style>
```

---

### Phase 5: 工作流配置管理页面

#### Task 14: 工作流配置页面

**Files:**
- Create: `frontend/src/views/workflow-config/index.vue`
- Create: `frontend/src/views/workflow-config/EnvironmentList.vue`
- Create: `frontend/src/views/workflow-config/WorkflowRoutes.vue`
- Create: `frontend/src/views/workflow-config/NodeMappings.vue`

- [ ] **Step 1: 创建 frontend/src/views/workflow-config/index.vue**

```vue
<template>
  <div class="workflow-config">
    <el-tabs v-model="activeTab">
      <el-tab-pane label="N8N环境" name="environments">
        <environment-list />
      </el-tab-pane>
      <el-tab-pane label="工作流路由" name="routes">
        <workflow-routes />
      </el-tab-pane>
      <el-tab-pane label="节点映射" name="mappings">
        <node-mappings />
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import EnvironmentList from './EnvironmentList.vue'
import WorkflowRoutes from './WorkflowRoutes.vue'
import NodeMappings from './NodeMappings.vue'

const activeTab = ref('environments')
</script>

<style scoped>
.workflow-config {
  background: #fff;
  border-radius: 8px;
  padding: 20px;
}
</style>
```

- [ ] **Step 2: 创建 frontend/src/views/workflow-config/EnvironmentList.vue**

```vue
<template>
  <div class="environment-list">
    <div class="toolbar">
      <el-button type="primary" @click="handleCreate">
        <el-icon><Plus /></el-icon>
        新建环境
      </el-button>
    </div>
    
    <el-table :data="environments" v-loading="loading">
      <el-table-column prop="name" label="环境名称" />
      <el-table-column prop="base_url" label="N8N地址" />
      <el-table-column prop="is_active" label="状态">
        <template #default="{ row }">
          <el-tag :type="row.is_active ? 'success' : 'info'" size="small">
            {{ row.is_active ? '激活' : '禁用' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="created_at" label="创建时间">
        <template #default="{ row }">
          {{ formatDate(row.created_at) }}
        </template>
      </el-table-column>
      <el-table-column label="操作" width="200">
        <template #default="{ row }">
          <el-button link type="primary" @click="handleEdit(row)">编辑</el-button>
          <el-button link type="primary" @click="handleTest(row)">测试</el-button>
          <el-button link type="danger" @click="handleDelete(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>
    
    <!-- 创建/编辑对话框 -->
    <el-dialog v-model="dialogVisible" :title="dialogTitle" width="500px">
      <el-form :model="formData" label-width="100px">
        <el-form-item label="环境名称">
          <el-input v-model="formData.name" />
        </el-form-item>
        <el-form-item label="N8N地址">
          <el-input v-model="formData.base_url" placeholder="http://localhost:5678" />
        </el-form-item>
        <el-form-item label="API Key">
          <el-input v-model="formData.api_key" show-password />
        </el-form-item>
        <el-form-item label="激活状态">
          <el-switch v-model="formData.is_active" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSave">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import { workflowApi } from '@/api/workflow'

const environments = ref([])
const loading = ref(false)
const dialogVisible = ref(false)
const dialogTitle = ref('')
const formData = ref({
  name: '',
  base_url: '',
  api_key: '',
  is_active: true
})

onMounted(() => {
  fetchEnvironments()
})

const fetchEnvironments = async () => {
  loading.value = true
  try {
    const res = await workflowApi.getEnvironments()
    environments.value = res.data
  } finally {
    loading.value = false
  }
}

const handleCreate = () => {
  formData.value = { name: '', base_url: '', api_key: '', is_active: true }
  dialogTitle.value = '新建环境'
  dialogVisible.value = true
}

const handleEdit = (row) => {
  formData.value = { ...row }
  dialogTitle.value = '编辑环境'
  dialogVisible.value = true
}

const handleSave = async () => {
  try {
    if (formData.value.id) {
      await workflowApi.updateEnvironment(formData.value.id, formData.value)
      ElMessage.success('更新成功')
    } else {
      await workflowApi.createEnvironment(formData.value)
      ElMessage.success('创建成功')
    }
    dialogVisible.value = false
    fetchEnvironments()
  } catch (e) {
    ElMessage.error('操作失败')
  }
}

const handleTest = async (row) => {
  try {
    const res = await workflowApi.testEnvironment(row.id)
    if (res.data.success) {
      ElMessage.success('连接成功')
    } else {
      ElMessage.error(res.data.message)
    }
  } catch (e) {
    ElMessage.error('连接失败')
  }
}

const handleDelete = async (row) => {
  try {
    await ElMessageBox.confirm('确认删除该环境吗？', '警告', { type: 'warning' })
    await workflowApi.deleteEnvironment(row.id)
    ElMessage.success('删除成功')
    fetchEnvironments()
  } catch (e) {
    if (e !== 'cancel') ElMessage.error('删除失败')
  }
}

const formatDate = (date) => {
  if (!date) return '-'
  return new Date(date).toLocaleDateString('zh-CN')
}
</script>

<style scoped>
.toolbar {
  margin-bottom: 16px;
}
</style>
```

- [ ] **Step 3: 创建 frontend/src/views/workflow-config/WorkflowRoutes.vue**

```vue
<template>
  <div class="workflow-routes">
    <div class="toolbar">
      <el-button type="primary" @click="handleCreate">
        <el-icon><Plus /></el-icon>
        新建工作流
      </el-button>
    </div>
    
    <el-table :data="workflows" v-loading="loading">
      <el-table-column prop="title" label="标题" />
      <el-table-column prop="description" label="描述" show-overflow-tooltip />
      <el-table-column prop="n8n_workflow_id" label="N8N工作流ID" />
      <el-table-column prop="is_active" label="状态">
        <template #default="{ row }">
          <el-tag :type="row.is_active ? 'success' : 'info'" size="small">
            {{ row.is_active ? '激活' : '禁用' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="200">
        <template #default="{ row }">
          <el-button link type="primary" @click="handleEdit(row)">编辑</el-button>
          <el-button link type="danger" @click="handleDelete(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>
    
    <el-dialog v-model="dialogVisible" :title="dialogTitle" width="600px">
      <el-form :model="formData" label-width="120px">
        <el-form-item label="所属环境">
          <el-select v-model="formData.environment_id" placeholder="请选择">
            <el-option
              v-for="env in environments"
              :key="env.id"
              :label="env.name"
              :value="env.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="标题">
          <el-input v-model="formData.title" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="formData.description" type="textarea" :rows="3" />
        </el-form-item>
        <el-form-item label="N8N工作流ID">
          <el-input v-model="formData.n8n_workflow_id" />
        </el-form-item>
        <el-form-item label="激活状态">
          <el-switch v-model="formData.is_active" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSave">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import { workflowApi } from '@/api/workflow'
import { useWorkflowStore } from '@/store/workflow'

const workflowStore = useWorkflowStore()
const workflows = ref([])
const environments = ref([])
const loading = ref(false)
const dialogVisible = ref(false)
const dialogTitle = ref('')
const formData = ref({
  environment_id: '',
  title: '',
  description: '',
  n8n_workflow_id: '',
  is_active: true
})

onMounted(() => {
  fetchData()
})

const fetchData = async () => {
  loading.value = true
  try {
    const [wfRes, envRes] = await Promise.all([
      workflowApi.getWorkflows(),
      workflowApi.getEnvironments()
    ])
    workflows.value = wfRes.data.items
    environments.value = envRes.data
  } finally {
    loading.value = false
  }
}

const handleCreate = () => {
  formData.value = { environment_id: '', title: '', description: '', n8n_workflow_id: '', is_active: true }
  dialogTitle.value = '新建工作流'
  dialogVisible.value = true
}

const handleEdit = (row) => {
  formData.value = { ...row }
  dialogTitle.value = '编辑工作流'
  dialogVisible.value = true
}

const handleSave = async () => {
  try {
    if (formData.value.id) {
      await workflowApi.updateWorkflow(formData.value.id, formData.value)
      ElMessage.success('更新成功')
    } else {
      await workflowApi.createWorkflow(formData.value)
      ElMessage.success('创建成功')
    }
    dialogVisible.value = false
    fetchData()
  } catch (e) {
    ElMessage.error('操作失败')
  }
}

const handleDelete = async (row) => {
  try {
    await ElMessageBox.confirm('确认删除该工作流吗？', '警告', { type: 'warning' })
    await workflowApi.deleteWorkflow(row.id)
    ElMessage.success('删除成功')
    fetchData()
  } catch (e) {
    if (e !== 'cancel') ElMessage.error('删除失败')
  }
}
</script>

<style scoped>
.toolbar {
  margin-bottom: 16px;
}
</style>
```

- [ ] **Step 4: 创建 frontend/src/views/workflow-config/NodeMappings.vue**

```vue
<template>
  <div class="node-mappings">
    <div class="toolbar">
      <el-select v-model="selectedRouteId" placeholder="选择工作流" @change="fetchMappings">
        <el-option
          v-for="wf in workflows"
          :key="wf.id"
          :label="wf.title"
          :value="wf.id"
        />
      </el-select>
      <el-button type="primary" @click="handleCreate" :disabled="!selectedRouteId">
        <el-icon><Plus /></el-icon>
        新建映射
      </el-button>
    </div>
    
    <el-table :data="mappings" v-loading="loading">
      <el-table-column prop="node_id" label="节点ID" />
      <el-table-column prop="node_name" label="节点名称" />
      <el-table-column prop="intent_schema_path" label="意图表单路径" show-overflow-tooltip />
      <el-table-column prop="artifact_schema_path" label="生成物表单路径" show-overflow-tooltip />
      <el-table-column label="操作" width="150">
        <template #default="{ row }">
          <el-button link type="primary" @click="handleEdit(row)">编辑</el-button>
          <el-button link type="danger" @click="handleDelete(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>
    
    <el-dialog v-model="dialogVisible" :title="dialogTitle" width="600px">
      <el-form :model="formData" label-width="140px">
        <el-form-item label="节点ID">
          <el-input v-model="formData.node_id" />
        </el-form-item>
        <el-form-item label="节点名称">
          <el-input v-model="formData.node_name" />
        </el-form-item>
        <el-form-item label="意图表单Schema路径">
          <el-input v-model="formData.intent_schema_path" placeholder="intent_forms/{route_id}/intent_schema.json" />
        </el-form-item>
        <el-form-item label="生成物表单Schema路径">
          <el-input v-model="formData.artifact_schema_path" placeholder="artifact_forms/{route_id}/artifact_schema.json" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSave">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import { workflowApi } from '@/api/workflow'

const workflows = ref([])
const mappings = ref([])
const selectedRouteId = ref(null)
const loading = ref(false)
const dialogVisible = ref(false)
const dialogTitle = ref('')
const formData = ref({
  node_id: '',
  node_name: '',
  intent_schema_path: '',
  artifact_schema_path: ''
})

onMounted(() => {
  fetchWorkflows()
})

const fetchWorkflows = async () => {
  const res = await workflowApi.getWorkflows()
  workflows.value = res.data.items
}

const fetchMappings = async () => {
  if (!selectedRouteId.value) return
  loading.value = true
  try {
    const res = await workflowApi.getMappings(selectedRouteId.value)
    mappings.value = res.data.items
  } finally {
    loading.value = false
  }
}

const handleCreate = () => {
  formData.value = { node_id: '', node_name: '', intent_schema_path: '', artifact_schema_path: '' }
  dialogTitle.value = '新建映射'
  dialogVisible.value = true
}

const handleEdit = (row) => {
  formData.value = { ...row }
  dialogTitle.value = '编辑映射'
  dialogVisible.value = true
}

const handleSave = async () => {
  try {
    if (formData.value.id) {
      await workflowApi.updateMapping(formData.value.id, formData.value)
      ElMessage.success('更新成功')
    } else {
      await workflowApi.createMapping(selectedRouteId.value, formData.value)
      ElMessage.success('创建成功')
    }
    dialogVisible.value = false
    fetchMappings()
  } catch (e) {
    ElMessage.error('操作失败')
  }
}

const handleDelete = async (row) => {
  try {
    await ElMessageBox.confirm('确认删除该映射吗？', '警告', { type: 'warning' })
    await workflowApi.deleteMapping(row.id)
    ElMessage.success('删除成功')
    fetchMappings()
  } catch (e) {
    if (e !== 'cancel') ElMessage.error('删除失败')
  }
}
</script>

<style scoped>
.toolbar {
  margin-bottom: 16px;
  display: flex;
  gap: 12px;
}
</style>
```

---

## 自检清单

### Spec 覆盖检查
- [x] 工作流路由配置 CRUD
- [x] 工作流节点映射配置 CRUD
- [x] 意图澄清表单配置（JSON Schema）
- [x] 生成物表单草稿配置（JSON Schema，含表格支持）
- [x] N8N 环境配置 CRUD
- [x] 工作流执行 API
- [x] AI 对话界面（三栏布局）
- [x] 动态表单渲染器
- [x] JWT 认证

### 占位符扫描
- [ ] 无 TBD/TODO
- [ ] 所有步骤都有具体代码
- [ ] 所有路径都是实际路径

### 类型一致性
- [ ] API 路径一致
- [ ] Schema 字段名一致
- [ ] Store 状态名一致

---

## 执行选择

**Plan 完成并保存至 `docs/superpowers/plans/2026-05-26-ierp-ai-assistant-implementation.md`**

两种执行方式：

**1. Subagent-Driven (推荐)** - 每个任务由独立 subagent 执行，任务间有检查点审核

**2. Inline Execution** - 在当前 session 中批量执行任务，带检查点

请选择执行方式？