# 少儿 Python 闯关学习平台

一个面向少儿和 Python 初学者的闯关式编程学习平台。项目采用前后端分离架构，前端使用 React + Vite，后端使用 FastAPI + SQLAlchemy + MySQL，并通过本地大模型接口提供 AI 智能辅导能力。

## 项目功能

- 用户认证：支持注册、登录、密码重置、JWT 登录态和 Argon2 密码哈希。
- 关卡学习：提供 Python 基础关卡、学习路线、进度展示和关卡解锁。
- 代码运行：后端提供代码执行接口、AST 安全检查、受限运行环境和错误提示。
- AI 辅导：对接本地大模型服务，支持 SSE 流式回复、历史会话和会话列表。
- 学习记录：支持日历打卡、学习内容、学习时长和学习状态记录。
- 系统设置：支持昵称、代码字号、护眼模式、AI 回答风格和后端地址配置。

## 技术栈

| 层级 | 技术 |
| --- | --- |
| 前端 | React 19、Vite 7 |
| 后端 | FastAPI、Uvicorn |
| 数据库 | MySQL、SQLAlchemy |
| 认证 | JWT、Argon2 |
| AI 服务 | 本地大模型兼容接口、SSE 流式响应 |
| 代码执行 | Python AST 安全检查、沙箱执行 |

## 目录结构

```text
.
├── app/                  # FastAPI 后端业务模块
│   ├── api/              # 认证、AI、代码运行、学习管理接口
│   ├── core/             # 数据库和认证核心配置
│   ├── models/           # SQLAlchemy 数据模型
│   └── services/         # 学习服务与代码沙箱
├── frontend/             # React + Vite 前端
│   ├── src/              # 前端页面、API 封装、关卡数据和样式
│   └── images/           # 页面图片与 tabbar 图标资源
├── main.py               # 后端启动入口
└── requirements.txt      # 后端依赖
```

## 后端运行

1. 创建并激活 Python 环境。
2. 安装依赖：

```bash
pip install -r requirements.txt
```

3. 确认 MySQL 已启动，并创建数据库：

```sql
CREATE DATABASE ai_coding_platform DEFAULT CHARACTER SET utf8mb4;
```

4. 启动后端服务：

```bash
python main.py
```

默认接口地址：

```text
http://localhost:8000
```

健康检查：

```text
http://localhost:8000/api/v1/health
```

## 前端运行

进入前端目录并安装依赖：

```bash
cd frontend
npm install
npm run dev
```

生产构建：

```bash
npm run build
```

如需调整后端接口地址，可在前端设置页的开发者配置中修改 baseUrl，默认值为：

```text
http://localhost:8000/api/v1
```

## 主要接口

| 接口 | 方法 | 说明 |
| --- | --- | --- |
| `/api/v1/auth/register` | POST | 用户注册 |
| `/api/v1/auth/login` | POST | 用户登录 |
| `/api/v1/auth/me` | GET | 获取当前用户信息 |
| `/api/v1/levels` | GET | 获取关卡列表 |
| `/api/v1/progress` | GET | 获取学习进度 |
| `/api/v1/code/run` | POST | 运行或提交 Python 代码 |
| `/api/v1/ai/chat` | POST | AI 智能辅导 |
| `/api/v1/ai/sessions` | GET | 获取 AI 会话列表 |
| `/api/v1/study-records` | GET/POST | 学习打卡记录 |

## 数据库设计

项目核心数据表包括：

- `users`：用户信息。
- `levels`：关卡配置。
- `user_progress`：用户关卡进度。
- `study_records`：学习打卡记录。
- `ai_chat_records`：AI 对话记录。
- `code_execution_records`：代码运行记录。

## 验证命令

后端语法检查：

```bash
python -m compileall -q .
```

前端构建检查：

```bash
cd frontend
npm run build
```

安全和逻辑诊断脚本：

```bash
python test_security_check.py
python test_logic_check.py
```

## 后续优化

- 将 JWT 密钥、数据库连接等敏感配置迁移到环境变量。
- 补充验证码校验和管理员权限控制。
- 将诊断脚本整理为标准 pytest 自动化测试。
- 强化代码沙箱隔离，进一步限制 CPU、内存和运行时间。
- 优化 AI 非流式回复、会话查询性能和通关判定规则。
