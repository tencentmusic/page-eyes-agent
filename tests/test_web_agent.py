#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Author : aidenmo
# @Email : aidenmo@tencent.com
# @Time : 2025/9/28 16:35
import pytest

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def test_web_pc_01(web_agent_pc):
    await web_agent_pc.run(
        """
        1. 打开 url "https://wma.wavecommittee.com/"
        2. 点击"浪潮评委会成员"
        """
    )


async def test_web_pc_02(web_agent_pc):
    """测试等待"""
    await web_agent_pc.run(
        """
        1. 打开 url "https://wma.wavecommittee.com/"
        2. 等待2秒
        3. 点击"浪潮评委会成员"
        """
    )


async def test_web_pc_03(web_agent_pc):
    """批量断言"""
    await web_agent_pc.run(
        """
        1. 打开 url "https://wma.wavecommittee.com/"
        2. 点击"浪潮评委会成员"
        3. 检查屏幕中出现"编曲"、"作词"、"制作"
        """
    )


async def test_web_pc_04(web_agent_pc):
    """批量断言，包含失败断言"""
    await web_agent_pc.run(
        """
        1. 打开 url "https://wma.wavecommittee.com/"
        2. 点击"浪潮评委会成员"
        3. 检查屏幕中出现"编曲"、"作词"、"制作中"
        """
    )


async def test_web_pc_05(web_agent_pc):
    """测试禁止工具并发执行"""
    await web_agent_pc.run(
        """
        1. 打开 url "https://wma.wavecommittee.com/"
        2. 连续点击"浪潮评委会成员"2次
        """
    )


async def test_web_pc_06(web_agent_pc):
    """测试操作不存在的元素"""
    await web_agent_pc.run(
        """
        1. 打开 url "https://wma.wavecommittee.com/"
        2. 点击"确定"按钮
        """
    )


async def test_web_pc_07(web_agent_pc):
    """测试滑动操作"""
    await web_agent_pc.run(
        """
        1. 打开 url "https://wma.wavecommittee.com/reward-2025/committee/"
        2. 上滑2次
        3. 点击"查看浪潮评委会"
        """
    )


async def test_web_pc_08(web_agent_pc):
    """测试滑动直到出现指定元素"""
    await web_agent_pc.run(
        """
        1. 打开 url "https://wma.wavecommittee.com/reward-2025/committee/"
        2. 上滑，直到出现"查看浪潮评委会"
        3. 点击"查看浪潮评委会"
        """
    )


async def test_web_pc_09(web_agent_pc):
    """测试点击元素相对位置"""
    await web_agent_pc.run(
        """
        1. 打开 url "https://chart.tencentmusic.com/uni-chart"
        2. 点击"推荐"按钮
        3. 点击"推荐"按钮左侧
        4. 点击"推荐"按钮右侧
        5. 点击"推荐"按钮左侧1/3处
        5. 点击"推荐"按钮底部
        """
    )


async def test_web_mobile_01(web_agent_mobile):
    await web_agent_mobile.run(
        """
        1. 打开 url "https://yobang.tencentmusic.com/chart/uni-chart/rankList/"
        2. 点击 "查找" 按钮
        3. 等待1s
        4. 在搜索输入框中输入"小美满"
        """
    )


async def test_web_mobile_02(web_agent_mobile):
    await web_agent_mobile.run(
        """
        1. 打开 url "https://yobang.tencentmusic.com/chart/uni-chart/search/"
        2. 在搜索输入框中输入"小美满"
        """
    )


async def test_web_mobile_03(web_agent_mobile):
    await web_agent_mobile.run(
        """
        1. 打开 url "https://yobang.tencentmusic.com/chart/uni-chart/rankList/"
        2. 点击"日榜"
        3. 点击"搜索"按钮
        4. 在搜索输入框中输入"任素汐"
        5. 检查页面出现"亲爱的你啊"
        """
    )
