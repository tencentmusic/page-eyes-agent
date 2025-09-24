## PageEyes Agent

![](https://img.shields.io/badge/build-passing-brightgreen)
![](https://img.shields.io/badge/python-12-blue?logo=python)

---

**中文文档**: [PageEyes Agent](https://tencentmusic.github.io/page-eyes-agent/)

---

PageEyes Agent 是基于 [Pydantic AI](https://ai.pydantic.dev/#why-use-pydanticai) 框架开发的一个轻量级 UI Agent，
其中元素信息感知能力依靠 [OmniParserV2](https://huggingface.co/microsoft/OmniParser-v2.0) 模型，整个 Agent 的优势在于不依赖视觉语言大模型，
即使小参数的 LLM 也能胜任路径规划能力，同时支持多平台（Web、Android），目前主要包含以下功能：

1. 完全由自然语言指令驱动，无需编写脚本，既可实现自动化测试，UI巡检等任务
2. 跨平台、跨端支持，在 Python 环境中安装 page-eyes 库和配置 OmniParser 服务后即可开始 Web、Android 平台的自动化任务，未来还将继续支持iOS平台
3. 支持多种大模型接入，包括DeepSeek、OpenAI、千问等，默认使用 DeepSeek V3 模型，后续会支持更多大模型接入
4. 可通过自然语言进行断言，并生成详细的执行日志和报告，方便测试人员查看执行过程和结果

<img title="" src="https://cdn-y.tencentmusic.com/1e1e171e6dd06b6808489acd381db735.png" alt="" width="610" data-align="center">

***

## 安装

```shell
pip install page-eyes
```
## 快速开始
配置环境变量

| 环境变量          | 默认值       | 说明                                                                 |
|:------------------|-----------|----------------------------------------------------------------------|
| AGENT_MODEL       | openai:deepseek-v3 | 使用的AI模型，当前设置为deepseek-v3                                  |
| AGENT_DEBUG       | False     | 是否启用调试模式                                                     |
| AGENT_HEADLESS    | False     | 是否使用无头模式                                                     |
| AGENT_LOG_GRAPH_NODE | False     | 是否记录图节点日志                                                   |
| AGENT_OMNI_KEY    | test-UfcWMpXW | Omni服务的认证密钥                                                   |
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

    report = await ui_agent.run(
        ('1.打开 url "https://yobang.tencentmusic.com/chart/uni-chart/rankList/"\n'
         '2.点击"查找icon"\n'
         '3.在搜索输入框中输入"小美满"\n'
         '4.点击"小美满> "\n'
         '5.点击"日榜"'
         ))


if __name__ == "__main__":
    asyncio.run(main())
```

## 如有需要，加入我们的交流群
![](./docs/about/contact_qr.png)