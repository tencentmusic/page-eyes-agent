# 快速上手


本指南将带你用 5 分钟时间，完成从安装到运行第一个 Web 自动化脚本的全过程。

我们的目标是编写一个脚本，自动打开浪潮音乐大赏官网，并导航到评委会页面。

---

### 第 1 步：环境准备

在开始之前，请确保你已经完成了以下两项基本安装。

> 如果需要更详细的环境要求（如移动端 ADB、报告存储 MinIO 等），请参考我们的 **[安装指南](../getting-started/installation.md)**。

1.  **安装 Page Eyes Agent**
    打开你的终端，运行以下命令：
    ```bash
    pip install page-eyes
    ```

2.  **安装浏览器驱动**
    PageEyes Agent 需要 Playwright 提供的浏览器驱动来执行任务。运行以下命令来自动安装：
    ```bash
    playwright install
    ```
    <small>（如果已安装，此命令会立刻提示并退出，不会重复下载）</small>


### 第 2 步：配置文件准备

在开始之前，请确保你已经部署好所需的大模型调用服务、OmniParser 服务以及（可选的）MinIO 存储服务。

项目通过根目录下的 `.env` 文件来加载这些服务的配置。请在项目根目录下创建一个名为 `.env` 的文件，并将以下内容作为模板填入：


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

---

### 第 3 步：编写你的第一个脚本

现在，环境和配置已经准备就绪。创建一个新的 Python 文件，例如 `my_first_test.py`，然后将下面的完整代码复制进去。

```python
import asyncio
from page_eyes.agent import WebAgent

async def main():
    # 初始化Web Agent
    # debug=True 设置浏览器以非无头模式运行
    ui_agent = await WebAgent.create(simulate_device='Intel MacBook Pro 13-inch', debug=True)

    # 给出清晰、分步骤的自然语言指令
    report = await ui_agent.run(
        ('1.打开 url "https://wma.wavecommittee.com/"\n'
         '2.点击"浪潮评委会成员"tab\n'
         '3.上滑页面，直到出现"查看浪潮评委会"\n'
         '4.点击"查看浪潮评委会"按钮\n'
         ))
    
    # 任务完成后，可以打印报告的摘要
    print("任务完成！报告摘要：", report.summary)


if __name__ == "__main__":
    asyncio.run(main())
```

---

### 第 4 步：运行脚本

回到终端，确保路径与你保存的 `my_first_test.py` 文件一致，然后运行它：

```bash
python my_first_test.py
```
---

### 第 5 步：观察结果

你应该能看到一个浏览器窗口自动弹出，并像一个真正的用户一样，按顺序执行了你给出的所有指令。当脚本在终端中打印出“任务完成！”时，你就成功地完成了第一次PagesEyes Agent驱动的UI自动化。
同时，本地已经生成了步骤报告

---

### 接下来做什么？

恭喜你！你已经掌握了 PageEyes Agent 的基本用法。

*   如果需要探索更复杂的场景，包括 **Android 端自动化**和查看详细的**交互视频与步骤报告**，请继续浏览我们的 **[实战案例](./examples.md)**。
*   如果需要深入理解 Agent 的工作原理，请阅读 **[核心概念](../guides/core-concepts.md)**。