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

#### 方法 1：如您已部署好 OmniParser V2 服务，则只需要在你的项目中配置环境变量

```bash
# （必需）设置环境变量， 调用 OmniParser V2 服务时使用
AGENT_OMNI_BASE_URL=http://host:port
```

#### 方法 2：使用 Docker 完整部署，支持 GPU（推荐）或 CPU 设备

1. 拉取镜像并部署服务 
```bash
docker run -d \
  --name omniparser \
  -p 8000:8000 \
  -e COS_SECRET_ID=xxx \
  -e COS_SECRET_KEY=xxx \
  -e COS_ENDPOINT=xxx \
  -e COS_BUCKET=xxx \
  lighthouseac/omniparser:latest
```
> COS_SECRET_ID: 腾讯云COS服务的Secret ID  
> COS_SECRET_KEY: 腾讯云COS服务的Secret Key   
> COS_ENDPOINT: 腾讯云COS服务的 endpoint  
> COS_BUCKET: 腾讯云COS服务的 bucket

如您没有申请 腾讯云COS 服务，也可参考第4步快速搭建一个开源的对象存储服务，然后执行下面的命令：

```bash
docker run -d \
  --name omniparser \
  -p 8000:8000 \
  -e MINIO_ACCESS_KEY=xxx \
  -e MINIO_SECRET_KEY=xxx \
  -e MINIO_BUCKET=xxx \
  -e MINIO_ENDPOINT=xxx \
  -e MINIO_SECURE=false \
  lighthouseac/omniparser:latest
```



#### 方法 3：从 Hugging Face 部署

