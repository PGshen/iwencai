# 数据抓取与IM推送服务

一个基于 FastAPI 的数据抓取和 IM 消息推送服务。

## 功能特点

- 🔍 **数据抓取**：支持 GET/POST 请求，可配置 Cookie、Headers、自定义解析代码
- 📢 **消息推送**：支持飞书、Discord Webhook 推送
- 📦 **Docker 部署**：一键启动

## 快速开始

### 本地开发

```bash
# 可选：创建虚拟环境
python -m venv .venv && source .venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 启动服务
uvicorn app.main:app --reload
```

服务启动后访问：
- API 文档：http://localhost:8000/docs
- 健康检查：http://localhost:8000/health
- Web 界面（模板渲染）：http://localhost:8000/

### Docker 部署

```bash
# 构建并启动
docker-compose up -d

# 查看日志
docker-compose logs -f
```

Docker 默认映射端口为 8000（见 [docker-compose.yml](file:///Users/peng/Me/Ai/iwencai/docker-compose.yml)），并挂载本地数据目录 `./data` 到容器 `/app/data`。

## API 接口

### 数据抓取

```bash
POST /api/scrape
```

```json
{
    "url": "https://api.example.com/data",
    "method": "GET",
    "headers": {"Cookie": "session=xxx"},
    "parser_code": "def parse(data):\n    return data['items']"
}
```

### 消息推送

```bash
POST /api/push
```

```json
{
    "channel": "feishu",
    "webhook_url": "https://open.feishu.cn/open-apis/bot/v2/hook/xxx",
    "message": {
        "title": "通知标题",
        "content": "消息内容",
        "type": "text"
    }
}
```

### 配置管理

```bash
GET    /api/configs/scrape      # 获取抓取配置列表
POST   /api/configs/scrape      # 创建抓取配置
GET    /api/configs/push        # 获取推送配置列表
POST   /api/configs/push        # 创建推送配置
```

### 定时任务

```bash
GET    /api/schedules           # 获取定时任务列表
POST   /api/schedules           # 创建定时任务
DELETE /api/schedules/{id}      # 删除定时任务
```

## 使用示例

```python
import requests

# 1. 抓取数据
resp = requests.post("http://localhost:8000/api/scrape", json={
    "url": "https://api.example.com/data",
    "method": "GET",
    "headers": {"Cookie": "your_cookie"},
    "parser_code": """
def parse(data):
    return [item['name'] for item in data['results']]
"""
})
data = resp.json()['data']

# 2. 本地处理
result = f"共 {len(data)} 条数据"

# 3. 推送消息
requests.post("http://localhost:8000/api/push", json={
    "channel": "feishu",
    "webhook_url": "your_webhook_url",
    "message": {"content": result, "type": "text"}
})
```

## 目录结构

```
iwencai/
├── app/
│   ├── main.py           # 应用入口
│   ├── config.py         # 配置管理
│   ├── database.py       # 数据库
│   ├── models/           # 数据模型
│   ├── routers/          # API 路由
│   ├── services/         # 业务服务
│   └── utils/            # 工具函数
├── data/                 # 数据目录
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

## 环境与配置

- 环境变量示例：见 [.env.example](file:///Users/peng/Me/Ai/iwencai/.env.example)
  - DEBUG：是否开启调试
  - DATABASE_URL：数据库连接（默认 SQLite：`sqlite+aiosqlite:///./data/app.db`）
  - PARSER_TIMEOUT：解析代码超时时间（秒）
- 应用启动会自动确保存在 `data/` 目录并初始化数据库（见 [main.py](file:///Users/peng/Me/Ai/iwencai/app/main.py#L16-L24)、[database.py](file:///Users/peng/Me/Ai/iwencai/app/database.py)）

## 数据库与迁移

- 默认使用 SQLite，文件位于 `./data/app.db`
- 如需补充历史表结构，执行迁移脚本：  
  ```bash
  python migrate_db.py
  ```
  参考脚本：[migrate_db.py](file:///Users/peng/Me/Ai/iwencai/migrate_db.py)

## 静态与模板

- 静态资源目录：`/static`（对应项目 [static](file:///Users/peng/Me/Ai/iwencai/static)）
- 模板目录：`app/templates`，首页路由 `/` 使用 `index.html`（见 [main.py](file:///Users/peng/Me/Ai/iwencai/app/main.py#L62-L66)）

## 版本控制说明

- 项目已配置 [.gitignore](file:///Users/peng/Me/Ai/iwencai/.gitignore)，当前忽略整个 [data](file:///Users/peng/Me/Ai/iwencai/data) 目录及数据库文件
- 若需提交示例数据或小型测试数据，请调整 `.gitignore` 规则或将数据放入非忽略目录
