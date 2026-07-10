"""
================================================================================
数据模型定义模块
================================================================================
这个文件定义了数据库表对应的 Python 类（ORM 模型），主要包含：
1. User 模型 - 存储用户基本信息
2. AIChatRecord 模型 - 存储 AI 对话记录

ORM（Object-Relational Mapping）说明：
- ORM 允许我们用 Python 类来表示数据库表
- 类的属性对应表的列
- 类的实例对应表的行
- 我们不需要写 SQL，直接操作 Python 对象就行

SQLAlchemy 类型说明：
- Column: 定义一个列
- Integer: 整数类型
- String: 字符串类型（需要指定长度）
- DateTime: 日期时间类型
- ForeignKey: 外键（关联其他表）
- func.now(): 数据库服务器当前时间（不是 Python 的时间）

作者: AIGC Project Team
创建日期: 2025
================================================================================
"""

# 导入 SQLAlchemy 类型和函数
from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.sql import func
from app.core.database import Base


# =============================================================================
# User 用户模型
# =============================================================================
class User(Base):
    """
    用户表模型 - 存储系统用户的基本信息
    
    数据库表名: users
    
    字段说明:
        id: 用户ID（主键，自动递增）
        username: 用户名（唯一，用于登录）
        password: 密码哈希（永远不存储明文密码！）
        phone: 手机号（唯一，用于注册和密码重置）
        nickname: 用户昵称
        avatar: 用户头像地址
        created_at: 账号创建时间（自动设置）
        last_login: 最后登录时间
        status: 账号状态（enabled/disabled）
    """
    
    # 定义数据库表名
    __tablename__ = "users"
    
    # id 列 - 主键，自增整数
    # primary_key=True: 这是主键
    # index=True: 为这个列创建索引（加快查询速度）
    id = Column(Integer, primary_key=True, index=True)
    
    # username 列 - 用户名，字符串类型，最大长度 50
    # unique=True: 用户名必须唯一，不能重复
    # nullable=False: 这个字段不能为空
    username = Column(String(50), unique=True, nullable=False, index=True)
    
    # password 列 - 密码哈希，字符串类型，最大长度 255
    # 注意：这里存储的是 Argon2 哈希后的密码，不是明文！
    password = Column(String(255), nullable=False)
    
    # phone 列 - 手机号，字符串类型，最大长度 20
    # unique=True: 手机号必须唯一
    phone = Column(String(20), unique=True, nullable=False, index=True)

    # nickname 列 - 用户昵称，可为空
    nickname = Column(String(50), nullable=True)

    # avatar 列 - 用户头像地址，可为空
    avatar = Column(String(255), nullable=True)
    
    # created_at 列 - 账号创建时间
    # server_default=func.now(): 使用数据库服务器的当前时间作为默认值
    # timezone=True: 带时区信息
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # last_login 列 - 最后登录时间
    # nullable=True: 这个字段可以为空（新用户还没登录过）
    last_login = Column(DateTime(timezone=True), nullable=True)
    
    # status 列 - 账号状态
    # default="enabled": 默认状态为启用
    # 可选值: "enabled"（启用）, "disabled"（禁用）
    status = Column(String(10), default="enabled", index=True)


