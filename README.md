## PageEyes Agent

![](https://img.shields.io/badge/build-passing-brightgreen)
![](https://img.shields.io/badge/python-12-blue?logo=python)
<a href="https://github.com/tencentmusic/page-eyes-agent/blob/master/LICENSE">
<img src="https://img.shields.io/badge/License-MIT-blue?labelColor=d4eaf7" alt="License">
</a>
<a href="https://pypi.org/project/page-eyes/">
<img alt="Version" src="https://img.shields.io/pypi/v/page-eyes.svg?labelColor=d4eaf7&label=version&color=blue">
</a>
![](https://img.shields.io/badge/Web-supported-brightgreen?logo=googlechrome&logoColor=white)
![](https://img.shields.io/badge/Android-supported-brightgreen?logo=android&logoColor=white)
![](https://img.shields.io/badge/iOS-supported-brightgreen?logo=apple&logoColor=white)
![](https://img.shields.io/badge/HarmonyOS_Next-supported-brightgreen?logo=harmonyos&logoColor=white)
![](https://img.shields.io/badge/Electron-supported-brightgreen?logo=electron&logoColor=white)

---

**Documentation**: [PageEyes Agent](https://tencentmusic.github.io/page-eyes-agent/)

---

<p align="center">
    <img src="./docs/img/logo-ai.png" height="100" alt="" />
</p>

PageEyes Agent 是基于 [Pydantic AI](https://ai.pydantic.dev/#why-use-pydanticai) 框架开发的一个轻量级 UI Agent，
其中元素信息感知能力依靠 [OmniParserV2](https://huggingface.co/microsoft/OmniParser-v2.0) 模型，整个 Agent
的优势在于不依赖视觉语言大模型，
即使小参数的 LLM 也能胜任路径规划能力，同时支持多平台（Web、Android、HarmonyOS、iOS、Electron 桌面应用），目前主要包含以下功能：

1. 完全由自然语言指令驱动，无需编写脚本，既可实现自动化测试，UI巡检等任务
2. 跨平台、跨端支持，在 Python 环境中安装 page-eyes 库和配置 OmniParser 服务后即可开始多个平台的自动化任务
3. 支持多种大模型接入，包括DeepSeek、OpenAI、千问等，默认使用 DeepSeek V3 模型，后续会支持更多大模型接入
4. 可通过自然语言进行断言，并生成详细的执行日志和报告，方便测试人员查看执行过程和结果

<p align="center">
<img title="" src="https://cdn-y.tencentmusic.com/1e1e171e6dd06b6808489acd381db735.png" alt="" width="610" data-align="center">
</p>

## 安装

您可以通过 [pip](https://pypi.org/project/page-eyes/) 安装

```shell
pip install page-eyes
```

或者克隆项目源码安装

```shell
git clone https://github.com/tencentmusic/page-eyes-agent.git
cd page-eyes-agent
uv sync  # 安装依赖
```

## 快速开始
配置环境变量，可在项目根目录下创建一个 `.env` 文件，配置项可参考 [.env.example](.env.example)

### 一、轻量化部署: 配好模型, 插上手机就能跑
`.env` 中配置VLM模型，以 qwen3-vl-plus 为例
```shell
OPENAI_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
OPENAI_API_KEY=xxx-xxx-xxx-xxx-xxx
AGENT_MODEL_TYPE=vlm
AGENT_MODEL=openai:qwen3-vl-plus
```
编写测试脚本，以 Android 端为例（需先安装好 adb）
```python
import asyncio

from page_eyes.agent import AndroidAgent


async def main():
    # 移动端
    ui_agent = await AndroidAgent.create()

    report = await ui_agent.run( "打开QQ音乐, 点击乐馆，点击排行，点击腾讯音乐榜，检测当前页面出现由你榜")

if __name__ == "__main__":
    asyncio.run(main())
```

### 二、多源融合(视觉小模型+大模型)部署
OmniParser + LLM

`.env` 中配置模型，以 deepseek v3 为例, OmiParser 需提前[部署](docs/getting-started/installation.md)
```shell
OPENAI_BASE_URL=https://api.deepseek.com/v1
OPENAI_API_KEY=xxx-xxx-xxx-xxx-xxx
AGENT_MODEL=openai:deepseek-chat
OMNI_BASE_URL=http://127.0.0.1:8000
```
测试脚本参考上面已有示例

### 三、更多配置
| 环境变量             | 默认值                         | 说明                                   |
|:-----------------|-----------------------------|--------------------------------------|
| AGENT_MODEL      | openai:deepseek-chat        | 使用的AI模型，当前设置为 deepseek-chat          |
| AGENT_DEBUG      | False                       | 是否启用调试模式                             |
| BROWSER_HEADLESS | False                       | WebAgent 启动浏览器时是否使用无头模式              |
| AGENT_MODEL_TYPE | llm                         | Agent 使用的模型类型，支持 llm 和 vlm           |
| OMNI_BASE_URL    | http://127.0.0.1:8000       | OmniParser API的服务端点, vlm 不需要配置该项     |
| OPENAI_BASE_URL  | https://api.deepseek.com/v1 | 模型 API 的服务端点                         |
| OPENAI_API_KEY   | xxx-xxx-xxx                 | 模型 API 所需的认证密钥                       |
| IOS_WDA_URL      | -                           | iOS WebDriverAgent 服务地址（仅 iOS 自动化需要） |

> vlm 模型支持：`glm-4.6v`  `qwen3-vl-plus` 等
>
> 如：AGENT_MODEL=openai:qwen3-vl-plus 

使用腾讯云COS服务（与MinIO二选一），可选，不配置则会使用 base64 保存图片

| 环境变量           | 默认值 | 说明                  |
|:---------------|-----|---------------------|
| COS_SECRET_ID  | -   | 腾讯云COS服务的Secret ID  |
| COS_SECRET_KEY | -   | 腾讯云COS服务的Secret Key |
| COS_ENDPOINT   | -   | 腾讯云COS服务的 endpoint  |
| COS_BUCKET     | -   | 腾讯云COS服务的 bucket    |

使用MinIO服务（与腾讯云COS二选一），可选，不配置则会使用 base64 保存图片

| 环境变量             | 默认值 | 说明                            |
|:-----------------|-----|-------------------------------|
| MINIO_ENDPOINT   | -   | MinIO 端点 host:port            |
| MINIO_ACCESS_KEY | -   | 您在后台创建的 Access Key            |
| MINIO_SECRET_KEY | -   | 创建 Access Key 时会生成 SECRET_KEY |
| MINIO_BUCKET     | -   | 您在后台创建的 Bucket                |

[详细部署参考](docs/getting-started/installation.md)

**使用示例**

根据需要操作的设备类型可以导入对应的 Agent 类

```python
from page_eyes.agent import WebAgent, AndroidAgent, HarmonyAgent, IOSAgent, ElectronAgent

...
```

| Agent Class  | 支持类型                               |
|--------------|------------------------------------|
| WebAgent     | Web/H5浏览器操作，依赖 Playwright 和 Chrome |
| AndroidAgent | Android 移动端操作，依赖 adb               |
| HarmonyAgent | 鸿蒙 Next 移动端操作，依赖 hdc               |
| IOSAgent     | iOS 移动端操作，依赖 facebook-wda          |

```python
import asyncio

from page_eyes.agent import WebAgent, AndroidAgent


async def main():
    # Web 端
    ui_agent = await WebAgent.create(simulate_device='iPhone 15 Pro')

    # 移动端
    # ui_agent = await AndroidAgent.create(serial='android-udid')

    report = await ui_agent.run("""
            - 打开 url "https://yobang.tencentmusic.com/chart/uni-chart/rankList/"
            - 点击"查找icon"
            - 在搜索输入框中输入"小美满"
            - 点击"小美满> "
            - 点击"日榜"
            """)


if __name__ == "__main__":
    asyncio.run(main())
```

### 四、使用 Skills
Agent 默认会加载当前 `./skills` 目录下的技能（如有），也可以自定义其他目录的skills
```python
import asyncio

from page_eyes.agent import AndroidAgent


async def main():
    # 移动端
    ui_agent = await AndroidAgent.create(skills_dirs=["./skills", "./more-skills"])

    report = await ui_agent.run( "打开QQ音乐, 点击乐馆，点击排行，点击腾讯音乐榜，检测当前页面出现由你榜")

if __name__ == "__main__":
    asyncio.run(main())
```


更多示例请参考[示例代码](https://github.com/tencentmusic/page-eyes-agent/tree/master/tests)

## 贡献指南

1. 检查现有 issues 或提交新 issue 来讨论功能想法或缺陷
2. 在GitHub上Fork[代码仓库](https://github.com/tencentmusic/page-eyes-agent)，基于主分支创建修改分支（或从其创建新分支）
3. 编写测试用例：通过测试验证缺陷已修复或新功能符合预期
4. 添加更新日志：按规范提交[更新日志](./CHANGELOG.md)
5. 完善文档：优化文档（增强细节、提升可读性等）

## 如有需要，加入我们的交流群

![](./docs/about/contact_qr.png)