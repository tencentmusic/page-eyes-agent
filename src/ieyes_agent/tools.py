#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Author : aidenmo
# @Email : aidenmo@tencent.com
# @Time : 2025/5/23 17:47
import asyncio
import io
from abc import ABC, abstractmethod
from functools import wraps
from pathlib import Path
from traceback import print_exc
from typing import IO, Optional, cast

from httpx import AsyncClient
from loguru import logger
from pydantic_ai import ModelRetry, RunContext
from playwright.async_api import TimeoutError

from .config import global_settings
from .deps import AgentDeps, StepActionInfo, ToolResult, StepInfo, LocationActionInfo, ClickActionInfo, \
    InputActionInfo, SwipeActionInfo, SwipeFromCoordinateActionInfo, OpenUrlActionInfo, ScreenInfo, ToolContext, \
    WaitActionInfo, AssertContainsActionInfo
from .device import AndroidDevice, WebDevice
from .util.adb_tool import AdbDeviceProxy
from .util.js_tool import JSTool
from .util.platform import get_client_url_schema

storage_client = global_settings.storage_client


class ToolHandler:
    """工具调用处理类，用于处理工具函数的前置和后置操作"""

    def __init__(self, *args, **kwargs):
        self.ctx: Optional[RunContext[AgentDeps[WebDevice | AndroidDevice]]] = None
        self.step_action: Optional[StepActionInfo] = None
        self.step_info: Optional[StepInfo] = None

        for arg in [*args, *kwargs.values()]:
            if isinstance(arg, RunContext):
                self.ctx = cast(RunContext[AgentDeps], arg)
                continue
            if isinstance(arg, StepActionInfo):
                self.step_action = arg
                continue

    @property
    def context(self) -> ToolContext:
        return self.ctx and self.ctx.deps.context

    async def pre_handle(self):
        """工具的前置处理"""
        if not all([self.ctx, self.step_action]):
            return
        logger.info(f'🕹 {self.step_action}')
        if self.ctx.deps.settings.debug and isinstance(self.step_action, LocationActionInfo):
            if isinstance(self.ctx.deps.device, WebDevice):
                await JSTool.add_highlight_element(self.ctx.deps.device.page, self.step_action.element_bbox)

        self.step_info = self.ctx.deps.context.steps.setdefault(
            self.step_action.step,
            StepInfo.model_validate(self.step_action)
        )

    async def post_handle(self, tool_result: ToolResult):
        """工具的后置处理"""
        if not all([self.ctx, self.step_action]):
            return
        self.step_info.image_url = self.context.screen_info.image_url
        self.step_info.screen_elements = self.context.screen_info.screen_elements
        self.step_info.is_success = tool_result.is_success
        self.context.screen_info.reset()  # 步骤结束后，重置当前屏幕信息


def tool(f=None, *, delay=1):
    """
    工具函数装饰器，用于标记函数为工具函数，并自动记录步骤信息
    :param f: 被装饰的函数
    :param delay: 操作后的等待时间，单位为秒，默认为1秒
    :return: 装饰后的函数
    """

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):

            try:
                tool_handler = ToolHandler(*args, **kwargs)
                await tool_handler.pre_handle()
                # 工具执行
                result = await func(*args, **kwargs)
                await asyncio.sleep(delay)  # 避免页面渲染慢，不稳定

                await tool_handler.post_handle(result)
                return result
            except Exception as e:
                print_exc()
                logger.error(f"Error occurred in tool '{func.__name__}': {str(e)}")
                raise ModelRetry(f"Error occurred in tool '{func.__name__}': {str(e)}")

        wrapper.is_tool = True
        return wrapper

    if f is not None:
        return decorator(f)
    return decorator


