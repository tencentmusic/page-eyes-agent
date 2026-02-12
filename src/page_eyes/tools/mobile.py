#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Author : aidenmo
# @Email : aidenmo@tencent.com
# @Time : 2026/2/12 14:59
import asyncio
import io
from typing import TypeAlias, Union

from loguru import logger
from pydantic_ai import RunContext, Agent

from .base import AgentTool, tool
from ..deps import ToolParams, ToolResult, ClickToolParams, \
    InputToolParams, SwipeToolParams, SwipeFromCoordinateToolParams, OpenUrlToolParams, ToolResultWithOutput, AgentDeps
from ..device import AndroidDevice, HarmonyDevice, IOSDevice
from ..util.adb_tool import AdbDeviceProxy
from ..util.platform import get_client_url_schema

AgentDepsType: TypeAlias = AgentDeps[
    Union[AndroidDevice, HarmonyDevice, IOSDevice],
    'AgentTool',
]


class MobileAgentTool(AgentTool):

    @staticmethod
    def _start_url(ctx: RunContext[AgentDepsType], url: str):
        raise NotImplementedError

    @staticmethod
    async def screenshot(ctx: RunContext[AgentDepsType]) -> io.BytesIO:
        image_buffer = io.BytesIO()
        screenshot = ctx.deps.device.target.screenshot()
        screenshot.save(image_buffer, format='png')
        image_buffer.name = 'screen.png'
        image_buffer.seek(0)
        return image_buffer

    @tool
    async def get_screen_info(self, ctx: RunContext[AgentDepsType]) -> ToolResultWithOutput[dict]:
        """
        获取当前屏幕信息，screen_elements 包含所有解析到的元素信息，bbox 是相对值，格式为 (x1, y1, x2, y2)
        该工具禁止作为一个单独步骤
        """
        screen_info = await self.get_screen(ctx)
        return ToolResultWithOutput.success(screen_info.model_dump(include={'screen_elements'}))

    async def tear_down(self, ctx: RunContext[AgentDepsType], params: ToolParams) -> ToolResult:
        """
        任务完成或结束后的清理操作
        """
        await self.get_screen(ctx, parse_element=False)
        return ToolResult.success()

    @tool(after_delay=0)
    async def open_url(self, ctx: RunContext[AgentDepsType], params: OpenUrlToolParams) -> ToolResult:
        """
        使用设备打开URL
        """
        platform = ctx.deps.device.platform
        url_schema = get_client_url_schema(params.url, platform)
        logger.info(f'open schema: {url_schema}')
        self._start_url(ctx, url_schema)
        await asyncio.sleep(2)
        await self.get_screen(ctx, parse_element=False)
        return ToolResult.success()

    @tool
    async def click(self, ctx: RunContext[AgentDepsType], params: ClickToolParams) -> ToolResult:
        """
        点击设备屏幕指定的元素
        """
        x, y = params.get_coordinate(ctx.deps.device.device_size, params.position, params.offset)
        logger.info(f'Click coordinate ({x}, {y})')
        ctx.deps.device.target.click(x, y)

        return ToolResult.success()

    @tool(after_delay=0)
    async def input(self, ctx: RunContext[AgentDepsType], params: InputToolParams):
        """
        在设备指定的元素中输入文本
        """
        x, y = params.get_coordinate(ctx.deps.device.device_size)
        logger.info(f'Input text: ({x}, {y}) -> {params.text}')
        ctx.deps.device.target.click(x, y)
        AdbDeviceProxy(ctx.deps.device.target).input_text(params.text)
        if params.send_enter:
            ctx.deps.device.target.keyevent('KEYCODE_ENTER')
        return ToolResult.success()

    @tool
    async def swipe(
            self,
            ctx: RunContext[AgentDepsType],
            params: SwipeToolParams,
    ):
        """
        在设备屏幕中滑动或滚动，参数 to 表示目标方向
        """
        logger.info(f'swipe to {params.to}')
        width, height = ctx.deps.device.device_size.width, ctx.deps.device.device_size.height
        if params.to == 'top':
            x1, y1, x2, y2 = 0.5 * width, 0.7 * height, 0.5 * width, 0.1 * height
        elif params.to == 'left':
            x1, y1, x2, y2 = 0.7 * width, 0.5 * height, 0.1 * width, 0.5 * height
        elif params.to == 'bottom':
            x1, y1, x2, y2 = 0.5 * width, 0.3 * height, 0.5 * width, 0.9 * height
        elif params.to == 'right':
            x1, y1, x2, y2 = 0.3 * width, 0.5 * height, 0.9 * width, 0.5 * height
        else:
            raise ValueError(f'Invalid Parameter: to={params.to}')
        x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)

        if params.repeat_times is None:
            if params.expect_keywords:
                params.repeat_times = 10
            else:
                params.repeat_times = 1
        for times in range(1, params.repeat_times + 1):
            logger.info(f'Swipe from ({x1}, {y1}) to ({x2}, {y2}), times={times}')
            ctx.deps.device.target.swipe(x1, y1, x2, y2, duration=2)
            if params.expect_keywords:
                await asyncio.sleep(1)  # 避免滑动后截图，元素还未稳定出现
                result = await self.expect_screen_contains(ctx, params.expect_keywords)
                if result.is_success:
                    return result
                if times == params.repeat_times:
                    return ToolResult.failed()

        return ToolResult.success()

    @tool
    async def swipe_from_coordinate(
            self,
            ctx: RunContext[AgentDepsType],
            params: SwipeFromCoordinateToolParams,
    ):
        """
        在设备屏幕中根据给定的坐标进行滑动操作，支持传递多个坐标进行连续滑动
        coordinates 是滑动坐标值的集合，如[(x1, y1), (x2, y2), ...]
        工具依次从坐标集中取出2组值作为开始坐标(x1, y1)和结束坐标(x2, y2)，直到完成所有坐标的滑动操作
        """
        # TODO: 先判断坐标是否在屏幕范围内
        coordinate_iter = iter(params.coordinates)
        for start_coordinate, end_coordinate in zip(coordinate_iter, coordinate_iter):
            x1, y1 = start_coordinate
            x2, y2 = end_coordinate
            logger.info(f'Swipe from ({x1}, {y1}) to ({x2}, {y2})')
            ctx.deps.device.target.swipe(x1, y1, x2, y2, duration=2)
        return ToolResult.success()

    @tool
    async def open_app(
            self,
            ctx: RunContext[AgentDepsType],
            params: ToolParams,
    ):
        """
        在设备中打开APP, 打开应用
        """
        packages: list[str] = ctx.deps.device.target.list_packages(filter_list=['-e'])
        sub_agent = Agent(
            ctx.model,
            output_type=str,
            system_prompt='你是一个移动端应用助手，负责根据用户输入的指令从提供的应用包名列表找出用户指令对应的包名，并仅返回包名，如果都不匹配则返回空字符串'
        )
        prompt = (f'用户指令：{params.instruction}\n'
                  f'应用包名列表：{packages}')
        result = await sub_agent.run(prompt, output_type=str)
        package_name = result.output
        if not package_name:
            return ToolResultWithOutput.failed(output='在该设备中未找到对应的应用')
        logger.info(f'Find App package name：{package_name}')
        ctx.deps.device.target.app_start(package_name)
        await asyncio.sleep(2)
        await self.get_screen(ctx, parse_element=False)
        return ToolResult.success()
