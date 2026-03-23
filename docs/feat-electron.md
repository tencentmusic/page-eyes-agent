# feat: 支持桌面端 Electron 应用自动化

## 背景

Electron 应用的渲染层本质是 Chromium 网页，Playwright 原生支持通过 CDP（Chrome DevTools Protocol）接入已运行的 Electron 进程。因此工具层可完全复用现有 `WebAgentTool`，改动主要集中在设备连接层。

---

## TODO

### 1. 设备层 `device.py`

- [x] 新增 `ElectronDevice(Device[Browser, Page])` 数据类
- [x] 实现 `ElectronDevice.create(cdp_url)` 异步工厂方法
  - 通过 `playwright.chromium.connect_over_cdp(cdp_url)` 连接已运行的 Electron 进程
  - 取 `browser.contexts[0].pages[0]` 作为操作目标页
  - 从 `page.viewport_size` 读取并存储 `device_size`
- [x] `tear_down` 时不关闭 browser（Electron 进程由外部管理，不应随 agent 结束而退出）

```python
# 连接方式（对比 WebDevice）
# WebDevice:      playwright.chromium.launch_persistent_context(...)  ← 自己启动浏览器
# ElectronDevice: playwright.chromium.connect_over_cdp(cdp_url)       ← 接入已运行进程
```

---

### 2. 工具层 `tools/electron.py`

- [x] 新增 `ElectronAgentTool(WebAgentTool)`，直接继承，**无需覆盖任何方法**
- [x] 仅覆盖 `tear_down`：去掉 `context.close()` 和 `client.stop()`，避免关掉 Electron 进程

```
继承自 WebAgentTool 可直接使用的工具：
✅ get_screen_info   截图 + OmniParser 解析元素
✅ click             鼠标点击
✅ input             键盘输入
✅ swipe             鼠标滚轮 / 拖拽滑动
✅ open_url          page.goto()（应用内 webview 跳转）
✅ goback            page.go_back()
✅ wait              等待 / 轮询关键字
✅ assert_*          断言屏幕包含/不包含关键字
```

---

### 3. 导出 `tools/__init__.py`

- [x] 添加 `from .electron import ElectronAgentTool`
- [x] 在 `__all__` 中补充 `ElectronAgentTool`

---

### 4. Agent 层 `agent.py`

- [x] 新增 `ElectronAgent(UiAgent)` 类
- [x] 实现 `ElectronAgent.create(cdp_url, model, debug, tool_cls)` 异步工厂方法，参照 `WebAgent.create()` 结构

---

### 5. 测试 `tests/`

- [x] 在 `conftest.py` 新增 `electron_agent` fixture，参数为 `cdp_url`（默认 `http://localhost:9222`）
- [x] 新增 `tests/test_electron_agent.py`，编写基础冒烟用例

---

### 6. 被测 Electron 应用的启动方式

Electron 应用需在启动时携带 `--remote-debugging-port` 参数，agent 才能通过 CDP 接入：

```bash
# macOS 通用方式（推荐先尝试，大多数 Electron App 支持）
open -a "应用名称" --args --remote-debugging-port=9222

# 以 XMind 为例
open -a "XMind" --args --remote-debugging-port=9222

# 验证是否连接成功（浏览器访问，能看到页面列表即可）
http://localhost:9222/json
```

如果应用不支持 `--remote-debugging-port`，备选方案：
- **视觉方案**：桌面截图（`pyautogui` / `mss`）+ `pyautogui` 操控鼠标键盘，复用 OmniParser + LLM 决策链路，需新增 `DesktopDevice`
- **Accessibility API**：macOS 原生辅助功能 API（`atomacos`），读取控件树，无需 CDP

---

## 改动文件汇总

| 文件 | 改动类型 | 说明 |
|---|---|---|
| `src/page_eyes/device.py` | 新增 | `ElectronDevice` 类 |
| `src/page_eyes/tools/electron.py` | 新增 | `ElectronAgentTool` 类 |
| `src/page_eyes/tools/__init__.py` | 修改 | 导出 `ElectronAgentTool` |
| `src/page_eyes/agent.py` | 新增 | `ElectronAgent` 类 |
| `tests/conftest.py` | 修改 | 新增 `electron_agent` fixture |
| `tests/test_electron_agent.py` | 新增 | 冒烟测试用例 |
