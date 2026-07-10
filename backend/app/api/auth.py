

# 导入必要的库
from fastapi import APIRouter, HTTPException, status, Depends
from sqlalchemy.orm import Session
from datetime import timedelta
from app.core.database import get_db  # 数据库依赖
from app.core.auth import (  # 认证工具
    verify_password,
    get_password_hash,
    create_access_token,
    create_refresh_token,
    get_current_user,
)
from app.models.user import User  # 用户模型
from pydantic import BaseModel  # 数据验证模型



router = APIRouter()


# =============================================================================
# 请求和响应模型（Pydantic）
# =============================================================================

class UserCreate(BaseModel):

    username: str  # 用户名
    password: str  # 密码
    phone: str  # 手机号


class UserLogin(BaseModel):

    username: str  # 用户名
    password: str  # 密码


class UserResponse(BaseModel):

    id: int
    username: str
    phone: str


class Token(BaseModel):

    access_token: str  # 访问令牌
    refresh_token: str  # 刷新令牌
    token_type: str = "bearer"  # 令牌类型


class PasswordResetRequest(BaseModel):

    phone: str  # 手机号


class PasswordReset(BaseModel):

    phone: str  # 手机号
    new_password: str  # 新密码


class AuthResponse(BaseModel):

    code: int = 200  # 状态码
    msg: str = "操作成功"  # 提示消息
    data: dict  # 数据


# =============================================================================
# 用户注册接口
# =============================================================================
@router.post("/auth/register")
async def register(user: UserCreate, db: Session = Depends(get_db)):

    # 1. 检查用户名是否已存在
    existing_user = db.query(User).filter(User.username == user.username).first()
    if existing_user:
        return AuthResponse(
            code=400,
            msg="用户名已存在",
            data={}
        )
    
    # 2. 检查手机号是否已存在
    existing_phone = db.query(User).filter(User.phone == user.phone).first()
    if existing_phone:
        return AuthResponse(
            code=400,
            msg="手机号已被注册",
            data={}
        )
    
    # 3. 对密码进行哈希加密
    # get_password_hash() 使用 Argon2 算法
    hashed_password = get_password_hash(user.password)
    
    # 4. 创建新用户记录
    new_user = User(
        username=user.username,
        password=hashed_password,  # 存储哈希后的密码，不是明文！
        phone=user.phone
    )
    db.add(new_user)  # 添加到数据库会话
    db.commit()  # 提交事务（真正保存到数据库）
    db.refresh(new_user)  # 刷新对象，获取数据库自动生成的 id
    
    # 5. 返回成功响应
    return AuthResponse(
        code=201,  # 201 = Created
        msg="注册成功",
        data={
            "id": new_user.id,
            "username": new_user.username,
            "phone": new_user.phone
        }
    )


# =============================================================================
# 用户登录接口
# =============================================================================
@router.post("/auth/login")
async def login(user: UserLogin, db: Session = Depends(get_db)):

    # 1. 根据用户名查找用户
    db_user = db.query(User).filter(User.username == user.username).first()
    
    # 2. 验证用户是否存在，密码是否正确
    # verify_password() 会比较明文密码和哈希密码
    if not db_user or not verify_password(user.password, db_user.password):
        # 使用 HTTPException 抛出标准 HTTP 错误
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误"
        )
    
    # 3. 检查账号状态
    if db_user.status == "disabled":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="账号已被禁用"
        )
    
    # 4. 生成 JWT token
    # access_token: 有效期较短（默认30分钟），用于 API 调用
    # refresh_token: 有效期较长（默认7天），用于获取新的 access_token
    access_token = create_access_token(data={"sub": db_user.username})
    refresh_token = create_refresh_token(data={"sub": db_user.username})
    
    # 5. 返回响应
    return AuthResponse(
        code=200,
        msg="登录成功",
        data={
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer"
        }
    )


# =============================================================================
# 密码重置请求接口（发送验证码）
# =============================================================================
@router.post("/auth/reset-password-request")
async def reset_password_request(request: PasswordResetRequest, db: Session = Depends(get_db)):

    # 检查手机号是否已注册
    user = db.query(User).filter(User.phone == request.phone).first()
    if not user:
        return AuthResponse(
            code=404,
            msg="手机号未注册",
            data={}
        )
    
    # TODO: 这里可以添加发送短信验证码的逻辑
    # 例如：调用阿里云短信、腾讯云短信等 API
    # 验证码存储到 Redis，设置 5 分钟过期
    
    return AuthResponse(
        code=200,
        msg="密码重置请求已接收，请检查手机验证码",
        data={}
    )


# =============================================================================
# 密码重置确认接口（设置新密码）
# =============================================================================
@router.post("/auth/reset-password")
async def reset_password(reset: PasswordReset, db: Session = Depends(get_db)):

    # 检查手机号是否存在
    user = db.query(User).filter(User.phone == reset.phone).first()
    if not user:
        return AuthResponse(
            code=404,
            msg="手机号未注册",
            data={}
        )
    
    # TODO: 这里应该验证验证码
    # 例如：从 Redis 读取验证码，比较用户输入的是否正确
    
    # 对新密码进行哈希加密
    hashed_password = get_password_hash(reset.new_password)
    user.password = hashed_password  # 更新密码
    db.commit()  # 保存到数据库
    
    return AuthResponse(
        code=200,
        msg="密码重置成功",
        data={}
    )


# =============================================================================
# 获取当前用户信息接口
# =============================================================================
@router.get("/auth/me")
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    return AuthResponse(
        code=200,
        msg="获取成功",
        data={
            "id": current_user.id,
            "username": current_user.username,
            "phone": current_user.phone,
            "nickname": current_user.nickname,
            "avatar": current_user.avatar,
        }
    )