1. 访问 [OmniParser V2 模型页面](https://huggingface.co/microsoft/OmniParser-v2.0)
2. 按照说明下载模型并部署服务
3. 确保服务在 `http://localhost:8000` 或其他可访问的地址上运行
4. 设置环境变量 `AGENT_OMNI_BASE_URL` 为服务地址


### 3. Android 调试桥 (ADB)（仅移动端需要）

如果计划在 Android 设备上运行自动化任务，需要安装 ADB：

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
docker run -d \
  --name minio \
  -e "MINIO_ROOT_USER=minioadmin" \
  -e "MINIO_ROOT_PASSWORD=minioadmin" \
  -p 9000:9000 \
  -p 9001:9001 \
  -v /path/to/data:/data \
  minio/minio:RELEASE.2025-04-22T22-12-26Z server /data --console-address ":9001" --address ":9000"
```
`/path/to/data` 为您宿主机上持久化数据的路径

> 注意：安装完后需要进入管理后台分别创建 Access Key 和 Bucket

管理地址: http://host:9001  
```bash
MINIO_ENDPOINT=http://host:9000  
MINIO_ACCESS_KEY=xxx  # 您在后台创建的 Access Key
MINIO_SECRET_KEY=xxx  # 创建 Access Key 时会生成 SECRET_KEY
MINIO_BUCKET=xxx  # 您在后台创建的 Bucket
```

更多配置可参考 [MinIO 开源项目](https://github.com/minio/minio)

## 验证安装

安装完成后，可运行以下简单测试来验证 PageEyes Agent 是否正确安装：

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

PageEyes Agent 采用灵活的配置管理系统，支持通过环境变量、`.env`文件或代码参数进行配置。配置优先级从高到低依次为：代码传入参数 > 环境变量 > `.env`文件 > 默认值。

环境变量

| 环境变量          | 默认值       | 说明                                                                 |
|:------------------|-----------|----------------------------------------------------------------------|
| AGENT_MODEL       | openai:deepseek-v3 | 使用的AI模型，当前设置为deepseek-v3                                  |
| AGENT_DEBUG       | False     | 是否启用调试模式                                                     |
| AGENT_HEADLESS    | False     | 是否使用无头模式                                                     |
| AGENT_LOG_GRAPH_NODE | False     | 是否记录图节点日志                                                   |
| OPENAI_BASE_URL   | https://api.deepseek.com/v1          | DeepSeek API的服务端点                                               |
| OPENAI_API_KEY    | a22a37d7-xxx | 调用DeepSeek API所需的认证密钥                                       |


使用腾讯云COS服务（与MinIO二选一）

| 环境变量 | 默认值 | 说明                                                                 |
|:-----|-----|----------------------------------------------------------------------|
| COS_SECRET_ID     | -   | 腾讯云COS服务的Secret ID                                    |
| COS_SECRET_KEY     | -   | 腾讯云COS服务的Secret Key                                    |
| COS_ENDPOINT     | -   | 腾讯云COS服务的 endpoint                                  |
| COS_BUCKET     | -   | 腾讯云COS服务的 bucket                                  |

使用MinIO服务（与腾讯云COS二选一）

| 环境变量 | 默认值 | 说明                            |
|:-----|-----|-------------------------------|
| MINIO_ENDPOINT     | -   | MinIO 端点 host:port            |
| MINIO_ACCESS_KEY     | -   | 您在后台创建的 Access Key            |
| MINIO_SECRET_KEY     | -   | 创建 Access Key 时会生成 SECRET_KEY |
| MINIO_BUCKET     | -   | 您在后台创建的 Bucket                |


### 1. 核心功能配置

这些配置控制 PageEyes Agent 的基本行为和功能：

```bash
# --- Agent 核心功能配置 ---
# 指定使用的大模型, 格式为 '提供商:模型名'
# 例如: openai:gpt-4o, 不指定时默认使用 openai:deepseek-v3
AGENT_MODEL="openai:your-model-name"

# 浏览器是否以无头模式运行 (True 表示不显示浏览器界面，False 表示显示)
# 默认值: True
AGENT_HEADLESS=False

# 模拟特定设备（可选）
# 可选值: 'iPhone 15', 'iPhone 15 Pro', 'iPhone 15 Pro Max', 'iPhone 6', 'Desktop Chrome' 等
# 不设置则使用默认浏览器配置
AGENT_SIMULATE_DEVICE="Desktop Chrome"
```

### 2. 服务依赖配置

这些配置用于连接 PageEyes Agent 依赖的外部服务：

```bash
# --- OmniParser 服务配置 ---
# OmniParser 服务基础 URL (如果使用自部署服务，需要设置)
# 默认值: http://21.6.91.201:8000
AGENT_OMNI_BASE_URL="http://your.omniparser.service:8000"

# OmniParser 服务 API Key
# 如果使用 PageEyes Agent 官方服务或官方 Docker 镜像，使用以下值:
AGENT_OMNI_KEY="test-UfcWMpXW"
# 如果使用从 Hugging Face 自行部署的 OmniParser 服务，无需设置此项 Key

# --- 大模型服务配置 ---
# 大模型服务基础 URL (例如 LiteLLM 代理地址或云服务商提供的地址)
OPENAI_BASE_URL="https://your.llm.provider.com/v1/"

# 大模型服务 API Key
OPENAI_API_KEY="your_llm_api_key_here"
```

### 3. 存储与调试配置

这些配置用于测试报告存储和调试目的：

```bash
# --- 报告存储配置 ---
# PageEyes Agent 优先使用腾讯云 COS，如未配置则尝试从系统内提取 MinIO配置

# 腾讯云 COS 配置 (推荐)
COS_SECRET_ID="your_cos_secret_id"
COS_SECRET_KEY="your_cos_secret_key"
COS_REGION="ap-guangzhou"  # 默认值，可根据需要修改
COS_ENDPOINT="cos-internal.ap-guangzhou.tencentcos.cn"  # 默认值，可根据需要修改
COS_BUCKET="your_cos_bucket"  # 默认: tme-dev-test-cos-1257943044

# MinIO 配置 (备选)
# 仅当未配置腾讯云 COS 时使用
MINIO_ACCESS_KEY="your_minio_access_key"
MINIO_SECRET_KEY="your_minio_secret_key"
MINIO_ENDPOINT="your_minio_endpoint"  # 例如: minio.example.com:9000
MINIO_BUCKET="your_minio_bucket"
MINIO_REGION="your_minio_region"  # 可选
MINIO_SECURE="False"  # 是否使用 HTTPS，默认 False

# --- 调试配置 ---
# 是否开启调试模式，会打印更详细的日志
# 默认值: False
AGENT_DEBUG=True

# 是否在日志中打印 Agent 的决策图节点
# 默认值: False
AGENT_LOG_GRAPH_NODE=True
```


## 故障排除

如果在安装过程中遇到问题，请尝试以下解决方案：


### 常见问题

1. **Playwright 安装失败**
   ```bash
   # 尝试手动安装浏览器
   python -m playwright install --force
   ```

2. **OmniParser 连接问题**
   ```bash
   # 如果是自行部署的服务，请检查 OmniParser 服务是否正在运行
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

如果你仍然遇到问题，可以通过以下方式获取帮助：

- 在 [GitHub Issues](https://github.com/tencentmusic/page-eyes-agent/issues) 提交问题
- 查阅 [常见问题解答](../faq/faq.md)
- 加入我们的 [开发者社区](https://github.com/tencentmusic/page-eyes-agent#community)


## 下一步

成功安装 PageEyes Agent 后，你可以：

- 查看 [快速开始指南](demo.md) 了解如何创建你的第一个自动化任务
- 探索 [核心概念](../guides/core-concepts.md) 深入了解 PageEyes Agent 的工作原理
- 查看 [API 参考](../api/index.md) 获取详细的 API 文档