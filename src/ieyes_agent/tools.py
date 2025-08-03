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

from .config import global_settings
from .deps import AgentDeps, StepActionInfo, ToolResult, StepInfo, LocationActionInfo, ClickActionInfo, \
    InputActionInfo, SwipeActionInfo, SwipeFromCoordinateActionInfo, OpenUrlActionInfo, ScreenInfo, ToolContext
from .device import AndroidDevice, WebDevice
from .util.adb_tool import AdbDeviceProxy
from .util.platform import get_client_url_schema

cos_client = global_settings.cos_client


class ToolHandler:
    """工具调用处理类，用于处理工具函数的前置和后置操作"""

    def __init__(self, *args, **kwargs):
        self.ctx: Optional[RunContext[AgentDeps]] = None
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

    def pre_handle(self):
        """工具的前置处理"""
        if not all([self.ctx, self.step_action]):
            return
        self.step_info = self.ctx.deps.context.steps.setdefault(
            self.step_action.step,
            StepInfo.model_validate(self.step_action)
        )

    def post_handle(self, tool_result: ToolResult):
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
                tool_handler.pre_handle()
                # 工具执行
                result = await func(*args, **kwargs)
                await asyncio.sleep(delay)  # 避免页面渲染慢，不稳定

                tool_handler.post_handle(result)
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


