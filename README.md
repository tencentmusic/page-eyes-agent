## PageEyes Agent

![](https://img.shields.io/badge/build-passing-brightgreen)
![](https://img.shields.io/badge/python-12-blue?logo=python)
<a href="https://github.com/tencentmusic/page-eyes-agent/blob/master/LICENSE">
    <img src="https://img.shields.io/badge/License-MIT-blue?labelColor=d4eaf7" alt="License">
</a>
<a href="https://pypi.org/project/page-eyes/">
    <img alt="Version" src="https://img.shields.io/pypi/v/page-eyes.svg?labelColor=d4eaf7&label=version&color=blue">
</a>

---

**Documentation**: [PageEyes Agent](https://tencentmusic.github.io/page-eyes-agent/)

---

<p align="center">
    <img src="./docs/img/logo-ai.png" height="100" alt="" />
</p>

PageEyes Agent 是基于 [Pydantic AI](https://ai.pydantic.dev/#why-use-pydanticai) 框架开发的一个轻量级 UI Agent，
其中元素信息感知能力依靠 [OmniParserV2](https://huggingface.co/microsoft/OmniParser-v2.0) 模型，整个 Agent 的优势在于不依赖视觉语言大模型，
即使小参数的 LLM 也能胜任路径规划能力，同时支持多平台（Web、Android），目前主要包含以下功能：

1. 完全由自然语言指令驱动，无需编写脚本，既可实现自动化测试，UI巡检等任务
2. 跨平台、跨端支持，在 Python 环境中安装 page-eyes 库和配置 OmniParser 服务后即可开始 Web、Android 平台的自动化任务，未来还将继续支持iOS平台
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
```python
from page_eyes.agent import WebAgent, MobileAgent
...
```

或者克隆项目源码安装
```shell
git clone https://github.com/tencentmusic/page-eyes-agent.git
cd page-eyes-agent
uv sync  # 安装依赖
```

## 快速开始
配置环境变量

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

[详细部署参考](docs/getting-started/installation.md)

使用示例

```python
import asyncio

from page_eyes.agent import WebAgent, MobileAgent


async def main():
    # Web 端
    ui_agent = await WebAgent.create(simulate_device='iPhone 15 Pro')

    # 移动端
    # ui_agent = await MobileAgent.create(serial='android-udid')

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
更多示例请参考[示例代码](https://github.com/tencentmusic/page-eyes-agent/tree/master/tests)

## 贡献指南
1. 检查现有 issues 或提交新 issue 来讨论功能想法或缺陷
2. 在GitHub上Fork[代码仓库](https://github.com/tencentmusic/page-eyes-agent)，基于主分支创建修改分支（或从其创建新分支）
3. 编写测试用例：通过测试验证缺陷已修复或新功能符合预期
4. 添加更新日志：按规范提交[更新日志](./CHANGELOG.md)
5. 完善文档：优化文档（增强细节、提升可读性等）

## 如有需要，加入我们的交流群
![](./docs/about/contact_qr.png)

[![Star History Chart](https://api.star-history.com/svg?repos=tencentmusic/page-eyes-agent&type=date&legend=top-left)](https://www.star-history.com/#tencentmusic/page-eyes-agent&type=date&legend=top-left)
