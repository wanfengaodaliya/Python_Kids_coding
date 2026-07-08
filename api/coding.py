"""
================================================================================
代码执行 API 模块
================================================================================
这个文件负责处理代码执行相关的 HTTP 请求，主要功能：
1. 接收用户输入的 Python 代码
2. 在安全沙箱中执行代码
3. 返回执行结果（输出、错误、执行时间等）

安全沙箱说明：
- 代码在隔离环境中运行，防止恶意代码破坏系统
- 限制执行时间（超时自动终止）
- 限制内存使用
- 禁止危险操作（文件读写、网络访问等）

工作流程：
1. 前端发送代码到后端
2. 后端调用 sandbox 模块执行代码
3. sandbox 捕获输出、错误、执行时间
4. 后端返回结果给前端

作者: AIGC Project Team
创建日期: 2025
================================================================================
"""

# 导入必要的库
import json
from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field  # 数据验证
from sqlalchemy.orm import Session
from app.core.auth import get_demo_or_current_user
from app.core.database import get_db
from app.models.user import CodeExecutionRecord, Level, User
from app.api.learning import upsert_completed_progress
from app.services.sandbox.sandbox import run_code  # 沙箱执行函数


# =============================================================================
# 创建路由对象
# =============================================================================
router = APIRouter()


# =============================================================================
# 请求和响应模型（Pydantic）
# =============================================================================

class CodeRunRequest(BaseModel):
    """
    代码执行请求模型
    
    字段说明:
        code: 要执行的 Python 代码（必填）
        timeout: 超时时间，单位秒（默认10秒，防止死循环）
    """
    code: str = Field(..., description="Python code to execute")  # 代码内容
    timeout: int = Field(default=10, description="Execution timeout in seconds")  # 超时时间
    level_id: Optional[int] = Field(default=None, description="Level id when running level code")
    is_submission: bool = Field(default=False, description="Whether this run is a level submission")


class CodeRunResponse(BaseModel):
    """
    代码执行响应模型
    
    字段说明:
        code: 状态码
        msg: 提示消息
        data: 执行结果数据
            - success: 是否执行成功（布尔值）
            - output: 标准输出内容（print 的内容）
            - errors: 错误信息列表（如果有异常）
            - execution_time: 执行时间（秒）
    """
    code: int = 200  # 状态码
    msg: str = "执行成功"  # 提示消息
    data: dict = {}  # 数据


# =============================================================================
# 代码执行接口
# =============================================================================
@router.post("/code/run")
async def execute_code(
    request: CodeRunRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_demo_or_current_user),
):
    """
    代码执行接口 - 在沙箱中运行 Python 代码
    
    请求路径: POST /api/v1/code/run
    
    请求体示例:
        {
            "code": "print('Hello, World!')",
            "timeout": 10
        }
    
    参数:
        request (CodeRunRequest): 包含代码和超时时间
        
    返回:
        CodeRunResponse: 执行结果
        
    工作流程:
        1. 接收代码和超时时间
        2. 调用 sandbox.run_code() 执行代码
        3. 捕获输出、错误、执行时间
        4. 返回执行结果
        
    返回数据示例（成功）:
        {
            "code": 200,
            "msg": "执行成功",
            "data": {
                "success": true,
                "output": "Hello, World!",
                "errors": [],
                "execution_time": 0.001
            }
        }
        
    返回数据示例（失败）:
        {
            "code": 200,
            "msg": "代码有错误",
            "data": {
                "success": false,
                "output": "",
                "errors": [
                    {
                        "type": "SyntaxError",
                        "message": "invalid syntax",
                        "line": 1
                    }
                ],
                "execution_time": 0.001
            }
        }
    """
    # 调用沙箱执行代码
    # run_code() 是一个安全的代码执行函数
    result = run_code(request.code, timeout=request.timeout)
    level = None
    passed = False

    if request.level_id:
        level = db.query(Level).filter(Level.id == request.level_id, Level.status == "enabled").first()
        if level and result["success"]:
            passed = result["output"].strip() == level.expected_output.strip()

    record = CodeExecutionRecord(
        user_id=current_user.id,
        level_id=request.level_id if level else None,
        code=request.code,
        output=result["output"],
        errors=json.dumps(result["errors"], ensure_ascii=False),
        execution_time=result["execution_time"],
        success=result["success"],
        is_submission=request.is_submission,
        passed=passed,
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    if request.is_submission and passed and level:
        upsert_completed_progress(db, current_user.id, level.id, 100)
        db.commit()
    
    # 根据执行结果返回不同的消息
    # result["success"] 为 True 表示执行成功
    # result["success"] 为 False 表示有错误
    return CodeRunResponse(
        code=200,
        msg="执行成功" if result["success"] else "代码有错误",
        data={
            "success": result["success"],  # 是否成功
            "output": result["output"],  # 标准输出
            "errors": result["errors"],  # 错误列表
            "execution_time": result["execution_time"],  # 执行时间
            "execution_id": record.execution_id,
            "passed": passed,
        },
    )


@router.get("/code/records")
async def get_code_records(
    level_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_demo_or_current_user),
):
    query = db.query(CodeExecutionRecord).filter(CodeExecutionRecord.user_id == current_user.id)
    if level_id:
        query = query.filter(CodeExecutionRecord.level_id == level_id)
    records = query.order_by(CodeExecutionRecord.executed_at.desc()).limit(100).all()
    return CodeRunResponse(
        code=200,
        msg="获取成功",
        data={
            "records": [
                {
                    "execution_id": row.execution_id,
                    "level_id": row.level_id,
                    "code": row.code,
                    "output": row.output,
                    "errors": json.loads(row.errors or "[]"),
                    "execution_time": row.execution_time,
                    "success": row.success,
                    "is_submission": row.is_submission,
                    "passed": row.passed,
                    "executed_at": row.executed_at,
                }
                for row in records
            ]
        },
    )
