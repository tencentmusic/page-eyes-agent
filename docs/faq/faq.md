# 常见问题

## 元素识别和操作类

### 页面加载和元素解析不稳定，指令执行的成功率低怎么办？

当前PageEyes Agent使用的元素解析来源分为3类，分别是`box_ocr_content_ocr`、`box_yolo_content_ocr`、`box_yolo_content_yolo`。

本质是来自OCR的text和来自florence2-base-ft模型的icon，在解析不稳定时text和icon可能变动。因此，我们建议：

1. **使用稳定的文本和按钮标识**：
   ```
   并行使用元素的 text 和 icon 信息，比如：`点击"推荐"按钮或"点赞"按钮`
   避免使用动态元素
   ```
2. **借助元素相对位置信息**：
   ```
   点击"菜单"按钮右边的图标
   点击表格第一行的"编辑"链接
   ```

3. **使用具体的元素描述**：
   ```
   ✅ 好：`点击弹窗内的"确认"按钮`
   ❌ 差：`点击弹窗内的按钮`
   ```
更多示范请参考文档 [最佳实践](/guides/best-practice.md)


### 复杂页面操作失败怎么办？
1. **分解复杂操作**：
   ```
   1. 点击"最新"tab
   2. 等待直到页面内出现"配置"按钮
   3. 滚动到页面底部
   4. 点击"提交"按钮
   ```

2. **添加等待时间**：
   ```
   1. 点击"提交"按钮
   2. 等待页面加载完成
   3. 检查页面出现"提交成功"文本
   ```

### 页面不稳定，加载超时怎么办？
- 考虑使用 `等待 3 秒`、 `等待直到页面内出现"xxx"元素`等自然语言指令


## 断言和验证类

### 支持断言吗？
- 支持。断言方式是通过在指令内添加断言页面内存在或者不存在指定的元素

#### 常用断言示例
```
# 存在性断言
检查页面包含"投票成功"文本
检查页面存在"QQ音乐"图标

# 不存在性断言
检查页面不包含"错误"、"异常"文本
检查页面不存在"加载中"图标
```

### 断言是如何实现的？
- 断言通过模型调用断言工具来实现，内嵌在PageEyes Agent项目中。此外提供了统一工具接口，如果需要其他的断言只要实现相应的工具既可


## 日志和报告类

### 执行时生成的日志可视化是如何实现的？
日志由Loguru打印，步骤节点信息由 Agent Graph 节点提供

### 如何开启详细日志？
```bash
# 开启调试模式
export AGENT_DEBUG=True

# 开启图节点日志
export AGENT_LOG_GRAPH_NODE=True
```

### 测试报告存储在哪里？
PageEyes Agent 支持两种存储方式：
1. **腾讯云 COS**（推荐）
2. **MinIO**（开源替代方案）

配置存储服务后，测试报告和截图会自动上传到指定的存储桶中。


##  移动端（Android）类

### Android 设备adb连接不上怎么解决？
- 确保设备已开启"USB 调试"
- 开启"允许通过 USB 安装应用"
- 部分设备需要开启"USB 调试（安全设置）"
- 首次连接时需要在设备上确认授权
可参考[adb 连接设备](https://developer.android.com/studio/command-line/adb#connect-to-a-device-over-usb)


## 模型和 API 类

### 支持哪些大模型？
PageEyes Agent 支持多种大模型：
- **DeepSeek V3**（默认推荐）
- **OpenAI GPT-4o**
- **千问系列模型**
- 其他兼容 OpenAI API 格式的模型

### 如何切换模型？
```bash
# 使用 DeepSeek
export AGENT_MODEL="openai:deepseek-v3"
export OPENAI_BASE_URL="https://api.deepseek.com/v1"
export OPENAI_API_KEY="your_deepseek_api_key"

# 使用 OpenAI
export AGENT_MODEL="openai:gpt-4o"
export OPENAI_BASE_URL="https://api.openai.com/v1"
export OPENAI_API_KEY="your_openai_api_key"
```

### API 调用失败怎么办？
1. **检查 API Key**：确保 API Key 有效且有足够余额
2. **检查网络连接**：确保能访问模型服务端点
3. **检查配置**：验证 `OPENAI_BASE_URL` 和 `AGENT_MODEL` 配置正确
4. **查看错误日志**：开启 `AGENT_DEBUG=True` 查看详细错误信息


## 性能优化类

### 如何提高执行速度？
1. **使用无头模式**：
   ```bash
   export AGENT_HEADLESS=True
   ```

2. **优化指令**：
   - 减少不必要的等待时间
   - 合并相似操作
   - 使用精确的元素描述


## 集成和部署类

### 如何与 CI/CD 集成？
PageEyes Agent 可以集成到 CI/CD 流水线中：

```yaml
- name: Run UI Tests
  run: |
    export AGENT_HEADLESS=True
    python test_ui.py
```

## 获取帮助

### 遇到问题如何获取帮助？
1. **查阅文档**：[PageEyes Agent 官方文档](https://tencentmusic.github.io/page-eyes-agent/)
2. **GitHub Issues**：[提交问题](https://github.com/tencentmusic/page-eyes-agent/issues)
3. **开发者社区**：加入PageEyes Agent用户交流群


