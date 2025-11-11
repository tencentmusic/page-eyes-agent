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
        1. 打开 "微信" APP
        2. 等待1s
        3. 打开 "设置" APP
        4. 等待1s
        5. 打开 "浏览器" APP
        """
    )


async def test_mobile_02(mobile_agent):
    """测试多个交互"""
    await mobile_agent.run(
        """
        1. 打开 url "https://yobang.tencentmusic.com/chart/uni-chart/rankList/"
        2. 检查页面是否有 "close" 按钮，如果有则点击 "close" 按钮
        3. 点击"Q"
        4. 在搜索输入框中输入"任素汐"
        5. 等待3秒，直到出现"在腾讯音乐由你榜内相关歌曲"
        6. 向上滑动，直到出现"胡广生"
        """
    )
