"""
================================================================================
AIGC Backend Application - 主入口文件
================================================================================
这个文件是整个后端应用的启动入口，主要功能：
1. 初始化 FastAPI 应用实例
2. 配置 CORS 跨域支持（允许前端访问）
3. 自动创建数据库表
4. 注册所有 API 路由
5. 提供健康检查接口

作者: AIGC Project Team
创建日期: 2025
================================================================================
"""

# 导入 FastAPI 核心库
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# 导入自定义模块
from app.api import ai, auth, coding, learning  # 导入功能模块的路由
from app.core.database import Base, SessionLocal, engine, ensure_mysql_schema_compatibility  # 导入数据库基类和引擎
from app.models import (  # 导入数据模型（确保表被注册）
    AIChatRecord,
    CodeExecutionRecord,
    Level,
    StudyRecord,
    User,
    UserProgress,
)
from app.services.learning import seed_default_levels

# =============================================================================
# 数据库初始化
# =============================================================================
# 尝试自动创建所有数据库表
# Base.metadata.create_all() 会根据定义的模型类自动在数据库中创建表
# 如果表已存在，不会重复创建
try:
    Base.metadata.create_all(bind=engine)
    ensure_mysql_schema_compatibility(engine)
    seed_db = SessionLocal()
    try:
        seed_default_levels(seed_db)
    finally:
        seed_db.close()
    print("Database tables initialized successfully / 数据库表初始化成功")
except Exception as exc:
    print(f"Database initialization failed / 数据库初始化失败: {exc}")

# =============================================================================
# FastAPI 应用实例创建
# =============================================================================
# 创建 FastAPI 应用实例
# - title: 应用名称（会显示在 API 文档页面）
# - description: 应用描述（会显示在 API 文档页面）
# - version: 应用版本号
app = FastAPI(
    title="AIGC Backend",
    description="Backend service for authentication, AI chat, and code execution. / 提供用户认证、AI对话和代码执行功能的后端服务。",
    version="1.0.0",
)

# =============================================================================
# CORS 跨域配置
# =============================================================================
# 添加 CORS 中间件，允许前端从不同的域名访问后端 API
# CORS = Cross-Origin Resource Sharing（跨域资源共享）
# 在开发阶段，前端通常运行在 localhost:3000，后端运行在 localhost:8000，需要跨域
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 允许所有来源（生产环境建议指定具体域名）
    allow_credentials=True,  # 允许携带凭证（如 cookies）
    allow_methods=["*"],  # 允许所有 HTTP 方法（GET, POST, PUT, DELETE 等）
    allow_headers=["*"],  # 允许所有请求头
)

# =============================================================================
# 注册路由
# =============================================================================
# 把各个功能模块的路由注册到主应用上
# - prefix: 路由前缀，所有接口都会以 /api/v1 开头
# - tags: 标签，用于在 API 文档中分组显示

# 1. 用户认证模块路由（登录、注册、密码重置等）
app.include_router(auth.router, prefix="/api/v1", tags=["auth / 用户认证"])

# 2. AI 对话模块路由（聊天、历史记录等）
app.include_router(ai.router, prefix="/api/v1", tags=["ai / AI对话"])

# 3. 代码执行模块路由（运行代码等）
app.include_router(coding.router, prefix="/api/v1", tags=["coding / 代码执行"])

# 4. 学习模块路由（关卡、进度、打卡、统计）
app.include_router(learning.router, prefix="/api/v1", tags=["learning / 学习管理"])


# =============================================================================
# 根路径接口
# =============================================================================
@app.get("/")
async def root():
    """
    根路径接口 - 返回应用基本信息

    访问地址: http://localhost:8000/

    返回:
        dict: 包含欢迎消息的字典
    """
    return {"message": "AIGC Backend Service / AIGC 后端服务"}


# =============================================================================
# 健康检查接口
# =============================================================================
@app.get("/api/v1/health")
async def health_check():
    """
    健康检查接口 - 用于监控服务是否正常运行

    访问地址: http://localhost:8000/api/v1/health

    返回:
        dict: 包含服务状态的字典
    """
    return {"status": "healthy / 服务正常"}


# =============================================================================
# 直接运行入口（开发时使用）
# =============================================================================
# 当直接运行 python main.py 时，会执行这段代码
# 使用 uvicorn 作为 ASGI 服务器来运行 FastAPI 应用
if __name__ == "__main__":
    uvicorn.run(
        "main:app",  # 应用位置（模块名:实例名）
        host="0.0.0.0",  # 监听所有网络接口（可以从外部访问）
        port=8000,  # 监听端口
        reload=True  # 开发模式：代码修改后自动重启
    )
