#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Author : aidenmo
# @Email : aidenmo@tencent.com
# @Time : 2025/9/28 16:35
import pytest

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def test_mobile_01(android_agent):
    await android_agent.run(
        """
        - 打开 "微信" APP
        - 等待1s
        - 打开 "设置" APP
        - 等待1s
        - 打开 "浏览器" APP
        """
    )


async def test_mobile_02(android_agent):
    """测试多个交互"""
    await android_agent.run(
        """
        - 打开 url "https://yobang.tencentmusic.com/chart/uni-chart/rankList/"
        - 检查页面是否有 "close" 按钮，如果有则点击 "close" 按钮
        - 点击"Q"
        - 在搜索输入框中输入"任素汐"
        - 等待3秒，直到出现"在腾讯音乐由你榜内相关歌曲"
        - 向上滑动，直到出现"胡广生"
        """
    )


async def test_mobile_03(android_agent):
    """测试多个交互"""
    await android_agent.run(
        """
        - 打开 url "https://i2.y.qq.com/n3/coin_center/pages/client_v1/index.html"
        - 如果出现“立即签到”则点击“立即签到”，否则跳过
        - 如果出现"close"元素，则点击"close"元素，否则跳过
        - 从 (350, 500) 滑动到 (350, 100)
        - 点击“看视频”按钮
        - 如果出现出现“点击浏览15秒”则点击“点击浏览15秒”，否则跳过
        - 等待15秒。
        - 则点击媒体元素右侧的"close"元素
        - 如果出现2个"close"元素，则点击第2个"close"元素，否则点击第1个"close"元素
        - 上滑屏幕，直到页面中出现 "金币抽奖" 元素
        """
    )


async def test_mobile_04(android_agent):
    """测试多个交互"""
    await android_agent.run(
        """
        - 打开 url https://yobang.tencentmusic.com/chart/live-chart/rankList/
        - 点击"全部播放"左侧的播放按钮
        """
    )
