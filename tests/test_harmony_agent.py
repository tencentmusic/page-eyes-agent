#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Author : aidenmo
# @Email : aidenmo@tencent.com
# @Time : 2025/9/28 16:35
import pytest

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def test_mobile_01(harmony_agent):
    await harmony_agent.run(
        """
        - 打开 "微信" APP
        - 等待1s
        - 打开 "设置" APP
        - 等待1s
        - 打开 "浏览器" APP
        """
    )


async def test_mobile_02(harmony_agent):
    """测试多个交互"""
    await harmony_agent.run(
        """
        - 打开 url "https://yobang.tencentmusic.com/chart/uni-chart/rankList/"
        - 如果出现 "close" 按钮，则点击 "close" 按钮, 否则跳过
        - 点击"搜索"
        - 在搜索输入框中输入"任素汐"
        - 等待3秒，直到出现"在腾讯音乐由你榜内相关歌曲"
        - 向上滑动，直到出现"胡广生"
        """
    )


async def test_mobile_03(harmony_agent):
    """测试多个交互"""
    await harmony_agent.run(
        """
        - 打开 "QQ音乐" APP
        - 点击 "乐馆"
        - 点击 "歌手"
        - 上滑直到出现 "周深"
        - 点击 "周深"
        - 点击 "全部播放"
        """
    )