class AgentTool(ABC):
    OMNI_BASE_URL = global_settings.omni_base_url
    OMNI_KEY = global_settings.omni_key

    @property
    def tools(self) -> list:
        result = []
        for item in dir(self):
            if item.startswith('_') or item == 'tools':
                continue
            value = getattr(self, item)
            if callable(value) and hasattr(value, 'is_tool'):
                result.append(value)

        return result

    @staticmethod
    async def _upload_cos(file: IO[bytes], prefix='page-eyes-agent/', suffix='.png') -> str:
        return await storage_client.async_upload_file(file, prefix=prefix, suffix=suffix)

    async def _parse_element(self, file: Optional[IO[bytes]] = None, image_url: Optional[str] = None):
        url = f'{self.OMNI_BASE_URL}/omni/parse/'
        if not file and not image_url:
            raise ValueError('请提供file或image_url')
        async with AsyncClient(timeout=120) as client:
            response = await client.post(url, files={'file': file}, data={'key': self.OMNI_KEY})
            response.raise_for_status()
            return response.json()

    @staticmethod
    @abstractmethod
    async def screenshot(ctx: RunContext[AgentDeps]) -> io.BytesIO:
        raise NotImplementedError

    async def _get_screen_info(self, ctx: RunContext[AgentDeps], parse_element: bool = True) -> ScreenInfo:
        image_buffer = await self.screenshot(ctx)
        if parse_element:
            parsed_data = await self._parse_element(image_buffer)
            image_url = parsed_data.get('labeled_image_url') or ''
            parsed_content_list = parsed_data.get('parsed_content_list') or []
            logger.info(f'👁‍🗨 Get screen info：{image_url}')
        else:
            image_url = await self._upload_cos(image_buffer, suffix=Path(image_buffer.name).suffix)
            parsed_content_list = []

        screen_info = ScreenInfo(image_url=image_url, screen_elements=parsed_content_list)
        # 将当前屏幕信息记录到上下文
        ctx.deps.context.screen_info = screen_info.model_copy(deep=True)
        return screen_info

    @abstractmethod
    async def open_url(self, ctx: RunContext[AgentDeps], action: OpenUrlActionInfo) -> ToolResult:
        raise NotImplementedError

    @abstractmethod
    async def get_screen_info(self, ctx: RunContext[AgentDeps]) -> ToolResult[ScreenInfo]:
        raise NotImplementedError

    @abstractmethod
    async def tear_down(self, ctx: RunContext[AgentDeps], action: StepActionInfo) -> ToolResult:
        raise NotImplementedError

    @tool(delay=0)
    async def wait_for_timeout(self, ctx: RunContext[AgentDeps[WebDevice]], action: WaitActionInfo) -> ToolResult:
        """
        在任务中等待或停留指定的超时时间（action.timeout），单位：秒
        """
        logger.info(f'Wait for timeout {action.timeout}s')
        await asyncio.sleep(action.timeout)
        await self._get_screen_info(ctx, parse_element=False)
        return ToolResult.success()

    @tool(delay=0)
    async def assert_screen_contains(self, ctx: RunContext[AgentDeps[WebDevice]],
                                     action: AssertContainsActionInfo) -> ToolResult:
        """
        断言屏幕中是否出现、存在、包含指定关键字内容，如果是则 is_success=True, 否则 is_success=False
        """
        screen_info: ScreenInfo = await self._get_screen_info(ctx, parse_element=True)
        if action.keyword in str(screen_info.screen_elements):
            logger.info(f'Screen contains keyword "{action.keyword}"')
            return ToolResult.success()
        logger.warning(f'Screen not contains keyword "{action.keyword}"')
        return ToolResult.failed()


