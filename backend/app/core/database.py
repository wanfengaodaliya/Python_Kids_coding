"""
================================================================================
数据库配置模块
================================================================================
这个文件负责配置和管理数据库连接，主要功能：
1. 从环境变量加载配置
2. 创建数据库引擎（Engine）- 负责与数据库通信
3. 创建会话工厂（SessionLocal）- 负责生成数据库会话
4. 创建基类（Base）- 所有数据模型的基类
5. 提供依赖项函数（get_db）- 用于 FastAPI 路由获取数据库会话

SQLAlchemy 核心概念：
- Engine: 数据库连接的入口点，管理连接池
- Session: 与数据库交互的工作区，用于执行查询和提交事务
- Base: 声明式基类，所有模型类都继承自它

作者: AIGC Project Team
创建日期: 2025
================================================================================
"""

# 导入 SQLAlchemy 核心组件
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv  # 用于从 .env 文件加载环境变量


# =============================================================================
# 加载环境变量
# =============================================================================
# 从项目根目录的 .env 文件中加载环境变量
# 如果没有 .env 文件，这一步不会报错，只是不会加载任何变量
load_dotenv()


# =============================================================================
# 数据库连接配置
# =============================================================================
# 数据库连接 URL 格式：
# mysql+pymysql://用户名:密码@主机:端口/数据库名
# 
# 说明：
# - mysql+pymysql: 使用 MySQL 数据库，pymysql 作为驱动
# - root: 数据库用户名
# - 1234: 数据库密码
# - localhost:3306: 数据库主机和端口（MySQL 默认端口是 3306）
# - ai_coding_platform: 数据库名称
#
# 注意：生产环境建议从环境变量读取这些敏感信息，不要硬编码在代码中！
DATABASE_URL = "mysql+pymysql://root:1234@localhost:3306/ai_coding_platform"


# =============================================================================
# 创建数据库引擎
# =============================================================================
# Engine 是 SQLAlchemy 的核心对象，负责：
# 1. 管理数据库连接池
# 2. 执行 SQL 语句
# 3. 处理数据库方言（不同数据库的语法差异）
#
# create_engine() 参数说明：
# - pool_pre_ping: 每次使用连接前先测试连接是否有效（避免"MySQL server has gone away"错误）
# - pool_recycle: 连接在池中存活的秒数（超过这个时间会被回收）
# - echo: 是否打印执行的 SQL 语句（调试时设为 True）
engine = create_engine(DATABASE_URL)


MYSQL_COMPATIBILITY_COLUMNS = {
    "users": {
        "nickname": "VARCHAR(50) NULL",
        "avatar": "VARCHAR(255) NULL",
    },
    "ai_chat_records": {
        "feedback": "VARCHAR(20) NULL",
    },
}


def build_missing_mysql_column_statements(existing_columns):
    """
    Build ALTER TABLE statements for nullable columns added after early local DBs
    were already created. This keeps development databases compatible with the
    current SQLAlchemy models without introducing a full migration framework.
    """
    statements = []
    for table_name, required_columns in MYSQL_COMPATIBILITY_COLUMNS.items():
        table_columns = existing_columns.get(table_name, set())
        for column_name, column_definition in required_columns.items():
            if column_name not in table_columns:
                statements.append(
                    f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_definition}"
                )
    return statements


def ensure_mysql_schema_compatibility(db_engine):
    """
    Add newly introduced nullable columns to existing MySQL tables.

    Base.metadata.create_all() creates missing tables but intentionally does not
    modify existing ones, so local databases created before model changes need
    this small compatibility step.
    """
    if db_engine.dialect.name != "mysql":
        return

    inspector = inspect(db_engine)
    existing_columns = {}
    for table_name in MYSQL_COMPATIBILITY_COLUMNS:
        if inspector.has_table(table_name):
            existing_columns[table_name] = {
                column["name"] for column in inspector.get_columns(table_name)
            }

    statements = build_missing_mysql_column_statements(existing_columns)
    if not statements:
        return

    with db_engine.begin() as connection:
        for statement in statements:
            connection.execute(text(statement))


# =============================================================================
# 创建会话工厂
# =============================================================================
# SessionLocal 是一个工厂函数，用于创建新的 Session 对象
# Session 是我们与数据库交互的主要接口
#
# 参数说明：
# - autocommit=False: 不自动提交事务（需要手动调用 db.commit()）
# - autoflush=False: 不自动刷新（需要手动调用 db.flush()）
# - bind=engine: 绑定到上面创建的数据库引擎
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# =============================================================================
# 创建声明式基类
# =============================================================================
# Base 是所有数据模型类的基类
# 我们定义的每个表模型（如 User, AIChatRecord）都要继承自 Base
# Base 会自动跟踪这些类，并提供 ORM 功能
Base = declarative_base()


# =============================================================================
# 依赖项：获取数据库会话
# =============================================================================
def get_db():
    """
    FastAPI 依赖项函数 - 获取数据库会话
    
    这个函数用于 FastAPI 路由中，通过 Depends(get_db) 注入数据库会话
    
    使用方法：
        from fastapi import Depends
        from sqlalchemy.orm import Session
        
        @app.get("/some-endpoint")
        def some_endpoint(db: Session = Depends(get_db)):
            # 使用 db 进行数据库操作
            ...
    
    工作原理：
    1. 创建一个新的数据库会话
    2. 使用 yield 将会话提供给路由函数
    3. 路由函数执行完毕后，自动关闭会话（无论是否发生异常）
    
    Yield 说明：
    - yield 前面的代码：在路由函数执行前运行（创建会话）
    - yield 后面的代码：在路由函数执行后运行（关闭会话）
    """
    # 创建新的数据库会话
    db = SessionLocal()
    try:
        # yield 把会话提供给调用者（FastAPI 路由函数）
        # 路由函数会在这个 yield 处暂停，等待路由执行完毕
        yield db
    finally:
        # 无论路由函数是否成功执行，都会关闭会话
        # 这很重要，防止数据库连接泄漏
        db.close()
