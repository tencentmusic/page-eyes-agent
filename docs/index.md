---
title: PageEyes Agent
hide:
#  - navigation
---

<div align="center" markdown>

# **PageEyes Agent**

### 轻量级 UI 自动化 Agent  
*基于自然语言指令驱动的跨平台 UI 自动化解决方案*

![](https://img.shields.io/badge/build-passing-brightgreen)
![](https://img.shields.io/badge/python-12-blue?logo=python)
<a href="https://github.com/tencentmusic/page-eyes-agent/blob/master/LICENSE">
    <img src="https://img.shields.io/badge/License-MIT-blue?labelColor=d4eaf7" alt="License">
</a>
<a href="https://pypi.org/project/page-eyes/">
    <img alt="Version" src="https://img.shields.io/pypi/v/page-eyes.svg?labelColor=d4eaf7&label=version&color=blue">
</a>

</div>

---
## 简介

PageEyes Agent 是一个 **Python UI 自动化 Agent 框架**，帮助你用自然语言快速、稳定地完成跨平台 UI 自动化测试、巡检和业务验证。

PageEyes Agent 以 *自然语言指令* 颠覆传统 UI 自动化：无需编写脚本，也能实现复杂的跨平台测试与巡检。基于 [Pydantic AI](https://ai.pydantic.dev/#why-use-pydanticai) 框架开发，
其中元素信息感知能力依靠 [OmniParserV2](https://huggingface.co/microsoft/OmniParser-v2.0) 模型，不依赖视觉语言大模型，
即使小参数的 LLM 也能胜任路径规划能力，同时支持多平台（Web、Android）

---

## 功能特性

<div class="grid cards" markdown>

- :material-message-processing:{ .lg .icon-color } **[自然语言驱动](guides/core-concepts.md)**  
  完全由自然语言指令驱动，无需编写脚本，即可实现自动化测试、UI 巡检等任务。  
  { .card .shadow .primary }

- :material-devices:{ .lg .icon-color } **[跨平台支持](getting-started/installation.md)**  
  支持 Web、Android 平台，未来将支持 iOS 平台。  
  { .card .shadow .indigo }

- :material-brain:{ .lg .icon-color } **[多模型接入](guides/core-concepts.md)**  
  支持 DeepSeek、OpenAI、千问等多种大模型接入，默认使用 DeepSeek V3 模型。  
  { .card .shadow .purple }

- :material-file-document:{ .lg .icon-color } **[详细报告](guides/core-concepts.md)**  
  可通过自然语言进行断言，并生成详细的执行日志和报告。  
  { .card .shadow .blue }

</div>

---

## 为什么选择 PageEyes Agent？

借助 Page Eyes Agent，你可以用自然语言快速构建、执行和维护跨平台 UI 自动化测试。  
与传统 UI 自动化方案相比，它具备以下优势：

<div class="grid cards" markdown>

- :material-speedometer:{ .lg } **更高的开发效率**  
  使用自然语言指令即可完成测试用例，无需编写和维护脚本  
  { .card .shadow }

- :material-autorenew:{ .lg } **更低的维护成本**  
  UI 变动时仅需调整指令，减少定位器和测试逻辑的重复修改  
  { .card .shadow }

- :material-school:{ .lg } **平缓的学习曲线**  
  无需自动化框架或编程知识，业务人员也可直接使用  
  { .card .shadow }

- :material-devices:{ .lg } **强大的跨平台能力**  
  同一套指令适用于 Web、Android，未来支持 iOS  
  { .card .shadow }

- :material-shield-check:{ .lg } **智能的故障恢复**  
  自动尝试替代路径和恢复策略，避免小变动导致脚本失败  
  { .card .shadow }

</div>


---

## 应用场景
<div class="grid cards" markdown>

- :material-rocket-launch:{ .lg .icon-color } **UI 自动化测试**  
  快速构建和执行测试用例  
  { .card .shadow .primary }

- :material-eye:{ .lg .icon-color } **页面巡检**  
  定期检查页面功能和性能  
  { .card .shadow .indigo }

- :material-check-decagram:{ .lg .icon-color } **业务流程验证**  
  验证关键业务流程的正确性  
  { .card .shadow .purple }

- :material-cellphone-link:{ .lg .icon-color } **兼容性测试**  
  在不同平台和设备上验证应用行为  
  { .card .shadow .blue }

</div>
---
