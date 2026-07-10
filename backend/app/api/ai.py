

from fastapi import APIRouter, HTTPException, status, Depends, Query
from fastapi.responses import StreamingResponse  # 用于流式响应
from sqlalchemy.orm import Session  # 数据库会话
from app.core.auth import get_demo_or_current_user
from app.core.database import get_db  # 数据库依赖项
from app.models.user import AIChatRecord, User  # AI对话记录模型
from pydantic import BaseModel  # 数据验证模型
import json  # JSON 处理
import asyncio  # 异步编程
import uuid  # 生成唯一ID
import os  # 环境变量
from datetime import datetime  # 日期时间
from typing import List, Optional  # 类型提示
import httpx  # 异步 HTTP 客户端（用于调用本地模型）



router = APIRouter()


# =============================================================================
# 本地大模型配置
# =============================================================================

LOCAL_LLM_URL = os.getenv("LOCAL_LLM_URL", "http://172.23.46.241:8000/v1/chat/completions")

# 模型参数配置
MAX_TOKENS = int(os.getenv("AI_MAX_TOKENS", "512"))  # 模型最大生成 token 数（约等于字数）
TEMPERATURE = float(os.getenv("AI_TEMPERATURE", "0.7"))  # 温度参数（0-2），越高越随机，越低越确定


def build_model_messages(history_messages: List[dict], question: str) -> List[dict]:
    """构造模型消息：同会话历史上下文 + 当前用户问题，不额外注入系统提示词。"""
    return [
        *history_messages,
        {"role": "user", "content": question},
    ]


def sse_data(data: dict) -> str:
    """安全生成 SSE 数据行，避免 token 中的引号或换行破坏 JSON。"""
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"


def parse_model_stream_line(data_str: str) -> tuple[str, bool]:
    """兼容本地 token/done 格式和 OpenAI 兼容 SSE chunk 格式。"""
    if data_str.strip() == "[DONE]":
        return "", True

    data = json.loads(data_str)
    if "token" in data:
        return data.get("token") or "", bool(data.get("done"))

    choices = data.get("choices") or []
    if choices:
        choice = choices[0] or {}
        delta = choice.get("delta") or {}
        message = choice.get("message") or {}
        content = delta.get("content") or message.get("content") or ""
        return content, choice.get("finish_reason") is not None

    return "", bool(data.get("done"))




class AIChatRequest(BaseModel):

    question: str  # 用户的问题
    question_type: str = "text"  # 问题类型（预留字段）
    stream: bool = True  # 是否流式响应
    session_id: Optional[str] = None  # 会话ID


class AIChatResponse(BaseModel):

    code: int = 200  # 状态码
    msg: str = "响应成功"  # 提示消息
    data: dict  # 数据


class ChatRecordResponse(BaseModel):

    record_id: int
    user_id: int
    session_id: str
    question: str
    question_type: str
    answer: str
    response_time: datetime
    is_stream: bool


class ChatHistoryResponse(BaseModel):

    code: int = 200
    msg: str = "获取成功"
    data: List[ChatRecordResponse]  # 记录列表
    total: int  # 总数
    page: int  # 当前页
    page_size: int  # 每页数量


# =============================================================================
# 辅助函数：获取会话历史
# =============================================================================
async def get_session_history(db: Session, session_id: str, user_id: int):

    history = db.query(AIChatRecord).filter(
        AIChatRecord.user_id == user_id,
        AIChatRecord.session_id == session_id
    ).order_by(AIChatRecord.response_time.asc()).all()
    
    # 把数据库记录转换为模型需要的格式
    messages = []
    for record in history:
        # 添加用户的问题
        messages.append({"role": "user", "content": record.question})
        # 添加 AI 的回答
        messages.append({"role": "assistant", "content": record.answer})
    
    return messages


