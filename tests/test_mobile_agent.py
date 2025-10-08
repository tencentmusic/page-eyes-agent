#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Author : aidenmo
# @Email : aidenmo@tencent.com
# @Time : 2025/9/28 16:35
import pytest
pytestmark = pytest.mark.asyncio(loop_scope="session")


async def test_web_pc_01(mobile_agent):
    await mobile_agent.run(
        """
        1. 打开 "微信" APP
        2. 等待1s
        3. 打开 "设置" APP
        4. 等待1s
        5. 打开 "浏览器" APP
        """
    )
