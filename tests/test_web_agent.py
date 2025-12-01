#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Author : aidenmo
# @Email : aidenmo@tencent.com
# @Time : 2025/9/28 16:35
import pytest

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def test_web_pc_01(web_agent_pc):
    """综合交互测试"""
    await web_agent_pc.run(
        """
        - 打开 url "https://wma.wavecommittee.com/"
        - 向上滑动，直到出现"立即注册"按钮
        - 点击"立即注册"
        - 在手机号输入框中输入"13800138000"
        - 返回上一个页面
        - 等待1秒
        """
    )


async def test_web_pc_02(web_agent_pc):
    """测试等待"""
    await web_agent_pc.run(
        """
        - 打开 url "https://wma.wavecommittee.com/"
        - 等待2秒
        - 点击"浪潮评委会成员"
        - 等待3秒，直到出现"查看浪潮评委会"
        """
    )


async def test_web_pc_03(web_agent_pc):
    """测试批量断言"""
    await web_agent_pc.run(
        """
        - 打开 url "https://wma.wavecommittee.com/"
        - 点击"浪潮评委会成员"
        - 检查屏幕中出现"编曲"、"作词"、"制作"
        """
    )


async def test_web_pc_04(web_agent_pc):
    """批量断言，包含失败断言"""
    await web_agent_pc.run(
        """
        - 打开 url "https://wma.wavecommittee.com/"
        - 点击"浪潮评委会成员"
        - 检查屏幕中出现"编曲"、"作词"、"制作中"
        """
    )


async def test_web_pc_05(web_agent_pc):
    """测试禁止工具并发执行"""
    await web_agent_pc.run(
        """
        - 打开 url "https://wma.wavecommittee.com/"
        - 连续点击"浪潮评委会成员"2次
        """
    )


async def test_web_pc_06(web_agent_pc):
    """测试操作不存在的元素"""
    await web_agent_pc.run(
        """
        - 打开 url "https://wma.wavecommittee.com/"
        - 点击"确定"按钮
        """
    )


async def test_web_pc_07(web_agent_pc):
    """测试滑动操作"""
    await web_agent_pc.run(
        """
        - 打开 url "https://wma.wavecommittee.com/reward-2025/committee/"
        - 上滑2次
        - 点击"查看浪潮评委会"
        """
    )


async def test_web_pc_08(web_agent_pc):
    """测试滑动直到出现指定元素"""
    await web_agent_pc.run(
        """
        - 打开 url "https://wma.wavecommittee.com/reward-2025/committee/"
        - 上滑，直到出现"查看浪潮评委会"
        - 点击"查看浪潮评委会"
        """
    )


async def test_web_pc_09(web_agent_pc):
    """测试点击元素相对位置"""
    await web_agent_pc.run(
        """
        - 打开 url "https://chart.tencentmusic.com/uni-chart"
        - 点击"推荐"按钮
        - 点击"推荐"按钮左侧
        - 点击"推荐"按钮右侧
        - 点击"推荐"按钮左侧1/3处
        - 点击"推荐"按钮底部
        """
    )


async def test_web_pc_10(web_agent_pc):
    """测试点击上传文件"""
    await web_agent_pc.run(
        """
        - 打开 url "https://www.google.com/"
        - 点击"相机"按钮
        - 点击"将图片放到此处或上传文件"右侧1/4处，上传文件："./pic.png"
        """
    )


async def test_web_mobile_03(web_agent_mobile):
    """测试web H5 交互"""
    await web_agent_mobile.run(
        """
        - 打开 url "https://yobang.tencentmusic.com/chart/uni-chart/rankList/"
        - 检查页面是否有 "close" 按钮，如果有则点击 "close" 按钮，否则跳过
        - 点击"搜索"按钮
        - 在搜索输入框中输入"任素汐"
        - 等待3秒，直到出现"在腾讯音乐由你榜内相关歌曲"
        - 向上滑动，直到出现"胡广生"
        """
    )


async def test_web_mobile_04(web_agent_mobile):
    """测试web H5 输入交互， 输入后默认会自动回车，如果不需要回车可以要求不要发送回车/Enter"""
    await web_agent_mobile.run(
        """
        - 打开 url "https://yobang.tencentmusic.com/chart/uni-chart/search"
        - 输入框中输入"任素汐", 不要发送回车
        """
    )


async def test_web_mobile_05(web_agent_mobile):
    """测试web H5 输入交互"""
    await web_agent_mobile.run(
        """
        - 打开 url "https://yobang.tencentmusic.com/chart/uni-chart/search"
        - 输入框中输入"任素汐"
        """
    )


async def test_web_mobile_06(web_agent_mobile):
    """测试点击相对元素"""
    await web_agent_mobile.run(
        """
        - 打开 url "https://yobang.tencentmusic.com/chart/uni-chart/rankList/"
        - 点击"浪潮榜"左侧的元素
        - 点击"浪潮榜"右侧的元素
        - 点击"浪潮榜"左侧第2个元素
        - 点击"由你榜"右侧第4个元素
        - 点击"LIVE榜"上方的元素
        - 点击"里程碑"下方的元素
        - 在"搜索历史"上方的元素中输入"任素汐"
        """
    )
