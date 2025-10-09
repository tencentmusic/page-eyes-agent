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
    await web_agent_pc.run(
        """
        1. 打开 url "https://wma.wavecommittee.com/"
        2. 等待2秒
        2. 点击"浪潮评委会成员"
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


async def test_web_mobile_01(web_agent_mobile):
    """TODO 验证步骤"""
    await web_agent_mobile.run(
        """
        1. 打开 url "https://yobang.tencentmusic.com/chart/uni-chart/rankList/"
        2. 点击 "查找" 按钮
        3. 等待1s
        4. 在搜索输入框中输入"小美满"
        """
    )
