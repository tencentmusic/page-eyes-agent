# 代码风格指南

本文档定义了 PageEyes Agent 项目的代码风格规范，旨在保持代码库的一致性和可维护性。所有贡献者在提交代码前，请确保遵循以下规范。

## Python 代码风格

PageEyes Agent 项目采用 [PEP 8](https://peps.python.org/pep-0008/) 作为基础的 Python 代码风格指南，并有以下特定规范：

### 格式化

- 使用 **Black** 作为代码格式化工具，配置为 88 字符行长度
- 使用 **isort** 对导入语句进行排序，配置为与 Black 兼容的模式
- 缩进使用 4 个空格，不使用制表符
- 文件末尾保留一个空行

### 命名约定

- **类名**：使用 `PascalCase`（如 `WebAgent`、`MinioConfig`）
- **函数和方法名**：使用 `snake_case`（如 `create_from_config`、`execute_test`）
- **变量名**：使用 `snake_case`（如 `user_data_dir`、`context_params`）
- **常量**：使用全大写 `SNAKE_CASE`（如 `AGENT_DEBUG`、`OPENAI_API_KEY`）
- **私有属性和方法**：使用前导下划线（如 `_client`、`_setup_environment`）

### 导入规范

导入语句按以下顺序排列：
1. 标准库导入
2. 相关第三方导入
3. 本地应用/库特定导入

示例：
```python
import asyncio
import os
import tempfile
from pathlib import Path

import adbutils
from loguru import logger
from minio import Minio
from playwright.async_api import async_playwright

from page_eyes.config import Config
from page_eyes.util.storage import Storage
```

### 文档字符串

- 使用 [Google 风格的文档字符串](https://google.github.io/styleguide/pyguide.html#38-comments-and-docstrings)
- 为所有公共模块、函数、类和方法编写文档字符串
- 包含参数类型、返回类型和可能的异常

示例：
```python
def create_from_config(config: Config) -> Storage:
    """从配置创建存储客户端。

    Args:
        config: 配置对象，包含连接参数

    Returns:
        配置好的存储客户端实例

    Raises:
        ConnectionError: 无法连接到存储服务时
    """
```

### 类型注解

- 使用 Python 类型注解增强代码可读性和工具支持
- 复杂类型使用 `typing` 模块（如 `List[str]`、`Dict[str, Any]`、`Optional[int]`）
- 使用 Pydantic 模型进行数据验证和序列化

## 代码质量工具

项目使用以下工具确保代码质量：

- **Flake8**：代码风格检查
- **Mypy**：静态类型检查
- **Pytest**：单元测试和集成测试
- **Coverage**：测试覆盖率报告

## 提交前检查

在提交代码前，请运行以下命令确保代码符合规范：

```bash
# 格式化代码
black .
isort .

# 代码风格检查
flake8

# 类型检查
mypy .

# 运行测试
pytest
```

## 最佳实践

### 异步编程

- 使用 `async`/`await` 语法进行异步编程
- 避免在异步函数中使用阻塞操作
- 使用 `asyncio.gather` 进行并行异步操作

### 错误处理

- 使用具体的异常类型而非通用 `Exception`
- 提供有意义的错误消息
- 在适当的抽象级别处理异常

### 日志记录

- 使用 Loguru 进行日志记录
- 为不同级别的日志提供适当的上下文信息
- 避免在正常操作流程中记录过多的调试信息

### 资源管理

- 使用上下文管理器（`with` 语句）管理资源
- 确保在异步代码中正确清理资源
- 避免资源泄漏，特别是在处理浏览器和移动设备会话时

## 代码审查标准

代码审查将关注以下方面：

1. **功能性**：代码是否实现了预期功能
2. **可读性**：代码是否易于理解
3. **可维护性**：代码结构是否合理，是否易于修改
4. **性能**：代码是否高效
5. **测试覆盖**：是否有足够的测试
6. **文档**：是否有适当的文档

遵循这些规范将有助于保持 PageEyes Agent 代码库的质量和一致性，感谢配合！