# =============================================================================
# 流式响应处理函数
# =============================================================================
async def stream_chat_response(chat_data: AIChatRequest, db: Session, user_id: int):

    # 1. 处理会话ID
    # 如果前端没有提供，生成新的 UUID
    session_id = chat_data.session_id or str(uuid.uuid4())
    
    # 2. 获取历史记录
    history_messages = await get_session_history(db, session_id, user_id)
    
    # 3. 构建完整的消息列表：历史记录 + 当前问题
    messages = build_model_messages(history_messages, chat_data.question)
    
    # 4. 构建请求给本地模型
    payload = {
        "messages": messages,
        "max_tokens": MAX_TOKENS,
        "temperature": TEMPERATURE,
        "stream": True
    }
    
    # 用于收集完整的回答（最后保存到数据库）
    full_content = ""
    
    # 5. 定义异步生成器函数
    # 这是流式响应的核心
    async def generate():
        """异步生成器 - 逐块生成响应数据"""
        nonlocal full_content  # 引用外部变量
        
        # 使用 httpx 异步客户端发送请求
        async with httpx.AsyncClient(timeout=60.0) as client:
            # client.stream() 表示流式请求
            async with client.stream("POST", LOCAL_LLM_URL, json=payload) as response:
                # 检查响应状态码
                if response.status_code != 200:
                    # 出错了，返回错误信息
                    error_text = await response.aread()
                    yield sse_data({"content": f"调用本地模型失败: {response.status_code}", "session_id": session_id})
                    yield sse_data({"content": "[END]", "session_id": session_id})
                    return
                
                # 逐行读取 SSE 流
                # SSE 格式：每行以 "data: " 开头
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        # 去掉 "data: " 前缀
                        data_str = line[6:]
                        if data_str.strip():
                            try:
                                token, done = parse_model_stream_line(data_str)
                                if token:
                                    full_content += token  # 收集完整回答
                                    # 转发给前端，格式符合 SSE
                                    yield sse_data({"content": token, "session_id": session_id})
                                if done:
                                    break
                            except json.JSONDecodeError:
                                # JSON 解析失败，跳过这一行
                                continue
        
        # 发送结束标记
        # 前端看到 "[END]" 就知道响应结束了
        yield sse_data({"content": "[END]", "session_id": session_id})
        
        # 6. 保存对话记录到数据库
        chat_record = AIChatRecord(
            user_id=user_id,
            conversation_id=1,
            session_id=session_id,
            question=chat_data.question,
            question_type=chat_data.question_type,
            answer=full_content,
            is_stream=True
        )
        db.add(chat_record)
        db.commit()
    
    # 返回流式响应
    # media_type="text/event-stream" 表示这是 SSE 流
    return StreamingResponse(
        generate(),
        media_type="text/event-stream"
    )


# =============================================================================
# 非流式响应处理函数
# =============================================================================
async def normal_chat_response(chat_data: AIChatRequest, db: Session, user_id: int):

    # 1. 处理会话ID
    session_id = chat_data.session_id or str(uuid.uuid4())
    
    # 2. 获取历史记录
    history_messages = await get_session_history(db, session_id, user_id)
    
    # 3. 构建消息列表：历史记录 + 当前问题
    messages = build_model_messages(history_messages, chat_data.question)
    
    # 4. 构建请求
    payload = {
        "messages": messages,
        "max_tokens": MAX_TOKENS,
        "temperature": TEMPERATURE,
        "stream": True
    }
    
    try:
        # 5. 调用本地模型
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(LOCAL_LLM_URL, json=payload)
            if response.status_code != 200:
                raise Exception(f"本地模型返回错误: {response.status_code}")
            
            # 6. 读取流并拼完整
            full_answer = ""
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data_str = line[6:]
                    if data_str.strip():
                        try:
                            token, done = parse_model_stream_line(data_str)
                            if token:
                                full_answer += token
                            if done:
                                break
                        except:
                            pass
            
            # 防止空回答
            if not full_answer:
                full_answer = "抱歉，模型没有返回有效回答。"
        
        # 7. 保存到数据库
        chat_record = AIChatRecord(
            user_id=user_id,
            conversation_id=1,
            session_id=session_id,
            question=chat_data.question,
            question_type=chat_data.question_type,
            answer=full_answer,
            is_stream=False
        )
        db.add(chat_record)
        db.commit()
        
        # 8. 返回响应
        return AIChatResponse(
            code=200,
            msg="响应成功",
            data={
                "question": chat_data.question,
                "answer": full_answer,
                "response_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "session_id": session_id
            }
        )
    
    except Exception as e:
        # 出错了，返回错误信息
        return AIChatResponse(
            code=400,
            msg=f"本地大模型调用失败: {str(e)}",
            data={}
        )


