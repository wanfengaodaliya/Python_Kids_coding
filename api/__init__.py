"""
================================================================================
API 路由模块包
================================================================================
这个包包含所有的 API 路由模块，每个模块负责一类功能：

模块列表：
1. auth.py - 用户认证相关接口（登录、注册、密码重置）
2. ai.py - AI 对话相关接口（聊天、历史记录、会话管理）
3. coding.py - 代码执行相关接口（运行 Python 代码）

使用说明：
在 main.py 中这样导入和使用：
    from app.api import ai, auth, coding
    app.include_router(auth.router, prefix="/api/v1")
    app.include_router(ai.router, prefix="/api/v1")
    app.include_router(coding.router, prefix="/api/v1")

作者: AIGC Project Team
创建日期: 2025
================================================================================
"""

# 这个文件标识 app/api 目录为一个 Python 包
# 通常 __init__.py 可以是空的，或者用于导出常用的对象
