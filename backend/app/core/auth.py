"""
================================================================================
用户认证与授权模块
================================================================================
这个文件负责处理用户密码加密、JWT 令牌生成和验证，主要功能：
1. 密码哈希（使用 Argon2 算法，比 bcrypt 更安全）
2. 密码验证
3. 创建访问令牌（Access Token）- 用于 API 认证，有效期较短
4. 创建刷新令牌（Refresh Token）- 用于获取新的访问令牌，有效期较长

JWT（JSON Web Token）说明：
- JWT 是一种用于身份验证的标准
- 它包含用户信息（如用户名），用密钥签名后发送给客户端
- 客户端后续请求时携带 JWT，服务器验证签名后确认用户身份
- JWT 不需要在服务器端存储会话，适合分布式系统

Argon2 说明：
- Argon2 是目前最安全的密码哈希算法之一
- 它是 Password Hashing Competition（PHC）的获胜者
- 抗 GPU 破解，抗彩虹表攻击

作者: AIGC Project Team
创建日期: 2025
================================================================================
"""

# 导入必要的库
from argon2 import PasswordHasher  # Argon2 密码哈希库
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt  # JWT（JSON Web Token）处理库
from sqlalchemy.orm import Session
from datetime import datetime, timedelta  # 日期时间处理
from typing import Optional  # 类型提示
from app.core.database import get_db


# =============================================================================
# 密码加密配置
# =============================================================================
# 创建密码哈希器实例
# Argon2 会自动处理 salt（盐值）和其他参数，不需要手动管理
ph = PasswordHasher()


# =============================================================================
# JWT 配置
# =============================================================================
# 注意：生产环境一定要把这些配置放到环境变量中，不要硬编码！
# SECRET_KEY 是用于签名 JWT 的密钥，泄露会导致安全问题
SECRET_KEY = "your-secret-key-here"  # JWT 签名密钥（请修改为随机字符串）
ALGORITHM = "HS256"  # JWT 签名算法（HS256 是 HMAC-SHA256）

# 令牌过期时间配置
ACCESS_TOKEN_EXPIRE_MINUTES = 30  # 访问令牌有效期：30 分钟
REFRESH_TOKEN_EXPIRE_DAYS = 7  # 刷新令牌有效期：7 天
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


# =============================================================================
# 密码验证函数
# =============================================================================
def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    验证用户输入的密码是否正确
    
    参数:
        plain_password (str): 用户输入的明文密码
        hashed_password (str): 数据库中存储的哈希密码
        
    返回:
        bool: 密码正确返回 True，错误返回 False
        
    说明:
        - Argon2 的 verify 方法会自动从哈希中提取 salt 和参数
        - 即使两个用户使用相同密码，哈希值也会不同（因为 salt 不同）
        - 即使密码错误，也应该花费相近的时间返回（防止时序攻击）
    """
    try:
        # 验证密码
        # ph.verify() 会在密码错误时抛出异常
        return ph.verify(hashed_password, plain_password)
    except Exception:
        # 任何异常都返回 False（密码错误）
        # 包括：密码不匹配、哈希格式错误等
        return False


# =============================================================================
# 密码哈希函数
# =============================================================================
def get_password_hash(password: str) -> str:
    """
    将明文密码转换为哈希值（用于存储到数据库）
    
    参数:
        password (str): 用户输入的明文密码
        
    返回:
        str: 加密后的密码哈希字符串
        
    说明:
        - 永远不要在数据库中存储明文密码！
        - Argon2 会自动生成随机的 salt（盐值）
        - 相同密码每次哈希结果都不同，但都能正确验证
    """
    # ph.hash() 会自动：
    # 1. 生成随机 salt
    # 2. 使用 Argon2 算法哈希密码
    # 3. 将 salt、参数和哈希值组合成一个字符串
    return ph.hash(password)


# =============================================================================
# 创建访问令牌函数
# =============================================================================
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    创建 JWT 访问令牌（Access Token）
    
    参数:
        data (dict): 要编码到令牌中的数据（通常包含用户名）
            例如: {"sub": "username"}
        expires_delta (Optional[timedelta]): 可选的过期时间增量
            如果不提供，使用默认的 ACCESS_TOKEN_EXPIRE_MINUTES
            
    返回:
        str: 编码后的 JWT 令牌字符串
        
    JWT 结构说明:
        JWT 由三部分组成，用点分隔：
        1. Header（头部）- 包含算法和类型
        2. Payload（载荷）- 包含用户数据和过期时间
        3. Signature（签名）- 用于验证令牌未被篡改
        
    使用示例:
        token = create_access_token(data={"sub": "alice"})
        # 客户端需要在请求头中携带: Authorization: Bearer <token>
    """
    # 复制输入数据，避免修改原字典
    to_encode = data.copy()
    
    # 计算过期时间
    if expires_delta:
        # 如果提供了自定义过期时间，使用它
        expire = datetime.utcnow() + expires_delta
    else:
        # 否则使用默认过期时间（30分钟）
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    # 将过期时间添加到载荷中
    # "exp" 是 JWT 标准声明，表示过期时间
    to_encode.update({"exp": expire})
    
    # 编码生成 JWT
    # 使用 SECRET_KEY 和 ALGORITHM 进行签名
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    
    return encoded_jwt


# =============================================================================
# 创建刷新令牌函数
# =============================================================================
def create_refresh_token(data: dict) -> str:
    """
    创建 JWT 刷新令牌（Refresh Token）
    
    参数:
        data (dict): 要编码到令牌中的数据
        
    返回:
        str: 编码后的 JWT 刷新令牌
        
    刷新令牌说明:
        - 刷新令牌有效期更长（7天）
        - 用于在访问令牌过期后获取新的访问令牌
        - 用户不需要重新登录就能继续使用应用
        - 可以在 payload 中添加 "type": "refresh" 来区分令牌类型
        
    使用流程:
        1. 用户登录 → 获取 access_token 和 refresh_token
        2. access_token 过期 → 使用 refresh_token 获取新的 access_token
        3. refresh_token 过期 → 用户需要重新登录
    """
    # 复制输入数据
    to_encode = data.copy()
    
    # 计算过期时间（7天后）
    expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    
    # 添加过期时间和令牌类型标识
    to_encode.update({
        "exp": expire,
        "type": "refresh"  # 标记这是刷新令牌
    })
    
    # 编码生成 JWT
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    
    return encoded_jwt


def decode_token_subject(token: str) -> Optional[str]:
    """解析 JWT 中的 sub 字段，失败或过期时返回 None。"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        subject = payload.get("sub")
        return subject if isinstance(subject, str) and subject else None
    except JWTError:
        return None


def get_current_user(token: Optional[str] = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    """FastAPI 依赖项：根据 Bearer Token 获取当前登录用户。"""
    from app.models.user import User

    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="请先登录")

    username = decode_token_subject(token)
    if not username:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="登录状态无效")

    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户不存在")
    if user.status == "disabled":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="账号已被禁用")
    return user


def get_demo_or_current_user(token: Optional[str] = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    """优先使用登录用户；没有 token 时退回到 id=1，方便课堂演示旧接口。"""
    from app.models.user import User

    if token:
        username = decode_token_subject(token)
        if username:
            user = db.query(User).filter(User.username == username).first()
            if user and user.status != "disabled":
                return user

    user = db.query(User).filter(User.id == 1).first()
    if user:
        return user

    user = User(username="demo", password=get_password_hash("demo123456"), phone="13800138000", nickname="演示用户")
    db.add(user)
    db.commit()
    db.refresh(user)
    return user
