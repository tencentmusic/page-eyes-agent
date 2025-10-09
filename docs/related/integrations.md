# 集成方案

本页面介绍如何将 PageEyes Agent 集成到你的项目中，以及与其他工具和系统的集成方案。

## 测试框架集成

### 1. Pytest 集成

将 PageEyes Agent 与 Pytest 集成，实现结构化的 UI 自动化测试。

**配置步骤：**

1. 安装必要的依赖：

```bash
pip install pytest pytest-asyncio page-eyes
```

2. 创建测试文件 `test_ui.py`：

```python
import pytest
import asyncio
from page_eyes.agent import WebAgent

@pytest.fixture(scope="module")
async def web_agent():
    agent = await WebAgent.create(simulate_device='Desktop Chrome', debug=True)
    yield agent
    

@pytest.mark.asyncio
async def test_login_flow(web_agent):
    await web_agent.run(
        ('1.打开 url "https://your-application-url.com"\n'
         '2.点击"登录"按钮\n'
         '3.在用户名输入框中输入"test@example.com"\n'
         '4.在密码输入框中输入"password123"\n'
         '5.点击"提交"按钮\n')
    )

@pytest.mark.asyncio
async def test_search_functionality(web_agent):
    await web_agent.run(
        ('1.打开 url "https://your-application-url.com"\n'
         '2.在搜索框中输入"测试产品"\n'
         '3.点击"搜索"按钮\n'
         '4.检查页面包含"搜索结果"文本\n')
    )

```

3. 运行测试：

```bash
pytest test_ui.py -v
```


## 自定义集成

### 1. 与现有测试框架的自定义集成

如果你有自己的测试框架，可以通过以下方式集成 PageEyes Agent：


### 2. 与自定义报告系统集成

如果你有自己的报告系统，可以通过以下方式集成 PageEyes Agent 的测试报告：


## 最佳实践

1. **环境变量管理**：使用环境变量或配置文件管理敏感信息，如 API 密钥和服务 URL。

2. **资源清理**：确保在测试完成后正确清理资源，避免内存泄漏和资源浪费。

3. **错误处理**：实现适当的错误处理机制，确保集成系统能够正确处理 PageEyes Agent 可能遇到的异常。

4. **弹性重试策略**：实现弹性重试机制，配置合理的重试阈值、间隔时间和最大尝试次数，以应对网络延迟、DOM 渲染异常和临时服务中断等瞬态故障。

5. **报告管理**：实现报告归档和过期清理策略，避免报告文件占用过多存储空间。

6. **监控和告警**：设置适当的监控和告警机制，及时发现和解决问题。


通过以上集成方案，可以将 PageEyes Agent 无缝集成到开发和测试流程中，实现自动化测试、UI 巡检和业务流程验证的自动化。