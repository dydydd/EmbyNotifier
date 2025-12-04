# GitHub 上传和自动构建指南

## 第一步：上传代码到 GitHub

### 1. 初始化 Git 仓库（如果还没有）

```bash
git init
git add .
git commit -m "Initial commit: Emby Telegram Notifier"
```

### 2. 添加远程仓库

```bash
git remote add origin https://github.com/dydydd/EmbyNotifier.git
```

### 3. 推送到 GitHub

```bash
# 如果仓库是空的，直接推送
git branch -M main
git push -u origin main
```

如果仓库已有内容（比如 README），需要先拉取：

```bash
git pull origin main --allow-unrelated-histories
# 解决可能的冲突后
git push -u origin main
```

## 第二步：配置 GitHub Secrets

1. 进入 GitHub 仓库页面
2. 点击 **Settings** → **Secrets and variables** → **Actions**
3. 点击 **New repository secret**，添加以下两个 Secrets：

   - **Name**: `DOCKER_USERNAME`
     **Value**: 你的 Docker Hub 用户名

   - **Name**: `DOCKER_PASSWORD`
     **Value**: 你的 Docker Hub 密码或访问令牌（推荐使用访问令牌）

### 获取 Docker Hub 访问令牌

1. 登录 [Docker Hub](https://hub.docker.com/)
2. 点击右上角头像 → **Account Settings** → **Security**
3. 点击 **New Access Token**
4. 创建令牌并复制（只显示一次，请保存好）

## 第三步：触发自动构建

### 方式一：推送代码（自动触发）

```bash
git add .
git commit -m "Update code"
git push origin main
```

### 方式二：创建标签（发布版本）

```bash
git tag v1.0.0
git push origin v1.0.0
```

### 方式三：手动触发

1. 进入 GitHub 仓库页面
2. 点击 **Actions** 标签
3. 选择 **Build and Push Docker Image** workflow
4. 点击 **Run workflow** → **Run workflow**

## 第四步：验证构建

1. 进入 **Actions** 标签页
2. 查看最新的 workflow 运行状态
3. 构建成功后，镜像会自动推送到 Docker Hub

## 使用构建的镜像

构建完成后，可以在 Docker Hub 查看镜像：
- 地址：https://hub.docker.com/r/dydydd/embynotifier

使用镜像：

```bash
docker pull dydydd/embynotifier:latest

docker run -d \
  --name emby-notify \
  -p 5000:5000 \
  -e TELEGRAM_BOT_TOKEN=your_bot_token_here \
  -e TELEGRAM_CHAT_ID=your_chat_id_here \
  -e AGGREGATION_DELAY=10 \
  --restart unless-stopped \
  dydydd/embynotifier:latest
```

## 镜像标签说明

- `dydydd/embynotifier:latest` - 主分支最新构建
- `dydydd/embynotifier:main` - 主分支构建
- `dydydd/embynotifier:v1.0.0` - 版本标签构建
- `dydydd/embynotifier:v1.0` - 主版本标签构建

## 故障排除

### 构建失败

1. 检查 GitHub Secrets 是否正确配置
2. 检查 Docker Hub 用户名和密码是否正确
3. 查看 Actions 日志了解具体错误

### 镜像未推送

1. 确认 `DOCKER_USERNAME` 和 `DOCKER_PASSWORD` Secrets 已配置
2. 确认 Docker Hub 账户有权限推送镜像
3. 检查 workflow 文件中的镜像名称是否正确

