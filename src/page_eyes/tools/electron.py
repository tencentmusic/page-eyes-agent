#!/usr/bin/env python
# -*- coding: utf-8 -*-
import asyncio
import io
from typing import TypeAlias

from loguru import logger
from playwright.async_api import Error as PlaywrightError
from playwright.async_api import TimeoutError
from pydantic_ai import RunContext

from ..deps import AgentDeps, ClickToolParams, ToolParams, ToolResult
from ..device import ElectronDevice
from ..util.js_tool import JSTool
from ._base import AgentTool, tool
from .web import WebAgentTool

AgentDepsType: TypeAlias = AgentDeps[ElectronDevice, AgentTool]


class ElectronAgentTool(WebAgentTool):
    """Electron 特定的 Agent 工具合集。"""

    @staticmethod
    async def screenshot(ctx: RunContext[AgentDepsType]) -> io.BytesIO:
        """获取当前活跃窗口的屏幕截图。

        Args:
            ctx: 运行上下文

        Returns:
            生成的图片字节流
        """
        # 每次截图前检测是否有新窗口，确保截到最新/活跃窗口
        await ctx.deps.device.switch_to_latest_page()
        page = ctx.deps.device.target
        # scale='css' 强制以 1x 分辨率截图，消除 Retina (DPR=2) 下
        # 截图像素与 CSS 坐标不一致导致的点击偏移
        screenshot = await page.screenshot(
            full_page=False,
            scale="css",
        )
        image_buffer = io.BytesIO(screenshot)
        image_buffer.name = "screen.png"
        return image_buffer

    @tool(after_delay=2)
    async def click(
        self, ctx: RunContext[AgentDepsType], params: ClickToolParams
    ) -> ToolResult:
        """点击设备屏幕指定的元素，element_bbox 不能为空。

        Args:
            ctx: 运行上下文
            params: 点击工具的具体参数

        Returns:
            执行结果信息封装
        """
        x, y = params.get_coordinate(ctx, params.position, params.offset)
        logger.info(f"click coordinate ({x}, {y})")
        await JSTool.add_highlight_position(ctx.deps.device.target, x, y)

        pages_before = len(ctx.deps.device.context.pages)
        try:
            if params.file_path:
                logger.info(f"upload file ({params.file_path.absolute()})")
                async with ctx.deps.device.target.expect_file_chooser(
                    timeout=5000
                ) as fc_info:
                    await ctx.deps.device.target.mouse.click(x, y)
                    file_chooser = await fc_info.value
                    await file_chooser.set_files(params.file_path)
            else:
                await ctx.deps.device.target.mouse.click(x, y)
        except TimeoutError:
            pass

        # 检测是否有新窗口打开，有则自动切换
        await asyncio.sleep(0.5)
        if len(ctx.deps.device.context.pages) > pages_before:
            await ctx.deps.device.switch_to_latest_page()

        try:
            await JSTool.remove_highlight_position(ctx.deps.device.target)
        except PlaywrightError as e:
            logger.warning(f"切换窗口后旧页面的高亮清理失败: {e}")
        return ToolResult.success()

    @tool(after_delay=1)
    async def close_window(
        self, ctx: RunContext[AgentDepsType], params: ToolParams
    ) -> ToolResult:
        """关闭当前窗口。如果还有其他窗口，会自动切换到上一个窗口。

        Args:
            ctx: 运行上下文
            params: 工具的基础参数

        Returns:
            执行结果信息封装
        """
        pages = ctx.deps.device.context.pages
        if len(pages) <= 1:
            logger.warning("只剩一个窗口，不执行关闭")
            return ToolResult.failed()

        current = ctx.deps.device.target
        logger.info(f"🗙 关闭当前窗口（剩余 {len(pages)} 个）")
        await current.close()
        # page_stack 的 close 事件回调会自动回退 target
        await asyncio.sleep(0.5)
        await self.get_screen(ctx, parse_element=False)
        return ToolResult.success()

    @tool
    async def tear_down(
        self, ctx: RunContext[AgentDepsType], params: ToolParams
    ) -> ToolResult:
        """任务完成或结束后的清理操作。

        注意：不关闭 browser，Electron 进程由外部管理。

        Args:
            ctx: 运行上下文
            params: 工具的基础参数

        Returns:
            执行结果信息封装
        """
        await JSTool.remove_highlight_element(ctx.deps.device.target)
        await self.get_screen(ctx, parse_element=False)
        return ToolResult.success()
