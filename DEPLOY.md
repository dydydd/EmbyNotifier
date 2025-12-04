# 部署说明

## GitHub Actions 自动构建

项目已配置 GitHub Actions，会自动构建 Docker 镜像并推送到 Docker Hub。

### 配置要求

在 GitHub 仓库的 Settings → Secrets and variables → Actions 中配置以下 Secrets：

- `DOCKER_USERNAME`: Docker Hub 用户名
- `DOCKER_PASSWORD`: Docker Hub 密码或访问令牌

### 触发条件

以下情况会自动触发构建：

1. **推送到主分支**：推送到 `main` 或 `master` 分支
2. **创建标签**：创建以 `v` 开头的标签（如 `v1.0.0`）
3. **手动触发**：在 GitHub Actions 页面手动运行 workflow

### 镜像标签

- `latest`: 主分支的最新构建
- `main`: 主分支构建
- `v1.0.0`: 版本标签构建
- `v1.0`: 主版本标签构建
- `main-<sha>`: 包含 commit SHA 的标签

### 使用构建的镜像

```bash
# 拉取最新镜像
docker pull dydydd/embynotifier:latest

# 运行容器
docker run -d \
  --name emby-notify \
  -p 5000:5000 \
  -e TELEGRAM_BOT_TOKEN=your_bot_token_here \
  -e TELEGRAM_CHAT_ID=your_chat_id_here \
  dydydd/embynotifier:latest
```

## 本地构建

如果需要本地构建镜像：

```bash
# 构建镜像
docker build -t embynotifier .

# 运行容器
docker run -d \
  --name emby-notify \
  -p 5000:5000 \
  -e TELEGRAM_BOT_TOKEN=your_bot_token_here \
  -e TELEGRAM_CHAT_ID=your_chat_id_here \
  embynotifier
```