class WebAgentTool(AgentTool):

    @staticmethod
    async def screenshot(ctx: RunContext[AgentDeps[WebDevice]]) -> io.BytesIO:
        screenshot = await ctx.deps.device.page.screenshot(full_page=False, style='#option-el-box {display: none;}')
        image_buffer = io.BytesIO(screenshot)
        image_buffer.name = 'screen.png'
        return image_buffer

    @tool(delay=0)
    async def get_screen_info(self, ctx: RunContext[AgentDeps[WebDevice]]) -> ToolResult[dict]:
        """
        获取当前屏幕信息，screen_elements 包含所有解析到的元素信息，bbox 是相对值，格式为 (x1, y1, x2, y2)
        该工具禁止作为一个单独步骤
        """
        screen_info = await self._get_screen_info(ctx)
        return ToolResult.success(screen_info.model_dump(include={'screen_elements'}))

    @tool(delay=0)
    async def tear_down(self, ctx: RunContext[AgentDeps[WebDevice]], action: StepActionInfo) -> ToolResult:
        """
        任务完成后的清理步骤
        """
        await JSTool.remove_highlight_element(ctx.deps.device.page)
        await self._get_screen_info(ctx, parse_element=False)

        if ctx.deps.device.playwright is not None:
            await ctx.deps.device.context.close()
            await ctx.deps.device.playwright.stop()
        return ToolResult.success()

    @tool(delay=0)
    async def open_url(self, ctx: RunContext[AgentDeps[WebDevice]], action: OpenUrlActionInfo) -> ToolResult:
        """
        使用设备打开URL {action.url}
        """
        await ctx.deps.device.page.goto(action.url, wait_until='load')
        await self._get_screen_info(ctx, parse_element=False)
        return ToolResult.success()

    @tool
    async def click(self, ctx: RunContext[AgentDeps[WebDevice]], action: ClickActionInfo) -> ToolResult:
        """
        点击设备屏幕指定的元素, action.element_bbox 不能为空
        """
        x, y = action.get_coordinate(ctx.deps.device.device_size)
        logger.info(f'click coordinate ({x}, {y})')
        try:
            async with ctx.deps.device.page.context.expect_page(timeout=1000) as new_page_info:
                await ctx.deps.device.page.mouse.click(x, y)
            old_page = ctx.deps.device.page
            ctx.deps.device.page = await new_page_info.value
            await old_page.close()
        except TimeoutError:
            pass
        return ToolResult.success()

    @tool(delay=0)
    async def input(self, ctx: RunContext[AgentDeps[WebDevice]], action: InputActionInfo) -> ToolResult:
        """
        在设备指定的元素中输入文本 {action.text}
        """
        x, y = action.get_coordinate(ctx.deps.device.device_size)
        logger.info(f'Input text: ({x}, {y}) -> {action.text}')
        await ctx.deps.device.page.mouse.click(x, y)
        await ctx.deps.device.page.keyboard.type(action.text)
        await ctx.deps.device.page.keyboard.press('Enter')
        return ToolResult.success()

    @staticmethod
    async def _swipe_by_mouse(
            ctx: RunContext[AgentDeps[WebDevice]],
            action: SwipeActionInfo,
            width: int,
            height: int,
            steps: int = 1000
    ):
        if action.to == 'top':
            x1, y1, x2, y2 = 0.5 * width, 0.8 * height, 0.5 * width, 0.2 * height
        elif action.to == 'left':
            x1, y1, x2, y2 = 0.8 * width, 0.5 * height, 0.2 * width, 0.5 * height
        elif action.to == 'bottom':
            x1, y1, x2, y2 = 0.5 * width, 0.2 * height, 0.5 * width, 0.8 * height
        elif action.to == 'right':
            x1, y1, x2, y2 = 0.2 * width, 0.5 * height, 0.8 * width, 0.5 * height
        else:
            raise ValueError(f'Invalid Parameter: to={action.to}')
        x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)
        logger.info(f'Swipe from ({x1}, {y1}) to ({x2}, {y2})')
        # TODO: 禁止滑动的时候选中文字，目前先简单实现，后面寻找更优方案
        el_handle = await ctx.deps.device.page.add_style_tag(content="* {user-select: none !important;}")

        await ctx.deps.device.page.mouse.move(x1, y1)
        await ctx.deps.device.page.mouse.down()
        await ctx.deps.device.page.mouse.move(x2, y2, steps=steps)
        await ctx.deps.device.page.mouse.up()
        await JSTool.remove_element(el_handle)

    @staticmethod
    async def _swipe_by_scroll(
            ctx: RunContext[AgentDeps[WebDevice]],
            action: SwipeActionInfo,
            width: int,
            height: int,
    ):
        if action.to == 'top':
            delta_x, delta_y = 0, 0.9 * height
        elif action.to == 'left':
            delta_x, delta_y = 0.9 * width, 0
        elif action.to == 'bottom':
            delta_x, delta_y = 0, -0.9 * height
        elif action.to == 'right':
            delta_x, delta_y = -0.9 * width, 0
        else:
            raise ValueError(f'Invalid Parameter: to={action.to}')

        logger.info(f'Scroll delta_x={delta_x}, delta_y={delta_y}')
        await ctx.deps.device.page.mouse.wheel(delta_x, delta_y)

    @tool
    async def swipe(self, ctx: RunContext[AgentDeps[WebDevice]], action: SwipeActionInfo) -> ToolResult:
        """
        在设备屏幕中滑动或滚动，参数 action.to 表示目标方向
        """
        logger.info(f'swipe to {action.to}')
        width, height = ctx.deps.device.device_size.width, ctx.deps.device.device_size.height
        has_scroll_bar = await JSTool.has_scrollbar(ctx.deps.device.page, action.to)
        if ctx.deps.device.is_mobile and not has_scroll_bar:
            await self._swipe_by_mouse(ctx, action, width, height)
        else:
            await self._swipe_by_scroll(ctx, action, width, height)

        return ToolResult.success()


