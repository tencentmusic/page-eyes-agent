#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Author : aidenmo
# @Email : aidenmo@tencent.com
# @Time : 2025/9/28 16:35
import pytest

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def test_web_pc_03(web_agent_mobile):
    """综合交互测试"""
    from page_eyes.tools import WebAgentTool
    from httpx import Client
    import io

    async def screenshot(*args, **kwargs) -> io.BytesIO:
        """截图"""
        url = 'https://tme-dev-test-cos-1257943044.cos-internal.ap-guangzhou.tencentcos.cn/page-shot/image/f7c626ab4fcbd803e4c9eef7461298d1.png'
        with Client() as client:
            response = client.get(url)
            image_buffer = io.BytesIO(response.content)
            image_buffer.name = 'screen.png'
            image_buffer.seek(0)
            return image_buffer

    WebAgentTool.screenshot = screenshot

    await web_agent_mobile.run(
        """
        - 点击推荐按钮
        """
    )


async def test_mobile_04(web_agent_mobile):
    """测试多个交互"""
    await web_agent_mobile.run(
        """
        - 打开 url https://yobang.tencentmusic.com/chart/live-chart/rankList/
        - 点击"推荐"按钮
        """
    )
