---
title: 安装指南
---

# 安装指南

PageEyes Agent 是一个轻量级 UI 自动化框架，支持通过自然语言指令驱动 Web 和 Android 平台的 UI 自动化任务。本指南将展示如何正确安装和配置 PageEyes Agent 及其依赖项。


## 系统要求

在安装 PageEyes Agent 之前，请确保系统满足以下要求：

- **操作系统**：支持 Windows、macOS 和 Linux
- **Python 版本**：Python 3.12 或更高版本


## 安装方法

### 方法 1：使用 pip 安装（推荐）

最简单的方法：

```bash
pip install page-eyes
```

### 方法 2：从源代码安装

也可以从源代码安装：

```bash
git clone https://github.com/tencentmusic/page-eyes-agent.git
cd page-eyes-agent
pip install -e .
```

## 依赖项安装

PageEyes Agent 依赖于几个关键组件才能正常工作。以下是安装和配置这些依赖项的步骤：

### 1. Playwright 浏览器驱动

[Playwright](https://playwright.dev/) 是 PageEyes Agent 用于 Web 自动化的核心组件。安装后，需要下载浏览器驱动：

```bash
# 安装 Playwright 浏览器驱动
playwright install

# 如果只需要特定浏览器，可以指定
playwright install chromium
```

### 2. OmniParser V2 服务

[OmniParser V2](https://huggingface.co/microsoft/OmniParser-v2.0) 是 PageEyes Agent 用于解析 UI 元素的核心模型。

#### 方法 1：直接使用 PageEyes Agent 搭建好的OmniParser V2 服务（推荐）

```bash
# （必需）设置环境变量， 调用OmniParser V2 服务时使用
AGENT_OMNI_KEY=test-UfcWMpXW
```

#### 方法 2：使用 Docker 部署

```bash
docker pull xxxxx/omniparser:v2.0
docker run -d -p 8000:8000 xxxxx/omniparser:v2.0
```

#### 方法 3：从 Hugging Face 部署

1. 访问 [OmniParser V2 模型页面](https://huggingface.co/microsoft/OmniParser-v2.0)
2. 按照说明下载模型并部署服务
3. 确保服务在 `http://localhost:8000` 或其他可访问的地址上运行
4. 设置环境变量 `OMNI_BASE_URL` 为服务地址
5. 设置环境变量 `OMNI_KEY` 为服务的 API 密钥


### 3. Android 调试桥 (ADB)（仅移动端需要）

如果您计划在 Android 设备上运行自动化任务，需要安装 ADB：

#### Windows

1. 下载 [Android SDK Platform Tools](https://developer.android.com/tools/releases/platform-tools)
2. 解压缩并将路径添加到系统环境变量

#### macOS

```bash
brew install android-platform-tools
```

#### Linux

```bash
sudo apt-get install android-tools-adb
```

### 4. MinIO（可选，用于报告存储）

如果您需要存储和共享测试报告，可以配置 MinIO：

```bash
# 使用 Docker 安装 MinIO
docker run -p 9000:9000 -p 9001:9001 \
  -e "MINIO_ROOT_USER=minioadmin" \
  -e "MINIO_ROOT_PASSWORD=minioadmin" \
  -v /path/to/data:/data \
  minio/minio server /data --console-address ":9001"
```

## 验证安装

安装完成后，您可以运行以下简单测试来验证 PageEyes Agent 是否正确安装：

```python
import asyncio
from page_eyes.agent import WebAgent

async def test_installation():
    try:
        # 创建 Web Agent 实例
        agent = await WebAgent.create(simulate_device='Desktop Chrome')
        print("✅ PageEyes Agent 安装成功！")

    except Exception as e:
        print(f"❌ 安装验证失败: {str(e)}")

if __name__ == "__main__":
    asyncio.run(test_installation())
```

## 配置

### 配置文件

PageEyes Agent 支持通过环境变量进行配置：

```bash
# --- Agent 行为配置 ---
# (可选) 指定使用的模型, 格式为 '提供商:模型名'。例如: openai:gpt-4o, 不指定时默认使用deepseek-v3
AGENT_MODEL=openai:your-model-name
# (调试) 是否开启调试模式，会打印更详细的日志
AGENT_DEBUG=True
# (调试) 浏览器是否以非无头模式运行 (False 表示会显示浏览器界面)
AGENT_HEADLESS=False
# (调试) 是否在日志中打印 Agent 的决策图节点
AGENT_LOG_GRAPH_NODE=True

# --- 必填: 服务依赖配置 ---
# 你的 OmniParser 服务 API Key
AGENT_OMNI_KEY="your_omni_parser_api_key_here"


# 你的大模型服务基础 URL (例如 LiteLLM 代理地址或云服务商提供的地址)
OPENAI_BASE_URL="https://your.llm.provider.com/v1/"
# 你的大模型服务 API Key
OPENAI_API_KEY="your_llm_api_key_here"


# --- 可选: 报告存储配置 (minIO) ---
# 如果不需要将报告上传到对象存储，可以忽略以下配置
xxxx_SECRET_ID="your_minio_secret_id"
xxxx_SECRET_KEY="your_minio_secret_key"
```


## 故障排除

如果您在安装过程中遇到问题，请尝试以下解决方案：


### 常见问题

1. **Playwright 安装失败**
   ```bash
   # 尝试手动安装浏览器
   python -m playwright install --force
   ```

2. **OmniParser 连接问题**
   ```bash
   # 如果是您自行部署的服务，请检查 OmniParser 服务是否正在运行
   curl http://localhost:8000/health
   ```

3. **ADB 设备未识别**
   ```bash
   # 列出已连接的设备
   adb devices
   
   # 重启 ADB 服务
   adb kill-server
   adb start-server
   ```

### 获取帮助

如果您仍然遇到问题，可以通过以下方式获取帮助：

- 在 [GitHub Issues](https://github.com/tencentmusic/page-eyes-agent/issues) 提交问题
- 查阅 [常见问题解答](../faq/index.md)
- 加入我们的 [开发者社区](https://github.com/tencentmusic/page-eyes-agent#community)


## 下一步

成功安装 PageEyes Agent 后，您可以：

- 查看 [快速开始指南](demo.md) 了解如何创建您的第一个自动化任务
- 探索 [核心概念](../guides/core-concepts.md) 深入了解 PageEyes Agent 的工作原理
- 查看 [API 参考](../api/index.md) 获取详细的 API 文档