def drawer_box(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        ctx: Optional[RunContext[AgentDeps[WebDevice]]] = None
        bbox: Optional[list[float]] = None
        for arg in [*args, *kwargs.values()]:
            if isinstance(arg, RunContext):
                ctx = cast(RunContext[AgentDeps[WebDevice]], arg)
                continue
            if isinstance(arg, LocationActionInfo):
                bbox = arg.element_bbox
                continue
        if ctx and ctx.deps.settings.debug and bbox:
            await ctx.deps.device.page.evaluate("""
            ([bbox]) => {
                let box = document.querySelector("#option-el-box")
                if (!box) {
                    box = document.createElement("div");
                    box.id = "option-el-box";
                    box.style.position = "absolute";
                    box.style.zIndex = "1000";
                    box.style.border = "2px solid rgba(255,0,0)";
                    box.style.borderRadius = "5px";
                    box.style.pointerEvents = "none"
                    document.body.appendChild(box);
                }
                const [x1, y1, x2, y2] = bbox
                box.style.top = y1 * 100 + "%"
                box.style.left = x1 * 100 + "%"
                box.style.width = (x2 - x1) * 100 + "%"
                box.style.height = (y2 - y1) * 100 + "%"
                return box
            }
            """, [bbox])
        return await func(*args, **kwargs)

    return wrapper


class AgentTool(ABC):
    OMNI_BASE_URL = global_settings.omni_base_url
    COS_BASE_URL = global_settings.cos_base_url

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
        return await cos_client.async_upload_file(file, prefix=prefix, suffix=suffix)

    async def _parse_element(self, file: Optional[IO[bytes]] = None, image_url: Optional[str] = None):
        url = f'{self.OMNI_BASE_URL}/omni/parse/'
        if not file and not image_url:
            raise ValueError('请提供file或image_url')
        async with AsyncClient() as client:
            response = await client.post(url, files={'file': file})
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
            logger.info(f'获取当前屏幕元素信息：{image_url}')
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
        获取当前屏幕信息，parsed_content_list 包含所有解析到的元素信息，bbox 是相对值，格式为 (x1, y1, x2, y2)
        该工具禁止作为一个单独步骤
        """
        screen_info = await self._get_screen_info(ctx)
        return ToolResult.success(screen_info.model_dump(include={'screen_elements'}),
                                  'screen_elements 为当前屏幕元素信息')

    @tool(delay=0)
    async def tear_down(self, ctx: RunContext[AgentDeps[WebDevice]], action: StepActionInfo) -> ToolResult:
        """
        任务完成后的清理步骤
        """
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
        await ctx.deps.device.page.goto(action.url, wait_until='networkidle')
        await self._get_screen_info(ctx, parse_element=False)
        return ToolResult.success()

    @tool
    @drawer_box
    async def click(self, ctx: RunContext[AgentDeps[WebDevice]], action: ClickActionInfo) -> ToolResult:
        """
        点击设备屏幕指定的元素, action.element_bbox 不能为空
        """
        x, y = action.get_coordinate(ctx.deps.device.device_size)
        logger.info(f'click coordinate ({x}, {y})')
        await ctx.deps.device.page.mouse.click(x, y)
        return ToolResult.success()

    @tool
    @drawer_box
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
    async def _scroll(
            ctx: RunContext[AgentDeps[WebDevice]],
            action: StepActionInfo,
    ):
        logger.info(f'scroll {action.to}')
        width, height = ctx.deps.device.device_size.width, ctx.deps.device.device_size.height
        if action.to == 'bottom':
            delta_x, delta_y = 0, 0.9 * height
        elif action.to == 'right':
            delta_x, delta_y = 0.9 * width, 0
        elif action.to == 'top':
            delta_x, delta_y = 0, -0.9 * height
        elif action.to == 'left':
            delta_x, delta_y = -0.9 * width, 0
        else:
            raise ValueError(f'Invalid Parameter: to={action.to}')

        logger.info(f'Scroll delta_x={delta_x}, delta_y={delta_y}')
        await ctx.deps.device.page.mouse.wheel(delta_x, delta_y)

    @tool
    async def scroll(self, ctx: RunContext[AgentDeps[WebDevice]], action: SwipeActionInfo) -> ToolResult:
        """
        在设备屏幕中滚动滚动条，仅滚动操作可使用，参数 to 表示滚动方向
        to='left' 向左滚动
        to='right' 向右滚动
        to='top' 向上滚动
        to='bottom' 向下滚动
        """
        await self._scroll(ctx, action)
        return ToolResult.success()

    @tool
    async def swipe(self, ctx: RunContext[AgentDeps[WebDevice]], action: SwipeActionInfo) -> ToolResult:
        """
        在设备屏幕中滑动，仅滑动操作可使用，参数 to 表示滑动方向
        action.to='left' 向左滑动
        action.to='right' 向右滑动
        action.to='top' 向上滑动
        action.to='bottom' 向下滑动
        """
        swipe_to_scroll_mapping = {
            'left': 'right',
            'right': 'left',
            'top': 'bottom',
            'bottom': 'top',
        }
        # noinspection PyTypeChecker
        action.to = swipe_to_scroll_mapping.get(action.to)
        await self._scroll(ctx, action)
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
        获取当前屏幕信息，parsed_content_list 包含所有解析到的元素信息，bbox 是相对值，格式为 (x1, y1, x2, y2)
        该工具禁止作为一个单独步骤
        """
        screen_info = await self._get_screen_info(ctx)
        return ToolResult.success(screen_info.model_dump(include={'screen_elements'}),
                                  'screen_elements 为当前屏幕元素信息')

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

    @tool
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
        在设备屏幕中滑动，参数 to 表示滑动方向
        action.to='left' 向左滑动
        action.to='right' 向右滑动
        action.to='top' 向上滑动
        action.to='bottom' 向下滑动
        """
        logger.info(f'swipe to {action.to}')
        width, height = ctx.deps.device.device_size.width, ctx.deps.device.device_size.height
        if action.to == 'top':
            x1, y1, x2, y2 = 0.5 * width, 0.9 * height, 0.5 * width, 0.1 * height
        elif action.to == 'left':
            x1, y1, x2, y2 = 0.9 * width, 0.5 * height, 0.1 * width, 0.5 * height
        elif action.to == 'bottom':
            x1, y1, x2, y2 = 0.5 * width, 0.1 * height, 0.5 * width, 0.9 * height
        elif action.to == 'right':
            x1, y1, x2, y2 = 0.1 * width, 0.5 * height, 0.9 * width, 0.5 * height
        else:
            raise ValueError(f'Invalid Parameter: to={action.to}')

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
        在设备屏幕中根据给定的坐标进行滑动操作，支持使用多个坐标进行连续滑动
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