class AndroidAgentTool(AgentTool):

    @staticmethod
    async def screenshot(ctx: RunContext[AgentDeps[AndroidDevice]]) -> io.BytesIO:
        image_buffer = io.BytesIO()
        screenshot = ctx.deps.device.adb_device.screenshot()
        screenshot.save(image_buffer, format='webp')
        image_buffer.name = 'screen.webp'
        image_buffer.seek(0)
        return image_buffer

    @tool
    async def get_screen_info(self, ctx: RunContext[AgentDeps[AndroidDevice]]) -> ToolResult:
        """
        获取当前屏幕信息，screen_elements 包含所有解析到的元素信息，bbox 是相对值，格式为 (x1, y1, x2, y2)
        该工具禁止作为一个单独步骤
        """
        screen_info = await self._get_screen_info(ctx)
        return ToolResult.success(screen_info.model_dump(include={'screen_elements'}))

    @tool
    async def tear_down(self, ctx: RunContext[AgentDeps[AndroidDevice]], action: StepActionInfo) -> ToolResult:
        """
        任务完成后的清理步骤，返回步骤信息
        """
        await self._get_screen_info(ctx, parse_element=False)
        return ToolResult.success()

    @tool(delay=0)
    async def open_url(self, ctx: RunContext[AgentDeps[AndroidDevice]], action: OpenUrlActionInfo) -> ToolResult:
        """
        使用设备打开URL {action.url}
        """
        platform = ctx.deps.device.platform
        url_schema = get_client_url_schema(action.url, platform)
        logger.info(f'open schema: {url_schema}')

        ctx.deps.device.adb_device.shell(f'am start -a android.intent.action.VIEW -d "{url_schema}"')
        await asyncio.sleep(2)
        await self._get_screen_info(ctx, parse_element=False)
        return ToolResult.success()

    @tool
    async def click(self, ctx: RunContext[AgentDeps[AndroidDevice]], action: ClickActionInfo) -> ToolResult:
        """
        点击设备屏幕指定的元素
        """
        x, y = action.get_coordinate(ctx.deps.device.device_size)
        logger.info(f'Click coordinate ({x}, {y})')
        ctx.deps.device.adb_device.click(x, y)

        return ToolResult.success()

    @tool(delay=0)
    async def input(self, ctx: RunContext[AgentDeps[AndroidDevice]], action: InputActionInfo):
        """
        在设备指定的元素中输入文本
        """
        x, y = action.get_coordinate(ctx.deps.device.device_size)
        logger.info(f'Input text: ({x}, {y}) -> {action.text}')
        ctx.deps.device.adb_device.click(x, y)
        AdbDeviceProxy(ctx.deps.device.adb_device).input_text(action.text)
        ctx.deps.device.adb_device.keyevent('KEYCODE_ENTER')
        return ToolResult.success()

    @tool
    async def swipe(
            self,
            ctx: RunContext[AgentDeps[AndroidDevice]],
            action: SwipeActionInfo,
    ):
        """
        在设备屏幕中滑动或滚动，参数 action.to 表示目标方向
        """
        logger.info(f'swipe to {action.to}')
        width, height = ctx.deps.device.device_size.width, ctx.deps.device.device_size.height
        if action.to == 'top':
            x1, y1, x2, y2 = 0.5 * width, 0.8 * height, 0.5 * width, 0.1 * height
        elif action.to == 'left':
            x1, y1, x2, y2 = 0.9 * width, 0.5 * height, 0.1 * width, 0.5 * height
        elif action.to == 'bottom':
            x1, y1, x2, y2 = 0.5 * width, 0.2 * height, 0.5 * width, 0.9 * height
        elif action.to == 'right':
            x1, y1, x2, y2 = 0.1 * width, 0.5 * height, 0.9 * width, 0.5 * height
        else:
            raise ValueError(f'Invalid Parameter: to={action.to}')
        x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)
        logger.info(f'Swipe from ({x1}, {y1}) to ({x2}, {y2})')
        ctx.deps.device.adb_device.swipe(x1, y1, x2, y2, duration=2)
        return ToolResult.success()

    @tool
    async def swipe_from_coordinate(
            self,
            ctx: RunContext[AgentDeps[AndroidDevice]],
            action: SwipeFromCoordinateActionInfo,
    ):
        """
        在设备屏幕中根据给定的坐标进行滑动操作，支持传递多个坐标进行连续滑动
        action.coordinates 是滑动坐标值的集合，如[(x1, y1), (x2, y2), ...]
        工具依次从坐标集中取出2组值作为开始坐标(x1, y1)和结束坐标(x2, y2)，直到完成所有坐标的滑动操作
        """
        # TODO: 先判断坐标是否在屏幕范围内
        coordinate_iter = iter(action.coordinates)
        for start_coordinate, end_coordinate in zip(coordinate_iter, coordinate_iter):
            x1, y1 = start_coordinate
            x2, y2 = end_coordinate
            logger.info(f'Swipe from ({x1}, {y1}) to ({x2}, {y2})')
            ctx.deps.device.adb_device.swipe(x1, y1, x2, y2, duration=2)
        return ToolResult.success()
