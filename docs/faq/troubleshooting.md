# 故障排查

---
## 环境配置问题

### 问题：环境变量配置不生效

**解决方案：**

1. **检查 .env 文件（参考项目根目录下的.env.example文件）**
   ```bash
   # 在项目根目录创建 .env 文件
   AGENT_HEADLESS=True
   AGENT_MODEL=openai:deepseek-v3
   AGENT_OMNI_BASE_URL=https://your-omni-service.com
   AGENT_OMNI_KEY=your_omni_key
   ```
2. **检查环境变量格式是否正确，注意 AGENT_前缀、OPENAI_前缀、COS_前缀、MINIO_前缀**

3. **验证配置加载**
   ```python
   from page_eyes.config import default_settings
   print(default_settings.model_dump())
   ```
  
### 问题：依赖包安装失败或者冲突
**解决方案：**

1. **使用 uv 管理虚拟环境**
   ```bash
   # 创建虚拟环境
   uv venv
   
   # 激活虚拟环境
   source .venv/bin/activate  # Linux/Mac
   # 或
   .venv\Scripts\activate     # Windows
   
   # 或者使用 uv 直接运行（推荐）
   uv run python your_script.py
   ```

2. **检查 Python 版本**
   ```bash
   # 检查当前 Python 版本
   uv python list
   python --version  # 需要 Python 3.12+
   
   # 如需指定 Python 版本
   uv venv --python 3.12
   ```

3. **使用 uv 安装依赖**
   ```bash
   # 升级 uv 到最新版本
   uv self update
   
   # 安装项目依赖
   uv sync
   
   # 或从 requirements.txt 安装
   uv pip install -r requirements.txt
   
   # 安装单个包
   uv add package_name
   ```

4. **清理和重建环境**
   ```bash
   # 删除现有虚拟环境
   rm -rf .venv
   
   # 重新创建虚拟环境
   uv venv
   
   # 重新安装依赖
   uv sync
   ```

5. **解决版本冲突**
   ```bash
   # 查看依赖树
   uv tree
   
   # 更新所有依赖到兼容版本
   uv lock --upgrade
   
   # 强制重新解析依赖
   uv lock --refresh
   ```

---

## 设备连接问题

### 问题：Playwright浏览器启动失败
**解决方案：**

1. **安装Playwright浏览器**
   ```bash
   playwright install chromium
   # 或安装所有浏览器
   playwright install
   ```

2. **检查系统依赖**
   ```bash
   # Ubuntu/Debian
   playwright install-deps
   
   # 或手动安装依赖
   sudo apt-get install libnss3 libatk-bridge2.0-0 libdrm2 libxkbcommon0 libxcomposite1 libxdamage1 libxrandr2 libgbm1 libxss1 libasound2
   ```

3. **权限问题**
   ```bash
   # 确保有执行权限
   chmod +x ~/.cache/ms-playwright/chromium-*/chrome-linux/chrome
   ```
---

## 元素识别问题

### 问题：元素解析服务连接失败

**解决方案：**

1. **检查OMNI服务配置**
```bash
   # 验证服务地址
   export AGENT_OMNI_BASE_URL="https://your-omni-service.com"
```

2. **测试网络连通性**
```bash
curl -X POST "${AGENT_OMNI_BASE_URL}/omni/parse/" \
        -H "Content-Type: multipart/form-data" \
        -F "file=@test_image.png"
```

---

## 存储服务问题

### 问题：COS/MinIO上传文件失败

**解决方案：**

1. **检查存储配置（可参考项目根目录下的.env.example文件）**
```bash
# 使用 MinIO
MINIO_ACCESS_KEY=xxx
MINIO_SECRET_KEY=xxx
MINIO_ENDPOINT=host:port
MINIO_BUCKET=bucket-name

#使用腾讯云COS
COS_SECRET_ID=xxx
COS_SECRET_KEY=xxx
COS_ENDPOINT=xxx
COS_BUCKET=xxx
```

2. **测试连接**
   ```python
   from page_eyes.util.storage import storage_client
   
   # 测试上传
   with open('test.png', 'rb') as f:
       url = await storage_client.async_upload_file(f)
       print(f"Upload success: {url}")
   ```

3. **切换存储方式**
   ```python
   # 临时使用本地存储
   import tempfile
   temp_dir = tempfile.mkdtemp()
   # 保存文件到本地目录
   ```


---

## 日志分析

### 启用详细日志

```bash
# 启用所有调试信息
export AGENT_DEBUG=True
export AGENT_LOG_GRAPH_NODE=True

# 设置日志级别
export LOGURU_LEVEL=DEBUG
```

---

## 获取帮助

如果文档及以上解决方案都无法解决问题，请：


1. **提交Issue**：
   访问[GitHub Issues](https://github.com/tencentmusic/page-eyes-agent/issues)，包含完整的错误日志和环境信息，提供复现步骤

2. **社区支持**：
   查阅[官方文档](https://tencentmusic.github.io/page-eyes-agent/)，加入"PageEyes Agent 用户交流群"

---