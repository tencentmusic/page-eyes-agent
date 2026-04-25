#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Author : aidenmo
# @Email : aidenmo@tencent.com
# @Time : 2025/9/28 16:35
import pytest

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def test_mobile_01(mobile_agent):
    await mobile_agent.run(
        """
        - 打开 "微信" APP
        - 等待1s
        - 打开 "设置" APP
        - 等待1s
        - 打开 "浏览器" APP
        """
    )

