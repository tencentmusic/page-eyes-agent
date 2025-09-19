# 开发环境设置

本文档提供了设置 PageEyes Agent 开发环境的详细指南，帮助贡献者快速搭建一个完整的开发环境。

## 系统要求

PageEyes Agent 支持以下操作系统：

- **Linux**：Ubuntu 20.04+, CentOS 7+
- **macOS**：10.15 (Catalina) 及以上
- **Windows**：Windows 10 及以上 (WSL2 推荐)

## 前置依赖

在开始之前，请确保您的系统已安装以下软件：

1. **Python 3.12+**：PageEyes Agent 需要 Python 3.12 或更高版本
2. **pip**：Python 包管理工具
3. **Git**：版本控制系统
4. **Node.js**：用于文档站点构建 (可选)

### 针对 Web 自动化

- **Chromium** 或 **Chrome**：Playwright 将自动安装所需的浏览器

### 针对 Android 自动化

- **ADB**：Android 调试桥
- **Android SDK Platform Tools**：包含 ADB 和其他工具

## 安装步骤

### 1. 克隆代码库

```bash
# 克隆主仓库
git clone https://github.com/tencentmusic/page-eyes-agent.git
cd page-eyes-agent

# 或者克隆您的 fork (如果您计划贡献代码)
git clone https://github.com/YOUR_USERNAME/page-eyes-agent.git
cd page-eyes-agent
```

### 2. 创建虚拟环境

推荐使用 uv 来管理虚拟环境和依赖，uv 是一个快速的 Python 包管理器和虚拟环境工具：

```bash
# 安装 uv (如果尚未安装)
curl -sSf https://install.ultraviolet.rs | sh

# 创建虚拟环境
uv venv

# 激活虚拟环境 (Linux/macOS)
source .venv/bin/activate

# 激活虚拟环境 (Windows)
.venv\Scripts\activate
```

### 3. 安装依赖

```bash
# 使用 uv 安装项目依赖
uv pip install -e ".[dev]"

# 安装 Playwright 浏览器
playwright install chromium
```


### 4. 配置 OmniParser 服务

PageEyes Agent 依赖 OmniParser 服务进行元素解析。您可以选择以下方式之一：

#### 选项 1：使用官方 OmniParser 服务

在环境变量中配置：

```bash
# Linux/macOS
export AGENT_OMNI_KEY="test-UfcWMpXW"

# Windows
set AGENT_OMNI_KEY=test-UfcWMpXW
```


#### 选项 2：自行部署 OmniParser 服务

1. 从 [Hugging Face](https://huggingface.co/microsoft/OmniParser-v2.0) 下载 OmniParser 模型
2. 按照模型页面的说明部署服务
3. 配置环境变量：

```bash
# Linux/macOS
export AGENT_OMNI_BASE_URL="http://your.omniparser.service:8000"

# Windows
set AGENT_OMNI_BASE_URL=http://your.omniparser.service:8000
```

### 5. 配置大模型服务

PageEyes Agent 支持多种大模型，默认使用 DeepSeek V3。配置环境变量：

```bash
# Linux/macOS
export OPENAI_BASE_URL="https://your.llm.provider.com/v1/"
export OPENAI_API_KEY="your_llm_api_key_here"

# Windows
set OPENAI_BASE_URL=https://your.llm.provider.com/v1/
set OPENAI_API_KEY=your_llm_api_key_here
```

### 6. 配置存储服务 (可选)

如果需要存储测试报告和截图，可以配置腾讯云 COS 或 MinIO：

```bash
# 腾讯云 COS (推荐)
export COS_SECRET_ID="your_cos_secret_id"
export COS_SECRET_KEY="your_cos_secret_key"

# 或 MinIO
export MINIO_ACCESS_KEY="your_minio_access_key"
export MINIO_SECRET_KEY="your_minio_secret_key"
export MINIO_ENDPOINT="your_minio_endpoint"
export MINIO_BUCKET="your_minio_bucket"
export MINIO_SECURE="True"
```

## 验证安装

运行以下命令验证开发环境是否正确设置：

```bash
# 运行单元测试
pytest tests/unit

# 运行简单的 Web 自动化示例
python examples/web_simple.py
```

## 开发工具配置

### VSCode 配置

推荐使用 VSCode 进行开发，以下是推荐的扩展和设置：

1. **Python 扩展**：提供 Python 语言支持
2. **Pylance**：Python 语言服务器
3. **Black Formatter**：代码格式化
4. **isort**：导入排序
5. **Flake8**：代码风格检查
6. **Mypy**：类型检查

创建 `.vscode/settings.json` 文件：

```json
{
    "python.linting.enabled": true,
    "python.linting.flake8Enabled": true,
    "python.linting.mypyEnabled": true,
    "python.formatting.provider": "black",
    "editor.formatOnSave": true,
    "editor.codeActionsOnSave": {
        "source.organizeImports": true
    },
    "python.testing.pytestEnabled": true
}
```

### Git 钩子 (可选)

使用 pre-commit 设置 Git 钩子，确保提交前代码符合规范：

```bash
# 安装 pre-commit
pip install pre-commit

# 设置 Git 钩子
pre-commit install
```

## 文档开发

如果您计划贡献文档，需要安装额外的依赖：

```bash
# 安装文档依赖
pip install -e ".[docs]"

# 启动本地文档服务器
mkdocs serve
```

访问 http://localhost:8000 查看文档站点。

## 故障排除

### 常见问题

1. **Playwright 浏览器安装失败**

   尝试手动安装：
   ```bash
   PLAYWRIGHT_BROWSERS_PATH=0 playwright install chromium
   ```

2. **ADB 设备连接问题**

   检查设备连接和权限：
   ```bash
   adb devices -l
   ```

3. **OmniParser 服务连接失败**

   检查网络连接和服务状态：
   ```bash
   curl -I http://your.omniparser.service:8000/health
   ```

### 获取帮助

如果您遇到其他问题，可以：

- 查阅 [常见问题文档](../faq/troubleshooting.md)
- 在 GitHub Issues 中搜索或提问
- 联系项目维护者：aidenmo@tencent.com

## 下一步

成功设置开发环境后，您可以：

1. 阅读 [代码风格指南](code-style.md) 了解编码规范
2. 查看 [路线图](../roadmap.md) 了解项目计划
3. 浏览 [GitHub Issues](https://github.com/tencentmusic/page-eyes-agent/issues) 寻找可以贡献的任务

祝您开发愉快！