#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Author : xinttan
# @Email : xinttan@tencent.com
# @Time : 2025/2/11 16:35
import pytest

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def test_ios_01(ios_agent):
    """综合交互测试 - URL打开、搜索、滑动"""
    await ios_agent.run(
        """
        - 打开 url "https://yobang.tencentmusic.com/chart/uni-chart/rankList/"
        - 检查页面是否有 "close" 按钮，如果有则点击 "close" 按钮
        - 进入日榜
        - 点击排名第一的歌曲名
        """
    )


async def test_ios_02(ios_agent):
    """回到桌面、打开应用测试"""
    await ios_agent.run(
        """
        - 回到桌面
        - 打开设置应用
        - 进入通用设置
        - 进入关于本机
        - 查看iOS版本信息
        -再返回上一页，再回到桌面，再打开短信应用
        """
    )


async def test_ios_03(ios_agent):
    """打开URL、回退测试"""
    await ios_agent.run(
        """
        - 打开url"apple.com"
        - 再打开url"baidu.com"
        - 向上滑动两次，再往下滑动一次
        - 返回上一页
        """
    )


async def test_ios_04(ios_agent):
    """打开URL，搜索测试"""
    await ios_agent.run(
        """
        - 打开"baidu.com"
        - 打开搜索框
        - 输入"2026blast春决"
        """
    )


async def test_ios_05(ios_agent):
    """测试批量断言"""
    await ios_agent.run(
        """
        - 打开 url "https://yobang.tencentmusic.com/chart/uni-chart/rankList/"
        - 检查屏幕中出现"浪潮榜"、"由你榜"、"LIVE榜"
        """
    )


async def test_ios_06(ios_agent):
    """测试等待"""
    await ios_agent.run(
        """
        - 打开 url "https://yobang.tencentmusic.com/chart/uni-chart/rankList/"
        - 等待2秒
        - 点击"搜索"按钮
        - 等待3秒，直到出现搜索输入框
        """
    )


async def test_ios_07(ios_agent):
    """测试滑动操作"""
    await ios_agent.run(
        """
        - 打开 url "https://yobang.tencentmusic.com/chart/uni-chart/rankList/"
        - 上滑2次
        - 下滑1次
        """
    )



async def test_ios_09(ios_agent):
    """测试输入交互，输入后默认会自动回车"""
    await ios_agent.run(
        """
        - 打开 url "https://yobang.tencentmusic.com/chart/uni-chart/search"
        - 在搜索输入框中输入"任素汐"
        - 等待3秒，直到出现搜索结果
        """
    )


async def test_ios_10(ios_agent):
    """测试输入交互，不发送回车"""
    await ios_agent.run(
        """
        - 打开 url "https://yobang.tencentmusic.com/chart/uni-chart/search"
        - 输入框中输入"任素汐", 不要发送回车
        """
    )

async def test_ios_13(ios_agent):
    """测试条件判断和操作"""
    await ios_agent.run(
        """
        - 打开 url "https://yobang.tencentmusic.com/chart/uni-chart/rankList/"
        - 如果出现弹窗则点击 "关闭" 或 "跳过" 或 "close"否则跳过直接进行下一步
        - 点击"搜索"按钮
        """
    )

async def test_ios_15(ios_agent):
    """测试操作不存在的元素"""
    await ios_agent.run(
        """
        - 打开 url "https://yobang.tencentmusic.com/chart/uni-chart/rankList/"
        - 点击"确定"按钮
        """
    )


async def test_ios_16(ios_agent):
    """测试原生应用操作 - 设置应用"""
    await ios_agent.run(
        """
        - 回到桌面
        - 打开设置应用
        - 点击"通用"
        - 检查页面包含"软件更新"、"关于本机"
        - 返回上一页
        """
    )


async def test_ios_17(ios_agent):
    """测试坐标滑动"""
    await ios_agent.run(
        """
        - 打开 url "https://yobang.tencentmusic.com/chart/uni-chart/rankList/"
        - 从 (350, 500) 滑动到 (350, 100)
        - 从 (350, 100) 滑动到 (350, 500)
        """
    )


async def test_ios_18(ios_agent):
    """测试复杂条件判断"""
    await ios_agent.run(
        """
        - 打开 url "https://i2.y.qq.com/n3/coin_center/pages/client_v1/index.html"
        - 如果出现"立即签到"则点击"立即签到"，否则跳过
        - 如果出现"close"元素，则点击"close"元素，否则跳过
        - 等待2秒
        """
    )


async def test_ios_19(ios_agent):
    """测试多次点击相同元素"""
    await ios_agent.run(
        """
        - 打开 url "https://yobang.tencentmusic.com/chart/uni-chart/rankList/"
        - 连续点击"搜索"按钮2次
        """
    )


async def test_ios_20(ios_agent):
    """测试在相对元素中输入"""
    await ios_agent.run(
        """
        - 打开 url "https://yobang.tencentmusic.com/chart/uni-chart/rankList/"
        - 点击"搜索"
        - 在"搜索历史"上方的元素中输入"任素汐"
        """
    )

async def test_ios_21(ios_agent):
    """测试长按复制歌名"""
    await ios_agent.run(
        """
        - 打开qq音乐app
        - 搜索"蔡徐坤"
        - 向下滑动直到出现"What a Day"
        - 长按"What a Day",在弹出的菜单中点击"复制"
        """
    )

async def test_ios_22(ios_agent):
    """测试连续打开应用"""
    await ios_agent.run(
        """
        - 打开设置，再打开地图，再打开日历，再打开照片
        """
    )
