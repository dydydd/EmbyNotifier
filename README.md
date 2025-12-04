# Emby 入库通知 Telegram Bot

接收 Emby webhook 通知并发送到 Telegram 的程序。

[![Docker Image](https://img.shields.io/docker/pulls/dydydd/embynotifier?style=flat-square)](https://hub.docker.com/r/dydydd/embynotifier)
[![GitHub](https://img.shields.io/github/license/dydydd/EmbyNotifier?style=flat-square)](https://github.com/dydydd/EmbyNotifier)

## 功能特性

- ✅ 接收 Emby `library.new` 事件
- ✅ 支持电影和剧集通知
- ✅ **剧集通知聚合**：同一部剧的多集会在指定时间内聚合为一条通知
- ✅ **电影通知**：电影通知立即发送，不聚合
- ✅ 自动识别画质（720p/1080p/4K）和 HDR 信息
- ✅ 显示评分、类型、文件大小等信息
- ✅ 提供 TMDB、IMDb、豆瓣链接
- ✅ 使用 Jinja2 模板引擎，易于自定义
- ✅ 模块化设计，便于维护和扩展

## 项目结构

```
notiofy/
├── app.py                      # Flask 主应用
├── config.py                  # 配置管理模块
├── parser.py                  # Emby 数据解析模块
├── telegram_client.py         # Telegram 客户端模块
├── templates.py               # 消息模板管理模块
├── notification_aggregator.py # 通知聚合器模块
├── utils.py                   # 工具函数模块
├── requirements.txt           # Python 依赖
├── Dockerfile                 # Docker 镜像构建文件
├── docker-compose.yml         # Docker Compose 配置
├── .dockerignore              # Docker 忽略文件
├── config.example.env         # 配置示例文件（可选）
└── README.md                  # 说明文档
```

## 安装

### 方式一：使用 Docker（推荐）

#### 使用预构建镜像（最简单）

```bash
docker run -d \
  --name emby-notify \
  -p 5000:5000 \
  -e TELEGRAM_BOT_TOKEN=your_bot_token_here \
  -e TELEGRAM_CHAT_ID=your_chat_id_here \
  -e AGGREGATION_DELAY=10 \
  --restart unless-stopped \
  dydydd/embynotifier:latest
```

#### 使用 Docker Compose

1. 克隆或下载项目

2. 使用 Docker Compose 运行：
```bash
# 设置环境变量
export TELEGRAM_BOT_TOKEN=your_bot_token_here
export TELEGRAM_CHAT_ID=your_chat_id_here
export AGGREGATION_DELAY=10  # 可选，默认 10 秒

# 启动服务
docker-compose up -d
```

或者修改 `docker-compose.yml` 使用预构建镜像：
```yaml
services:
  emby-notify:
    image: dydydd/embynotifier:latest
    # ... 其他配置
```

3. 查看日志：
```bash
docker-compose logs -f
# 或
docker logs -f emby-notify
```

### 方式二：直接运行 Python

1. 克隆或下载项目

2. 安装依赖：
```bash
pip install -r requirements.txt
```

3. 设置环境变量：
```bash
# Linux/Mac
export TELEGRAM_BOT_TOKEN=your_bot_token_here
export TELEGRAM_CHAT_ID=your_chat_id_here
export AGGREGATION_DELAY=10

# Windows PowerShell
$env:TELEGRAM_BOT_TOKEN="your_bot_token_here"
$env:TELEGRAM_CHAT_ID="your_chat_id_here"
$env:AGGREGATION_DELAY="10"
```

4. 运行：
```bash
python app.py
```

## 配置说明

### 必需的环境变量

- `TELEGRAM_BOT_TOKEN`: 从 [@BotFather](https://t.me/BotFather) 获取
- `TELEGRAM_CHAT_ID`: 你的 Telegram Chat ID（可通过 [@userinfobot](https://t.me/userinfobot) 获取）

### 可选的环境变量

- `WEBHOOK_HOST`: Webhook 服务监听地址，默认 `0.0.0.0`
- `WEBHOOK_PORT`: Webhook 服务端口，默认 `5000`
- `AGGREGATION_DELAY`: 聚合延迟时间（秒），默认 `10` 秒。同一部剧的多集通知会在此时间内聚合为一条。设置为 `0` 则禁用聚合。

### Docker Compose 环境变量文件

你也可以创建 `.env` 文件（Docker Compose 会自动读取）：

```bash
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here
AGGREGATION_DELAY=10
```

然后运行：
```bash
docker-compose up -d
```

## Emby 配置

在 Emby 服务器中配置 Webhook：

1. 进入 **设置** → **网络** → **Webhooks**
2. 添加新的 Webhook URL：
   - 如果使用 Docker：`http://your-server-ip:5000/webhook`
   - 如果在同一台机器：`http://localhost:5000/webhook` 或 `http://127.0.0.1:5000/webhook`
3. 选择事件：**Library New**（或 `library.new`）

### Docker 网络配置

如果 Emby 和通知服务都在 Docker 中运行，可以使用 Docker 网络：

```yaml
# 在 docker-compose.yml 中添加网络
networks:
  emby-network:
    external: true
```

然后 Emby 的 webhook URL 可以使用容器名：
```
http://emby-notify:5000/webhook
```

## API 端点

- `GET /` - 服务信息
- `GET /health` - 健康检查
- `POST /webhook` - 接收 Emby webhook

## 消息模板

消息使用 Jinja2 模板引擎，你可以修改 `templates.py` 中的 `TemplateManager` 类来自定义消息格式。该类包含：
- `_create_title_template()`: 标题模板
- `_create_text_template()`: 正文模板

## 示例消息

### 单集通知（或电影通知）

```
🎬 神雕侠侣 (1995) S01E02 已入库

📢 媒体库：Emby
⭐️ 评分：7.6/10
📺 媒体类型：剧集
🏷 归类：Action / Adventure / Drama
🖼 质量：2160p (4K)
📂 文件：1 个
💾 大小：2.52 GB
🍿 TMDB ID：12345

📝 简介：儒文双英在过的洞中又吃又住，过要他们付帐。愁跟三夫妇来洞穴，要杀元女泄愤，三不敌，中针倒地，过用计使各人脱险，但最后二女被愁掳去。过不慎接触毒针，欧阳锋来救他，但要过认他作父，后更传蛤蟆功给杨过。郭靖、黄蓉遇过，蓉认出他是杨康之子，又因武三娘中毒死去，靖便把过和儒文兄弟带回桃花岛，希望过能在岛上长大成人。

🌐 链接： 🔗 [TMDB](https://www.themoviedb.org/tv/12345) | 🎬 [豆瓣](https://www.douban.com/search?cat=1002&q=tt8189092) | 🌟 [IMDb](https://www.imdb.com/title/tt8189092/)
```

### 聚合通知（多集聚合）

```
🎬 神雕侠侣 (1995) S01E01-E05 已入库（共 5 集）

📢 媒体库：Emby
⭐️ 评分：7.6/10
📺 媒体类型：剧集
🏷 归类：Action / Adventure / Drama
🖼 质量：2160p (4K)
📂 文件：5 个
💾 总大小：12.60 GB
🍿 TMDB ID：12345

📝 简介：儒文双英在过的洞中又吃又住，过要他们付帐。愁跟三夫妇来洞穴，要杀元女泄愤，三不敌，中针倒地，过用计使各人脱险，但最后二女被愁掳去。过不慎接触毒针，欧阳锋来救他，但要过认他作父，后更传蛤蟆功给杨过。郭靖、黄蓉遇过，蓉认出他是杨康之子，又因武三娘中毒死去，靖便把过和儒文兄弟带回桃花岛，希望过能在岛上长大成人。

🌐 链接： 🔗 [TMDB](https://www.themoviedb.org/tv/12345) | 🎬 [豆瓣](https://www.douban.com/search?cat=1002&q=tt8189092) | 🌟 [IMDb](https://www.imdb.com/title/tt8189092/)
```

## 聚合通知说明

### 工作原理

- **剧集通知**：当同一部剧的多集在短时间内（默认 10 秒）入库时，会自动聚合为一条通知
  - 例如：`神雕侠侣 (1995) S01E01-E05 已入库（共 5 集）`
  - 聚合通知会显示总文件数、总大小等信息
  
- **电影通知**：电影通知立即发送，不进行聚合
  - 每部电影入库时都会立即发送一条独立通知

### 配置聚合延迟

通过环境变量 `AGGREGATION_DELAY` 可以调整聚合延迟时间：
- 默认值：`10` 秒
- 设置为 `0`：禁用聚合，所有通知立即发送
- 建议值：`5-15` 秒，根据你的入库速度调整

## 注意事项

- 确保服务器防火墙允许访问 webhook 端口
- 如果使用内网，需要配置端口转发或使用内网穿透工具
- 程序只处理 `library.new` 事件，其他事件会被忽略
- 聚合通知使用线程定时器，确保程序正常关闭时所有通知都会被发送

## Docker 镜像

项目已配置 GitHub Actions 自动构建 Docker 镜像并推送到 Docker Hub。

### 自动构建

每次推送到 `main` 或 `master` 分支，或创建新标签时，会自动：
1. 构建 Docker 镜像（支持 linux/amd64 和 linux/arm64）
2. 推送到 Docker Hub: `dydydd/embynotifier`

### 使用预构建镜像

```bash
# 拉取最新镜像
docker pull dydydd/embynotifier:latest

# 运行容器
docker run -d \
  --name emby-notify \
  -p 5000:5000 \
  -e TELEGRAM_BOT_TOKEN=your_bot_token_here \
  -e TELEGRAM_CHAT_ID=your_chat_id_here \
  -e AGGREGATION_DELAY=10 \
  --restart unless-stopped \
  dydydd/embynotifier:latest
```

### 本地构建

如果需要本地构建镜像：

```bash
docker build -t embynotifier .
docker run -d \
  --name emby-notify \
  -p 5000:5000 \
  -e TELEGRAM_BOT_TOKEN=your_bot_token_here \
  -e TELEGRAM_CHAT_ID=your_chat_id_here \
  embynotifier
```

更多部署说明请查看 [DEPLOY.md](DEPLOY.md)

## 许可证

MIT

