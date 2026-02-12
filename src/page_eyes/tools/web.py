#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Author : aidenmo
# @Email : aidenmo@tencent.com
# @Time : 2026/2/11 15:50
import asyncio
import io
from typing import TypeAlias

from loguru import logger
# noinspection PyProtectedMember
from playwright.async_api import TimeoutError
from pydantic_ai import RunContext

from .base import AgentTool, tool
from ..deps import ToolParams, ToolResult, ClickToolParams, \
    InputToolParams, SwipeToolParams, OpenUrlToolParams, ToolResultWithOutput, AgentDeps
from ..device import WebDevice
from ..util.js_tool import JSTool

AgentDepsType: TypeAlias = AgentDeps[WebDevice, AgentTool]


class WebAgentTool(AgentTool):

    @staticmethod
    async def screenshot(ctx: RunContext[AgentDepsType]) -> io.BytesIO:
        screenshot = await ctx.deps.device.target.screenshot(full_page=False, style='#option-el-box {display: none;}')
        image_buffer = io.BytesIO(screenshot)
        image_buffer.name = 'screen.png'
        return image_buffer

    @tool
    async def get_screen_info(self, ctx: RunContext[AgentDepsType]) -> ToolResultWithOutput[dict]:
        """
        获取当前屏幕信息，screen_elements 包含所有解析到的元素信息，列表顺序即为屏幕元素的排列顺序，从左到右，从上到下
        每个元素包含以下字段：
        id: 元素的id
        bbox: 元素的相对坐标，格式为 (x1, y1, x2, y2)
        content: 元素描述信息
        left_elem_ids: 该元素左侧的元素列表
        right_elem_ids: 该元素右侧的元素列表
        top_elem_ids: 该元素上方的元素列表
        bottom_elem_ids: 该元素下方的元素列表
        """
        screen_info = await self.get_screen(ctx)
        return ToolResultWithOutput.success(screen_info.model_dump(include={'screen_elements'}))

    @tool
    async def tear_down(self, ctx: RunContext[AgentDepsType], params: ToolParams) -> ToolResult:
        """
        任务完成或结束后的清理操作
        """
        await JSTool.remove_highlight_element(ctx.deps.device.target)
        await self.get_screen(ctx, parse_element=False)

        if ctx.deps.device.client is not None:
            await ctx.deps.device.context.close()
            await ctx.deps.device.client.stop()
        return ToolResult.success()

    @tool(after_delay=2)
    async def open_url(self, ctx: RunContext[AgentDepsType], params: OpenUrlToolParams) -> ToolResult:
        """
        使用设备打开URL
        """
        await ctx.deps.device.target.goto(params.url, wait_until='networkidle')
        return ToolResult.success()

    @tool(after_delay=2)
    async def click(self, ctx: RunContext[AgentDepsType], params: ClickToolParams) -> ToolResult:
        """
        点击设备屏幕指定的元素, element_bbox 不能为空
        """
        x, y = params.get_coordinate(ctx.deps.device.device_size, params.position, params.offset)
        logger.info(f'click coordinate ({x}, {y})')
        await JSTool.add_highlight_position(ctx.deps.device.target, x, y)
        try:
            if params.file_path:
                logger.info(f'upload file ({params.file_path.absolute()})')
                async with ctx.deps.device.target.expect_file_chooser(timeout=5000) as fc_info:
                    await ctx.deps.device.target.mouse.click(x, y)
                    file_chooser = await fc_info.value
                    await file_chooser.set_files(params.file_path)
            else:
                async with ctx.deps.device.target.context.expect_page(timeout=1000) as new_page_info:
                    await ctx.deps.device.target.mouse.click(x, y)
                old_page = ctx.deps.device.target
                ctx.deps.device.target = await new_page_info.value
                await old_page.close()
        except TimeoutError:
            pass
        await JSTool.remove_highlight_position(ctx.deps.device.target)
        return ToolResult.success()

    @tool(after_delay=1)
    async def input(self, ctx: RunContext[AgentDepsType], params: InputToolParams) -> ToolResult:
        """
        在设备指定的元素中输入文本
        """
        x, y = params.get_coordinate(ctx.deps.device.device_size)
        logger.info(f'Input text: ({x}, {y}) -> {params.text}')
        await ctx.deps.device.target.mouse.click(x, y)
        await ctx.deps.device.target.keyboard.type(params.text)
        if params.send_enter:
            await ctx.deps.device.target.keyboard.press('Enter')
        return ToolResult.success()

    @staticmethod
    async def _swipe_by_mouse(
            ctx: RunContext[AgentDepsType],
            params: SwipeToolParams,
            width: int,
            height: int,
            steps: int = 1000
    ):
        if params.to == 'top':
            x1, y1, x2, y2 = 0.5 * width, 0.7 * height, 0.5 * width, 0.1 * height
        elif params.to == 'left':
            x1, y1, x2, y2 = 0.8 * width, 0.5 * height, 0.2 * width, 0.5 * height
        elif params.to == 'bottom':
            x1, y1, x2, y2 = 0.5 * width, 0.3 * height, 0.5 * width, 0.9 * height
        elif params.to == 'right':
            x1, y1, x2, y2 = 0.2 * width, 0.5 * height, 0.8 * width, 0.5 * height
        else:
            raise ValueError(f'Invalid Parameter: to={params.to}')
        x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)
        logger.info(f'Swipe from ({x1}, {y1}) to ({x2}, {y2})')
        # TODO: 禁止滑动的时候选中文字，目前先简单实现，后面寻找更优方案
        el_handle = await ctx.deps.device.target.add_style_tag(content="* {user-select: none !important;}")

        await ctx.deps.device.target.mouse.move(x1, y1)
        await ctx.deps.device.target.mouse.down()
        await ctx.deps.device.target.mouse.move(x2, y2, steps=steps)
        await ctx.deps.device.target.mouse.up()
        await JSTool.remove_element(el_handle)

    @staticmethod
    async def _swipe_by_scroll(
            ctx: RunContext[AgentDepsType],
            params: SwipeToolParams,
            width: int,
            height: int,
    ):
        if params.to == 'top':
            delta_x, delta_y = 0, 0.7 * height
        elif params.to == 'left':
            delta_x, delta_y = 0.7 * width, 0
        elif params.to == 'bottom':
            delta_x, delta_y = 0, -0.7 * height
        elif params.to == 'right':
            delta_x, delta_y = -0.7 * width, 0
        else:
            raise ValueError(f'Invalid Parameter: to={params.to}')

        logger.info(f'Scroll delta_x={delta_x}, delta_y={delta_y}')
        await ctx.deps.device.target.mouse.wheel(delta_x, delta_y)

    @tool(after_delay=1)
    async def swipe(self, ctx: RunContext[AgentDepsType], params: SwipeToolParams) -> ToolResult:
        """
        在设备屏幕中滑动或滚动
        """
        width, height = ctx.deps.device.device_size.width, ctx.deps.device.device_size.height
        has_scroll_bar = await JSTool.has_scrollbar(ctx.deps.device.target, params.to)

        if params.repeat_times is None:
            if params.expect_keywords:
                params.repeat_times = 10
            else:
                params.repeat_times = 1
        for times in range(1, params.repeat_times + 1):
            logger.info(f'swipe to {params.to}, times={times}')

            if ctx.deps.device.is_mobile and not has_scroll_bar:
                await self._swipe_by_mouse(ctx, params, width, height)
            else:
                await self._swipe_by_scroll(ctx, params, width, height)

            if params.expect_keywords:
                await asyncio.sleep(1)  # 避免滑动后截图，元素还未稳定出现
                result = await self.expect_screen_contains(ctx, params.expect_keywords)
                if result.is_success:
                    return result
                if times == params.repeat_times:
                    return ToolResult.failed()

        return ToolResult.success()

    @tool(after_delay=1)
    async def goback(self, ctx: RunContext[AgentDepsType], params: ToolParams) -> ToolResult:
        """
        操作返回到上一个页面
        """
        logger.info(f'go to previous page')
        await ctx.deps.device.target.go_back()
        return ToolResult.success()
