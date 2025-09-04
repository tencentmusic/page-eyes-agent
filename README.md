## PageEyes Agent

![](https://img.shields.io/badge/build-passing-brightgreen)
![](https://img.shields.io/badge/python-12-blue?logo=python)

PageEyes Agent 是基于 [Pydantic AI](https://ai.pydantic.dev/#why-use-pydanticai) 框架开发的一个轻量级 UI Agent，
其中元素信息感知能力依靠 [OmniParserV2](https://huggingface.co/microsoft/OmniParser-v2.0) 模型，整个 Agent 的优势在于不依赖视觉语言大模型，
即使小参数的 LLM 也能胜任路径规划能力，同时支持多平台（Web、Android），目前主要包含以下功能：

1. 完全由自然语言指令驱动，无需编写脚本，既可实现自动化测试，UI巡检等任务
2. 跨平台、夸端支持，在 Python 环境中安装 page-eyes 库和配置 OmniParser 服务后即可开始 Web、Android 平台的自动化任务，未来还将继续支持iOS平台
3. 支持多种大模型接入，包括DeepSeek、OpenAI、千问等，默认使用 DeepSeek V3 模型，后续会支持更多大模型接入
4. 可通过自然语言进行断言，并生成详细的执行日志和报告，方便测试人员查看执行过程和结果

<img title="" src="https://cdn-y.tencentmusic.com/1e1e171e6dd06b6808489acd381db735.png" alt="" width="610" data-align="center">

***

## 安装

```shell
pip install page-eyes
```

## 使用示例

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

## 更新日志

- 2025-09-03
  1. 支持等待、停留等自然语言操作
  2. 支持传递 OmniParser Key 鉴权
  3. 断言支持判断页面/屏幕中是否存在某个关键字

- 2025-08-01
  
  1. 精简了系统提示词，每次调用使用更少的token
  2. 优化报告的记录和生成逻辑，解决步骤偶然错乱的问题
  3. 优化工具的参数，实现最小化参数，减少token
  4. 优化了等待逻辑，实现更精准的等待，不需要统一等待1s
  5. 截图、解析改成异步,并发不阻塞
  6. 优化浏览器配置，支持使用持久化缓存，二次启动页面速度更快

- 2025-07-28
  
  1. 增加滚动和滑动操作
  2. 支持H5 swiper 组件滑动

- 2025-06-25
  
  1. 优化 LLM Graph 控制
  2. 更新配置模式

- 2025-06-09
  
  1. 支持 Web Agent 模式
  2. 增加执行报告和过程实时渲染
  3. 重构同步方法为异步

- 2025-06-04
  
  1. 支持移动端 Agent 模式
  2. 增加`click` `input` `open_url` 工具
  3. 支持接入 OmniParser 进行元素解析