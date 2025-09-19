# 相关工具

本页面介绍与 PageEyes Agent 相关的工具、库和框架，这些工具可以帮助您更好地使用和扩展 PageEyes Agent 的功能。

## 核心依赖工具

### 1. Playwright

[Playwright](https://playwright.dev/) 是 PageEyes Agent 用于 Web 自动化的核心组件，提供了强大的浏览器自动化能力。

**主要特性：**

- 支持多种浏览器（Chromium、Firefox、WebKit）
- 强大的元素选择器和交互能力
- 自动等待元素可交互
- 网络请求拦截和修改
- 模拟移动设备和地理位置

**在 PageEyes Agent 中的应用：**

PageEyes Agent 使用 Playwright 执行 Web 端的所有自动化操作，包括页面导航、元素点击、文本输入和滚动等。通过 Playwright 的 API，PageEyes Agent 能够模拟真实用户的浏览器交互行为。

### 2. OmniParser V2

[OmniParser V2](https://huggingface.co/microsoft/OmniParser-v2.0) 是 PageEyes Agent 用于解析 UI 元素的核心模型，由微软开发。

**主要特性：**

- 基于计算机视觉的 UI 元素识别
- 无需传统的元素定位器（如 XPath、CSS 选择器）
- 能够理解 UI 元素的语义和上下文关系
- 支持多种平台（Web、移动端）的界面解析

**在 PageEyes Agent 中的应用：**

PageEyes Agent 使用 OmniParser V2 分析屏幕截图，识别和定位 UI 元素，使得自然语言指令能够准确地映射到实际的 UI 操作上。这是实现自然语言驱动 UI 自动化的关键技术。


### 3. Android 调试桥 (ADB)

[Android Debug Bridge (ADB)](https://developer.android.com/tools/adb) 是一个用于与 Android 设备通信的命令行工具。

**主要特性：**

- 设备连接和管理
- 应用安装和卸载
- 文件传输
- 屏幕截图和录制
- 模拟用户输入（点击、滑动、文本输入）

**在 PageEyes Agent 中的应用：**

PageEyes Agent 使用 ADB 执行 Android 端的所有自动化操作，包括应用启动、元素点击、文本输入和滑动等。通过 ADB 的命令，PageEyes Agent 能够模拟真实用户在 Android 设备上的交互行为。


### 4. Pydantic AI

[Pydantic AI](https://ai.pydantic.dev/) 是一个用于构建 AI 应用的框架，提供了类型安全的数据验证和序列化功能。

**主要特性：**

- 基于 Pydantic 的数据模型
- 支持 LLM 工具调用
- 提供 Agent 框架
- 类型安全的 API

**在 PageEyes Agent 中的应用：**

PageEyes Agent 基于 Pydantic AI 框架开发，使用其 Agent 和工具调用功能来实现自然语言指令的解析和执行。这使得 PageEyes Agent 能够以结构化的方式处理复杂的 UI 自动化任务。

## 扩展工具

### 1. 腾讯云对象存储（COS）

[腾讯云对象存储（COS）](https://cloud.tencent.com/product/cos) 是腾讯云提供的无目录层次结构、无数据格式限制，可容纳海量数据且支持 HTTP/HTTPS 协议访问的分布式存储服务。

**主要特性：**

- 高可靠性（数据设计可靠性 99.999999999%）
- 高可用性（服务设计可用性 99.995%）
- 丰富的 SDK 和工具支持
- 兼容 S3 API
- 多种存储类型（标准存储、低频存储、归档存储等）
- 数据处理能力（图片处理、音视频转码、文档数据处理等）

**在 PageEyes Agent 中的应用：**

PageEyes Agent 支持使用腾讯云 COS 作为存储方案，适合已经使用腾讯云生态的团队。通过 COS，可以存储和管理测试过程中产生的各类资源，如屏幕截图、录制视频、测试报告等。COS 的高可靠性和可用性保证了测试资源的安全存储，同时其丰富的数据处理能力也为测试结果的后处理提供了便利。


### 2. MinIO

[MinIO](https://min.io/) 是一个高性能的对象存储服务，兼容 Amazon S3 API。

**主要特性：**

- 高性能对象存储
- 兼容 S3 API
- 支持多种存储后端
- 可扩展性强

**在 PageEyes Agent 中的应用：**

PageEyes Agent 也支持使用 MinIO 存储测试报告、屏幕截图和录制的视频，方便团队共享和查看测试结果。



## 开发工具

### 1. Loguru

[Loguru](https://github.com/Delgan/loguru) 是一个用于 Python 的日志记录库，提供了简单而强大的日志功能。

**主要特性：**

- 简洁的 API
- 彩色输出
- 异常追踪
- 日志轮转
- 结构化日志

**在 PageEyes Agent 中的应用：**

PageEyes Agent 使用 Loguru 记录执行过程中的各种信息，包括操作步骤、错误信息和调试信息，方便用户排查问题和优化自动化脚本。


### 2. HTTPX

[HTTPX](https://www.python-httpx.org/) 是一个现代化的 Python HTTP 客户端，支持异步请求。

**主要特性：**

- 同步和异步 API
- 支持 HTTP/2
- 类似 Requests 的 API
- 强大的超时和重试机制

**在 PageEyes Agent 中的应用：**

PageEyes Agent 使用 HTTPX 与 OmniParser V2 服务和其他 API 进行通信，处理 HTTP 请求和响应。


## 相关资源

- [Playwright 文档](https://playwright.dev/docs/intro)
- [OmniParser V2 模型页面](https://huggingface.co/microsoft/OmniParser-v2.0)
- [Android 调试桥 (ADB) 文档](https://developer.android.com/tools/adb)
- [Pydantic AI 文档](https://ai.pydantic.dev/)
- [腾讯云对象存储 文档](https://cloud.tencent.com/document/product/436)
- [MinIO 文档](https://min.io/docs/minio/container/index.html)