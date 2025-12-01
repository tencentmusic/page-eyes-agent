#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Author : aidenmo
# @Email : aidenmo@tencent.com
# @Time : 2025/9/28 16:35
import pytest
from loguru import logger

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def test_01(planning_agent):
    """
    [
        {'instruction': '打开 url "https://wma.wavecommittee.com/"'},
        {'instruction': '点击 "浪潮评委会成员" 按钮'}
    ]

    """
    result = await planning_agent.run(
        """
        - 打开 url "https://wma.wavecommittee.com/"
        - 点击浪潮评委会成员按钮
        """
    )
    logger.info(result.output)
    logger.info(result.output.model_dump().get('steps'))


async def test_02(planning_agent):
    """
    [
        {'instruction': '打开 "QQ音乐" APP'},
        {'instruction': '点击"close"关闭弹窗，若"close"元素不存在则跳过'},
        {'instruction': '向上滑动最多 10 次，直到页面中出现"搜索2025年上榜歌手"元素'},
        {'instruction': '点击"搜索"'},
        {'instruction': '等待 2 秒'},
        {'instruction': '输入"周杰伦"'},
        {'instruction': '向上滑动 3 次'}
    ]
    """
    result = await planning_agent.run(
        """
        打开QQ音乐APP，点击"close"关闭弹窗，如果点击的元素不存在则跳过，向上滑动最多10次，直到页面中出现"搜索2025年上榜歌手"元素，点击"搜索"
        等待2s，然后输入"周杰伦"，最后向上滑动3次'
        """
    )
    logger.info(result.output)
    logger.info(result.output.model_dump().get('steps'))


async def test_03(planning_agent):
    """
    """
    result = await planning_agent.run(
        """
        上滑多次，直到出现"查看浪潮评委会"元素
        """
    )
    logger.info(result.output)
    logger.info(result.output.model_dump().get('steps'))


async def test_04(planning_agent):
    """
    """
    result = await planning_agent.run(
        """
        点击"推荐"按钮, 等待3秒, 点击"去酷我音乐推荐"
        """
    )
    logger.info(result.output)
    logger.info(result.output.model_dump().get('steps'))


async def test_06(planning_agent):
    """
    """
    result = await planning_agent.run(
        """
        - 打开 url "https://yobang.tencentmusic.com/chart/uni-chart/search"
        - 输入框中输入"任素汐", 不要发送回车键
        """
    )
    logger.info(result.output)
    logger.info(result.output.model_dump().get('steps'))
