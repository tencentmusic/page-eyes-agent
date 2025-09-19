# 贡献指南

欢迎来到 PageEyes Agent 项目的贡献指南！我们非常感谢您对项目的兴趣，并期待您的贡献。本文档将帮助您了解如何参与到 PageEyes Agent 的开发中来。

## 项目概述

PageEyes Agent 是一个轻量级 UI Agent，通过自然语言指令驱动，无需编写脚本即可实现 Web、Android 平台的 UI 自动化任务。项目基于 [Pydantic AI](https://ai.pydantic.dev/) 框架开发，使用 [OmniParserV2](https://huggingface.co/microsoft/OmniParser-v2.0) 模型进行元素信息感知。

## 贡献流程

### 1. 准备工作

1. **Fork 仓库**：访问 [PageEyes Agent 仓库](https://github.com/tencentmusic/page-eyes-agent)，点击右上角的 "Fork" 按钮创建自己的副本。
2. **克隆仓库**：将您的 Fork 克隆到本地环境。
   ```bash
   git clone https://github.com/YOUR_USERNAME/page-eyes-agent.git
   cd page-eyes-agent
   ```
3. **设置开发环境**：按照 [开发环境设置指南](dev-env.md) 配置您的开发环境。

### 2. 创建分支

为您的贡献创建一个新的分支：

```bash
git checkout -b feature/your-feature-name
```

分支命名建议：
- `feature/xxx`：新功能开发
- `bugfix/xxx`：Bug 修复
- `docs/xxx`：文档更新
- `refactor/xxx`：代码重构

### 3. 开发与测试

1. 进行您的更改，遵循 [代码规范](code-style.md)。
2. 添加或更新测试以覆盖您的更改。
3. 确保所有测试通过：
   ```bash
   pytest
   ```

### 4. 提交更改

1. 提交您的更改：
   ```bash
   git add .
   git commit -m "feat: 添加新功能 xxx"
   ```
   请遵循 [约定式提交](https://www.conventionalcommits.org/zh-hans/v1.0.0/) 规范。

2. 将您的分支推送到 GitHub：
   ```bash
   git push origin feature/your-feature-name
   ```

### 5. 创建 Pull Request

1. 访问您的 Fork 仓库页面，点击 "Compare & pull request"。
2. 填写 PR 标题和描述，详细说明您的更改。
3. 提交 PR 后，项目维护者将会审查您的代码。
4. 根据反馈进行必要的修改。

## 贡献类型

我们欢迎各种形式的贡献，包括但不限于：

### 代码贡献

- **功能开发**：实现路线图中的新功能或您认为有价值的功能
- **Bug 修复**：修复已知问题或您发现的新问题
- **性能优化**：提高代码效率、减少资源消耗
- **代码重构**：改进代码结构，提高可维护性

### 文档贡献

- **文档改进**：修复错误、添加示例、完善解释
- **教程编写**：创建新的教程或指南
- **API 文档**：完善 API 文档

### 测试贡献

- **单元测试**：增加测试覆盖率
- **集成测试**：添加端到端测试
- **测试用例**：提供更多测试场景

### 其他贡献

- **问题报告**：提交详细的 Bug 报告
- **功能建议**：提出新功能或改进建议
- **用户体验反馈**：分享您使用 PageEyes Agent 的经验

## 行为准则

我们期望所有参与者遵循以下行为准则：

1. **尊重他人**：尊重不同观点和经验，友好对待每一位贡献者。
2. **专业沟通**：接受建设性批评，专注于项目的最佳利益。
3. **包容多样性**：欢迎来自不同背景和经验水平的贡献者。
4. **负责任**：对自己的言行负责，承诺高质量的贡献。

## 获取帮助

如果您在贡献过程中遇到任何问题，可以通过以下方式获取帮助：

- 在 GitHub Issues 中提问
- 联系项目维护者：aidenmo@tencent.com

感谢您对 PageEyes Agent 项目的贡献！