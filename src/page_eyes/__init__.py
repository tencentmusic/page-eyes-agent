#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Author : aidenmo
# @Email : aidenmo@tencent.com
# @Time : 2025/5/23 15:09
from dotenv import load_dotenv

"""
优先级规则（从高到低）：
1. 代码中传入的参数（如 Settings(headless=False)）
2. 环境变量
3. .env 文件
4. 类属性默认值
"""
load_dotenv(override=True)
