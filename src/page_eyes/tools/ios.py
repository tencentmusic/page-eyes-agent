#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Author : xinttan
# @Email : xinttan@tencent.com
# @Time : 2025/2/11 16:35
import asyncio
import io
from typing import TypeAlias

from loguru import logger
from pydantic_ai import RunContext, Agent

from ._mobile import MobileAgentTool
from ..deps import (
    AgentDeps, ToolParams, ToolResult, ToolResultWithOutput,
    ClickToolParams, InputToolParams, SwipeToolParams,
    SwipeFromCoordinateToolParams, OpenUrlToolParams
)
from ..device import IOSDevice
from ._base import tool

AgentDepsType: TypeAlias = AgentDeps[IOSDevice, 'IOSAgentTool']


class IOSAgentTool(MobileAgentTool):
    """iOS设备自动化工具类
    """

    @staticmethod
    async def screenshot(ctx: RunContext[AgentDepsType]) -> io.BytesIO:
        """截图并返回字节流"""
        image_buffer = io.BytesIO()
        screenshot = ctx.deps.device.target.screenshot()

        # 兼容不同版本的返回值
        if hasattr(screenshot, 'save'):
            # PIL Image 对象
            screenshot.save(image_buffer, format='PNG')
        else:
            # 字节流
            image_buffer.write(screenshot)

        image_buffer.name = 'screen.png'
        image_buffer.seek(0)
        return image_buffer

    @tool(after_delay=1)
    async def click(self, ctx: RunContext[AgentDepsType], params: ClickToolParams) -> ToolResult:
        """
        点击指定元素
        iOS使用WDA的tap方法
        """
        logger.info(f'click element: {params.element_content}')

        device = ctx.deps.device

        # 计算点击坐标
        x, y = params.get_coordinate(device.device_size, params.position, params.offset)

        # 执行点击
        device.target.session().tap(x,y)

        return ToolResult.success()

    @tool(after_delay=1)
    async def input(self, ctx: RunContext[AgentDepsType], params: InputToolParams) -> ToolResult:
        """
        在指定元素中输入文本
        iOS使用WDA的send_keys方法
        """
        logger.info(f'input text: {params.text} to element: {params.element_content}')

        device = ctx.deps.device

        # 计算点击坐标
        x, y = params.get_coordinate(device.device_size)

        # 将 session 转换为 WdaSession 并使用扩展方法
        device.client.tap_and_input(x, y, params.text, params.send_enter)

        return ToolResult.success()

    @tool(after_delay=1)
    async def swipe(self, ctx: RunContext[AgentDepsType], params: SwipeToolParams) -> ToolResult:
        """
        滑动屏幕
        iOS使用WDA的swipe方法
        """
        logger.info(f'swipe {params.to}, repeat_times: {params.repeat_times}')

        device = ctx.deps.device
        session = device.target.session()
        width, height = device.device_size.width, device.device_size.height

        # 定义滑动起点和终点
        center_x = width // 2
        swipe_configs = {
            'top': (center_x, int(height * 0.7), center_x, int(height * 0.3)),
            'bottom': (center_x, int(height * 0.3), center_x, int(height * 0.7)),
            'left': (int(width * 0.7), height // 2, int(width * 0.3), height // 2),
            'right': (int(width * 0.3), height // 2, int(width * 0.7), height // 2)
        }

        x1, y1, x2, y2 = swipe_configs[params.to]

        repeat_times = params.repeat_times or 999
        for times in range(1, repeat_times + 1):
            session.swipe(x1, y1, x2, y2)
            logger.info(f'swipe {params.to} times: {times}')

            if params.expect_keywords:
                await asyncio.sleep(1)
                result = await self.expect_screen_contains(ctx, params.expect_keywords)
                if result.is_success:
                    return result
                if times == params.repeat_times:
                    return ToolResult.failed()

        return ToolResult.success()

    @tool(after_delay=1)
    async def swipe_from_coordinate(
            self,
            ctx: RunContext[AgentDepsType],
            params: SwipeFromCoordinateToolParams,
    ) -> ToolResult:
        """
        在设备屏幕中根据给定的坐标进行滑动操作，支持传递多个坐标进行连续滑动
        coordinates 是滑动坐标值的集合，如[(x1, y1), (x2, y2), ...]
        工具依次从坐标集中取出2组值作为开始坐标(x1, y1)和结束坐标(x2, y2)，直到完成所有坐标的滑动操作
        """
        logger.info(f'swipe from coordinates: {params.coordinates}')

        device = ctx.deps.device
        session = device.target.session()
        width, height = device.device_size.width, device.device_size.height

        # 验证坐标是否在屏幕范围内
        for x, y in params.coordinates:
            if not (0 <= x <= width and 0 <= y <= height):
                logger.warning(f'Coordinate ({x}, {y}) is out of screen bounds ({width}x{height})')
                return ToolResult.failed(f'坐标 ({x}, {y}) 超出屏幕范围 ({width}x{height})')

        # 依次从坐标集中取出2组值进行滑动
        coordinate_iter = iter(params.coordinates)
        swipe_count = 0
        for start_coordinate, end_coordinate in zip(coordinate_iter, coordinate_iter):
            x1, y1 = start_coordinate
            x2, y2 = end_coordinate
            logger.info(f'Swipe from ({x1}, {y1}) to ({x2}, {y2})')
            session.swipe(x1, y1, x2, y2)
            swipe_count += 1

        logger.info(f'Completed {swipe_count} swipe(s)')
        return ToolResult.success()

    @tool(after_delay=1)
    async def goback(self, ctx: RunContext[AgentDepsType], params: ToolParams) -> ToolResult:
        """
        返回到上一个页面
        这里优先尝试查找并点击导航栏的返回按钮，如果没有则使用边缘滑动手势
        """
        logger.info('go to previous page')

        device = ctx.deps.device
        session = device.target.session()
        try:
            # 方法1：尝试查找并点击导航栏的返回按钮
            back_button = None

            # 尝试通过不同的方式查找返回按钮
            for selector in [
                {'type': 'XCUIElementTypeButton', 'name': '返回'},
                {'type': 'XCUIElementTypeButton', 'label': 'Back'},
                {'type': 'XCUIElementTypeButton', 'name': 'Back'},
            ]:
                try:
                    back_button = session(**selector)
                    if back_button.exists:
                        back_button.click()
                        logger.info('点击导航栏返回按钮')
                        return ToolResult.success()
                except:
                    continue
            # 方法2：如果没找到返回按钮，使用屏幕左边缘滑动手势
            logger.info('使用左边缘滑动手势返回')
            height = device.device_size.height
            width = device.device_size.width
            session.swipe(10, height // 2, width // 2, height // 2, duration=0.3)

        except Exception as e:
            logger.warning(f'返回操作失败: {e}，尝试备用方案')
            # 备用方案：使用更简单的滑动
            height = device.device_size.height
            session.swipe(10, height // 2, 200, height // 2)

        return ToolResult.success()

    @tool(after_delay=1)
    async def home(self, ctx: RunContext[AgentDepsType], params: ToolParams) -> ToolResult:
        """
        返回主屏幕
        """
        logger.info('go to home')

        session = ctx.deps.device.target.session()
        session.home()

        return ToolResult.success()

    @tool
    async def open_url(self, ctx: RunContext[AgentDepsType], params: OpenUrlToolParams) -> ToolResult:
        """
        使用iOS设备打开URL
        iOS通过Safari浏览器打开URL
        """
        logger.info(f'Open URL: {params.url}')

        # 格式化URL，确保有正确的协议头
        url = params.url.strip()
        if not url.startswith(('http://', 'https://')):
            # 如果没有协议头，添加https://
            if '.' in url and not url.startswith('www.'):
                url = f'https://{url}'
            else:
                url = f'https://www.{url}' if not url.startswith('www.') else f'https://{url}'

        logger.info(f'格式化后的URL: {url}')

        session = ctx.deps.device.target.session()

        # 先启动Safari浏览器
        session.app_launch('com.apple.mobilesafari')
        await asyncio.sleep(1)

        # 使用URL scheme打开网址
        session.open_url(url)

        await asyncio.sleep(2)
        await self.get_screen(ctx, parse_element=False)
        return ToolResult.success()

    @tool
    async def open_app(
            self,
            ctx: RunContext[AgentDepsType],
            params: ToolParams,
    ):
        """
        在设备中打开或启动指定的应用(APP)
        iOS使用Bundle ID启动应用
        """
        logger.info(f'打开应用指令: {params.instruction}')

        # 从 app_name_map 中查找匹配的 Bundle ID，优先级高于默认，因为如displayName=信息的app有两个bundle id（com.apple.MobileSMS和com.apple.mobilesms.compose）
        app_name_map = ctx.deps.app_name_map
        if app_name_map:
            instruction_lower = params.instruction.lower()
            for name, bid in app_name_map.items():
                if name.lower() in instruction_lower:
                    logger.info(f'从 app_name_map 中匹配到应用: {name} -> {bid}')
                    session = ctx.deps.device.target.session()
                    session.app_launch(bid)
                    await asyncio.sleep(2)
                    await self.get_screen(ctx, parse_element=False)
                    return ToolResult.success()

        # 获取设备上所有应用的Bundle ID和显示名称
        app_list = ctx.deps.device.client.get_app_list()
        logger.info(f'Found {len(app_list)} apps on device')

        # 使用LLM从应用列表中智能匹配
        sub_agent = Agent(
            ctx.model,
            output_type=str,
            system_prompt='你是一个移动端应用助手，负责根据用户输入的指令从提供的应用列表中找出用户指令对应的Bundle ID，并仅返回Bundle ID（不要返回其他内容），如果都不匹配则请你推理返回对应的Bundle ID'
        )
        prompt = (f'用户指令：{params.instruction}\n'
                  f'应用列表（Bundle ID | 显示名称）：\n' +
                  '\n'.join([f"{app.bundle_id} | {app.display_name}" for app in app_list]))
        result = await sub_agent.run(prompt, output_type=str)
        bundle_id = result.output

        if not bundle_id:
            return ToolResultWithOutput.failed(output='在该设备中未找到对应的应用')

        logger.info(f'Find App Bundle ID：{bundle_id}')

        # 启动应用
        session = ctx.deps.device.target.session()
        session.app_launch(bundle_id)
        await asyncio.sleep(2)
        await self.get_screen(ctx, parse_element=False)
        return ToolResult.success()
