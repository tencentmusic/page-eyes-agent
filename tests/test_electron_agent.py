#!/usr/bin/env python
# -*- coding: utf-8 -*-
import pytest

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def test_electron_01(electron_agent):
    """一键生成功能：点击按钮 → 弹窗输入 → 生成思维导图 → 验证中心节点"""
    result = await electron_agent.run("""
        - 点击左侧栏的"一键生成"按钮
        - 检查弹窗是否出现，弹窗中应包含输入框和"生成"按钮
        - 在一键生成面板中输入"AI agent 技术架构"
        - 点击"生成"按钮
        - 等待10秒，直到页面中出现新生成的思维导图
        - 检查屏幕中出现"AI agent 技术架构"（不要点击，只做断言验证）
        - 最后关闭新建思维导图的窗口
        """)
    assert result["is_success"], f"测试失败: {result['steps']}"