# =============================================================================
# 聊天接口（主入口）
# =============================================================================
@router.post("/ai/chat")
async def chat_with_ai(
    chat_data: AIChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_demo_or_current_user),
):

    # 检查问题是否为空
    if not chat_data.question:
        return AIChatResponse(
            code=400,
            msg="问题不能为空",
            data={}
        )
    
    # 根据 stream 参数选择响应方式
    if chat_data.stream:
        # 流式响应
        return await stream_chat_response(chat_data, db, current_user.id)
    else:
        # 非流式响应
        return await normal_chat_response(chat_data, db, current_user.id)


# =============================================================================
# 获取历史记录接口
# =============================================================================
MAX_HISTORY_RECORDS = 500  # 最多返回500条记录


@router.get("/ai/history", response_model=ChatHistoryResponse)
async def get_chat_history(
    session_id: Optional[str] = Query(None, description="会话ID"),  # 可选，过滤会话
    db: Session = Depends(get_db),
    current_user: User = Depends(get_demo_or_current_user),
):

    # 构建查询
    query = db.query(AIChatRecord).filter(AIChatRecord.user_id == current_user.id)

    # 如果提供了 session_id，再加过滤条件
    if session_id:
        query = query.filter(AIChatRecord.session_id == session_id)

    # 计算总数
    total = query.count()

    # 执行查询，最多返回 MAX_HISTORY_RECORDS 条
    records = query.order_by(AIChatRecord.response_time.asc()).limit(MAX_HISTORY_RECORDS).all()

    # 转换为响应模型
    record_responses = [
        ChatRecordResponse(
            record_id=record.record_id,
            user_id=record.user_id,
            session_id=record.session_id,
            question=record.question,
            question_type=record.question_type,
            answer=record.answer,
            response_time=record.response_time,
            is_stream=record.is_stream
        )
        for record in records
    ]

    # 返回响应
    return ChatHistoryResponse(
        data=record_responses,
        total=total,
        page=1,
        page_size=total
    )


# =============================================================================
# 删除历史记录接口
# =============================================================================
@router.delete("/ai/history/{record_id}")
async def delete_chat_history(
    record_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_demo_or_current_user),
):

    # 查找记录
    # 同时检查 record_id 和 user_id，防止删除别人的记录
    record = db.query(AIChatRecord).filter(
        AIChatRecord.record_id == record_id,
        AIChatRecord.user_id == current_user.id
    ).first()
    
    # 记录不存在
    if not record:
        return AIChatResponse(
            code=404,
            msg="记录不存在",
            data={}
        )
    
    # 删除记录
    db.delete(record)
    db.commit()
    
    # 返回成功
    return AIChatResponse(
        code=200,
        msg="删除成功",
        data={}
    )


# =============================================================================
# 获取会话列表接口
# =============================================================================
@router.get("/ai/sessions")
async def get_sessions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_demo_or_current_user),
):

    from sqlalchemy import func  # SQL 函数（min, max, count）
    

    sessions = db.query(
        AIChatRecord.session_id,
        func.min(AIChatRecord.response_time).label('first_message_time'),
        func.max(AIChatRecord.response_time).label('last_message_time'),
        func.count(AIChatRecord.record_id).label('message_count')
    ).filter(
        AIChatRecord.user_id == current_user.id
    ).group_by(
        AIChatRecord.session_id
    ).order_by(
        func.max(AIChatRecord.response_time).desc()  # 按最后时间倒序
    ).all()
    
    # 构建会话列表
    session_list = []
    for session in sessions:
        # 查询这个会话的第一条消息（用于显示）
        first_message = db.query(AIChatRecord.question).filter(
            AIChatRecord.user_id == current_user.id,
            AIChatRecord.session_id == session.session_id
        ).order_by(AIChatRecord.response_time.asc()).first()
        
        session_list.append({
            "session_id": session.session_id,
            "first_question": first_message[0] if first_message else "",
            "message_count": session.message_count,
            "first_message_time": session.first_message_time,
            "last_message_time": session.last_message_time
        })
    
    # 返回响应
    return AIChatResponse(
        code=200,
        msg="获取成功",
        data={"sessions": session_list}
    )