# =============================================================================
# AIChatRecord AI对话记录模型
# =============================================================================
class AIChatRecord(Base):
    """
    AI对话记录表模型 - 存储用户与AI的对话历史
    
    数据库表名: ai_chat_records
    
    字段说明:
        record_id: 记录ID（主键）
        user_id: 用户ID（关联到 users 表）
        conversation_id: 对话ID（暂未使用）
        session_id: 会话ID（用于区分不同的对话会话）
        question: 用户的问题
        question_type: 问题类型（预留字段）
        answer: AI的回答
        response_time: 响应时间（自动设置）
        is_stream: 是否使用流式响应（0/1）
        feedback: 用户反馈（like/dislike 等）
    """
    
    # 定义数据库表名
    __tablename__ = "ai_chat_records"
    
    # record_id 列 - 记录ID，主键
    record_id = Column(Integer, primary_key=True, index=True)
    
    # user_id 列 - 用户ID
    # 这个字段关联到 users 表的 id 列
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    # conversation_id 列 - 对话ID
    # 预留字段，目前固定为 1
    conversation_id = Column(Integer, nullable=False)
    
    # session_id 列 - 会话ID
    # 用于把多条消息归类到同一个对话中
    # 同一个 session_id 的消息属于同一次对话
    session_id = Column(String(255), nullable=False, index=True)
    
    # question 列 - 用户的问题
    # 最大长度 1000 字符
    question = Column(String(1000), nullable=False)
    
    # question_type 列 - 问题类型
    # 预留字段，用于区分不同类型的问题（如 text, image, code 等）
    question_type = Column(String(50), nullable=False)
    
    # answer 列 - AI的回答
    # 最大长度 5000 字符
    answer = Column(String(5000), nullable=False)
    
    # response_time 列 - 响应时间
    # 自动设置为数据库服务器当前时间
    response_time = Column(DateTime(timezone=True), server_default=func.now())
    
    # is_stream 列 - 是否使用流式响应
    # 0 = 非流式响应，1 = 流式响应
    is_stream = Column(Integer, default=0)

    # feedback 列 - 用户对 AI 回答的反馈
    feedback = Column(String(20), nullable=True)

    __table_args__ = (
        Index("idx_ai_chat_user_session_time", "user_id", "session_id", "response_time"),
    )


# =============================================================================
# Level 关卡配置模型
# =============================================================================
class Level(Base):
    """
    关卡配置表模型 - 存储少儿 Python 学习关卡内容

    数据库表名: levels
    """

    __tablename__ = "levels"

    id = Column(Integer, primary_key=True, index=True)
    level_name = Column(String(100), nullable=False)
    title = Column(String(150), nullable=False)
    description = Column(String(255), nullable=False)
    initial_code = Column(Text, nullable=False)
    expected_output = Column(Text, nullable=False)
    steps = Column(Text, nullable=False)
    hint = Column(Text, nullable=True)
    theme = Column(String(50), nullable=True)
    sort_order = Column(Integer, nullable=False, default=0, index=True)
    status = Column(String(10), nullable=False, default="enabled", index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


# =============================================================================
# UserProgress 用户关卡进度模型
# =============================================================================
class UserProgress(Base):
    """
    用户关卡进度表模型 - 记录每个用户在每个关卡的学习状态

    数据库表名: user_progress
    """

    __tablename__ = "user_progress"

    progress_id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    level_id = Column(Integer, ForeignKey("levels.id"), nullable=False, index=True)
    status = Column(String(20), nullable=False, default="not_started", index=True)
    score = Column(Integer, nullable=False, default=0)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("user_id", "level_id", name="uq_user_progress_user_level"),
        Index("idx_user_progress_user_status", "user_id", "status"),
    )


# =============================================================================
# StudyRecord 学习打卡记录模型
# =============================================================================
class StudyRecord(Base):
    """
    学习打卡记录表模型 - 记录用户每日学习打卡内容

    数据库表名: study_records
    """

    __tablename__ = "study_records"

    record_id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    study_date = Column(Date, nullable=False)
    content = Column(Text, nullable=False)
    duration = Column(Integer, nullable=False, default=0)
    mood = Column(String(20), nullable=False, default="一般")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("user_id", "study_date", name="uq_study_records_user_date"),
        Index("idx_study_records_user_date", "user_id", "study_date"),
    )


# =============================================================================
# CodeExecutionRecord 代码执行记录模型
# =============================================================================
class CodeExecutionRecord(Base):
    """
    代码执行记录表模型 - 保存用户运行和提交代码的结果

    数据库表名: code_execution_records
    """

    __tablename__ = "code_execution_records"

    execution_id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    level_id = Column(Integer, ForeignKey("levels.id"), nullable=True, index=True)
    code = Column(Text, nullable=False)
    output = Column(Text, nullable=True)
    errors = Column(Text, nullable=True)
    execution_time = Column(Float, nullable=False, default=0)
    success = Column(Boolean, nullable=False, default=False, index=True)
    is_submission = Column(Boolean, nullable=False, default=False)
    passed = Column(Boolean, nullable=False, default=False, index=True)
    executed_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    __table_args__ = (
        Index("idx_code_execution_user_level_time", "user_id", "level_id", "executed_at"),
    )
