#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Author : aidenmo
# @Email : aidenmo@tencent.com
# @Time : 2025/5/23 17:47
import asyncio
import io
import time
from abc import ABC, abstractmethod
from functools import wraps
from pathlib import Path
from traceback import print_exc
from typing import IO, Optional, cast, TypeAlias, Union, Callable, Awaitable

from httpx import AsyncClient
from loguru import logger
from pydantic_ai import ModelRetry, RunContext, Agent
from playwright.async_api import TimeoutError

from .config import global_settings
from .deps import AgentDeps, ToolParams, ToolResult, StepInfo, LocationToolParams, ClickToolParams, \
    InputToolParams, SwipeToolParams, SwipeFromCoordinateToolParams, OpenUrlToolParams, ScreenInfo, AgentContext, \
    WaitToolParams, AssertContainsParams, MarkFailedParams, AssertNotContainsParams
from .device import AndroidDevice, WebDevice
from .util.adb_tool import AdbDeviceProxy
from .util.js_tool import JSTool
from .util.platform import get_client_url_schema

storage_client = global_settings.storage_client

AgentDepsType: TypeAlias = AgentDeps[
    Union[WebDevice, AndroidDevice],
    Union['WebAgentTool', 'AndroidAgentTool'],
]


class ToolHandler:
    """工具调用处理类，用于处理工具函数的前置和后置操作"""

    def __init__(self, *args, **kwargs):
        self.ctx: Optional[RunContext[AgentDepsType]] = None
        self.step_params: Optional[ToolParams] = None
        self.step_info: Optional[StepInfo] = None

        for arg in [*args, *kwargs.values()]:
            if isinstance(arg, RunContext):
                self.ctx = cast(RunContext[AgentDepsType], arg)
                continue
            if isinstance(arg, ToolParams):
                self.step_params = arg
                continue

    @property
    def context(self) -> AgentContext:
        return self.ctx.deps.context

    @property
    def current_step(self) -> StepInfo:
        return self.ctx.deps.context.current_step

    async def pre_handle(self, func):
        """工具的前置处理"""
        if not all([self.ctx, self.step_params]):
            return
        if self.ctx.deps.context.current_step.parallel_tool_calls:
            raise ModelRetry('only use one tool at a time')

        self.current_step.params = self.step_params.model_dump(
            exclude_defaults=True,
            exclude_none=True
        )
        self.current_step.action = self.current_step.params.pop('action')

        if self.ctx.deps.settings.debug and isinstance(self.step_params, LocationToolParams):
            if isinstance(self.ctx.deps.device, WebDevice):
                await JSTool.add_highlight_element(self.ctx.deps.device.page, self.step_params.element_bbox)

    async def post_handle(self, tool_result: ToolResult):
        """工具的后置处理"""
        if not all([self.ctx, self.step_params]):
            return
        self.current_step.is_success = tool_result.is_success


def limit_recursion(max_depth):
    """用来限制工具内部递归次数"""
    def decorator(func):
        depth = 0

        @wraps(func)
        async def wrapper(*args, **kwargs):
            nonlocal depth
            if depth >= max_depth:
                return ToolResult.failed()
            depth += 1
            try:
                return await func(*args, **kwargs)
            finally:
                depth -= 1

        return wrapper

    return decorator


def tool(f=None, *, after_delay=0, before_delay=0):
    """
    工具函数装饰器，用于标记函数为工具函数，并自动记录步骤信息
    :param f: 被装饰的函数
    :param before_delay: 操作前的等待时间，单位为秒，默认为0
    :param after_delay: 操作后的等待时间，单位为秒，默认为0
    :return: 装饰后的函数
    """

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            tool_handler = ToolHandler(*args, **kwargs)
            await tool_handler.pre_handle(func)

            try:
                # 工具执行
                await asyncio.sleep(before_delay)
                result = await func(*args, **kwargs)
                await asyncio.sleep(after_delay)  # 避免页面渲染慢，不稳定
                await tool_handler.post_handle(result)
                return result
            except Exception as e:
                print_exc()
                logger.error(f"Error occurred in tool '{func.__name__}': {str(e)}")
                raise ModelRetry(f"Error occurred, try call '{func.__name__}' again")

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
            if item.startswith('_') or item in ['tools', 'tear_down']:
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
    async def screenshot(ctx: RunContext[AgentDepsType]) -> io.BytesIO:
        raise NotImplementedError

    async def get_screen(self, ctx: RunContext[AgentDepsType], parse_element: bool = True) -> ScreenInfo:
        image_buffer = await self.screenshot(ctx)
        if parse_element:
            parsed_data = await self._parse_element(image_buffer)
            image_url = parsed_data.get('labeled_image_url') or ''
            parsed_content_list = parsed_data.get('parsed_content_list') or []
            logger.info(f'👁‍🗨 Get screen element：{image_url}')
            if not parsed_content_list:
                raise Exception('Screen parsed error!')
        else:
            image_url = await self._upload_cos(image_buffer, suffix=Path(image_buffer.name).suffix)
            parsed_content_list = []
            logger.info(f'👁‍🗨 Get screen url：{image_url}')

        # 将当前屏幕信息记录到上下文
        ctx.deps.context.current_step.image_url = image_url
        ctx.deps.context.current_step.screen_elements = parsed_content_list
        return ScreenInfo(image_url=image_url, screen_elements=parsed_content_list)

    @abstractmethod
    async def get_screen_info(self, ctx: RunContext[AgentDepsType]) -> ToolResult:
        raise NotImplementedError

    @abstractmethod
    async def open_url(self, ctx: RunContext[AgentDepsType], params: OpenUrlToolParams) -> ToolResult:
        raise NotImplementedError

    @abstractmethod
    async def get_screen_info(self, ctx: RunContext[AgentDepsType]) -> ToolResult[ScreenInfo]:
        raise NotImplementedError

    @abstractmethod
    async def click(self, ctx: RunContext[AgentDepsType], params: ClickToolParams) -> ToolResult:
        raise NotImplementedError

    @abstractmethod
    async def input(self, ctx: RunContext[AgentDepsType], params: InputToolParams) -> ToolResult:
        raise NotImplementedError

    @abstractmethod
    async def swipe(self, ctx: RunContext[AgentDepsType], params: SwipeToolParams) -> ToolResult:
        raise NotImplementedError

    @abstractmethod
    async def tear_down(self, ctx: RunContext[AgentDepsType], params: ToolParams) -> ToolResult:
        raise NotImplementedError

    @tool(after_delay=0)
    async def wait_for_timeout(self, ctx: RunContext[AgentDepsType], params: WaitToolParams) -> ToolResult:
        """
        在任务中等待或停留指定的超时时间（timeout），单位：秒，等待过程中可期望指定的关键字出现
        """
        if params.expect_keywords is None:
            logger.info(f'Wait for timeout {params.timeout}s')
            await asyncio.sleep(params.timeout)
            return ToolResult.success()
        else:
            logger.info(f'Wait up to {params.timeout}s '
                        f'for the keywords {params.expect_keywords} to appear on the screen.')
            st = time.time()
            while time.time() - st < params.timeout:
                result = await self.expect_screen_contains(ctx, params.expect_keywords)
                if result.is_success:
                    return result
                await asyncio.sleep(2)
            else:
                return ToolResult.failed()
    
    async def _parse_screen_keywords(self, ctx: RunContext[AgentDepsType], keywords: list[str]) -> tuple[list, list]:
        screen_info: ScreenInfo = await self.get_screen(ctx, parse_element=True)
        elements_str = str(screen_info.screen_elements)
        contains, not_contains = [], []
        for keyword in keywords:
            if keyword in elements_str:
                contains.append(keyword)
            else:
                not_contains.append(keyword)
        return contains, not_contains

    async def expect_screen_contains(
            self,
            ctx: RunContext[AgentDepsType],
            keywords: list[str]
    ) -> ToolResult:
        contains, not_contains = await self._parse_screen_keywords(ctx, keywords)
        if len(not_contains) > 0:
            logger.warning(f'Screen does not contain expected keywords:"{not_contains}"')
            return ToolResult.failed()
        else:
            return ToolResult.success()

    async def expect_screen_not_contains(
            self,
            ctx: RunContext[AgentDepsType],
            keywords: list[str]
    ) -> ToolResult:
        contains, not_contains = await self._parse_screen_keywords(ctx, keywords)
        if len(contains) > 0:
            logger.warning(f'Screen contains unexpected keywords:"{contains}"')
            return ToolResult.failed()
        else:
            return ToolResult.success()

    @tool(before_delay=2)
    async def assert_screen_contains(
            self,
            ctx: RunContext[AgentDepsType],
            params: AssertContainsParams
    ) -> ToolResult:
        """
        检查屏幕中是否出现或包含指定的多个关键字内容，如果是则 is_success=True, 否则 is_success=False
        """
        return await self.expect_screen_contains(ctx, params.expect_keywords)

    @tool(before_delay=2)
    async def assert_screen_not_contains(
            self,
            ctx: RunContext[AgentDepsType],
            params: AssertNotContainsParams
    ) -> ToolResult:
        """
        检查屏幕中是否不出现或不包含指定的多个关键字内容，如果是则 is_success=True, 否则 is_success=False
        """
        return await self.expect_screen_not_contains(ctx, params.unexpect_keywords)

    @tool
    async def mark_failed(
            self,
            ctx: RunContext[AgentDepsType],
            params: MarkFailedParams
    ) -> ToolResult:
        """
        Mark the task as failed and terminate immediately if an element is not found or is not actionable.
        """
        logger.info(f'Mark task failed, reason: {params.reason}')
        ctx.deps.context.set_step_failed(params.reason)
        return ToolResult.success()


class WebAgentTool(AgentTool):

    @staticmethod
    async def screenshot(ctx: RunContext[AgentDepsType]) -> io.BytesIO:
        screenshot = await ctx.deps.device.page.screenshot(full_page=False, style='#option-el-box {display: none;}')
        image_buffer = io.BytesIO(screenshot)
        image_buffer.name = 'screen.png'
        return image_buffer

    @tool
    async def get_screen_info(self, ctx: RunContext[AgentDepsType]) -> ToolResult[dict]:
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
        return ToolResult.success(screen_info.model_dump(include={'screen_elements'}))

    @tool
    async def tear_down(self, ctx: RunContext[AgentDepsType], params: ToolParams) -> ToolResult:
        """
        任务完成或结束后的清理操作
        """
        await JSTool.remove_highlight_element(ctx.deps.device.page)
        await self.get_screen(ctx, parse_element=False)

        if ctx.deps.device.playwright is not None:
            await ctx.deps.device.context.close()
            await ctx.deps.device.playwright.stop()
        return ToolResult.success()

    @tool(after_delay=2)
    async def open_url(self, ctx: RunContext[AgentDepsType], params: OpenUrlToolParams) -> ToolResult:
        """
        使用设备打开URL
        """
        await ctx.deps.device.page.goto(params.url, wait_until='networkidle')
        return ToolResult.success()

    @tool(after_delay=2)
    async def click(self, ctx: RunContext[AgentDepsType], params: ClickToolParams) -> ToolResult:
        """
        点击设备屏幕指定的元素, element_bbox 不能为空
        """
        x, y = params.get_coordinate(ctx.deps.device.device_size, params.position, params.offset)
        logger.info(f'click coordinate ({x}, {y})')
        await JSTool.add_highlight_position(ctx.deps.device.page, x, y)
        try:
            async with ctx.deps.device.page.context.expect_page(timeout=1000) as new_page_info:
                await ctx.deps.device.page.mouse.click(x, y)
            old_page = ctx.deps.device.page
            ctx.deps.device.page = await new_page_info.value
            await old_page.close()
        except TimeoutError:
            pass
        await JSTool.remove_highlight_position(ctx.deps.device.page)
        return ToolResult.success()

    @tool(after_delay=1)
    async def input(self, ctx: RunContext[AgentDepsType], params: InputToolParams) -> ToolResult:
        """
        在设备指定的元素中输入文本
        """
        x, y = params.get_coordinate(ctx.deps.device.device_size)
        logger.info(f'Input text: ({x}, {y}) -> {params.text}')
        await ctx.deps.device.page.mouse.click(x, y)
        await ctx.deps.device.page.keyboard.type(params.text)
        await ctx.deps.device.page.keyboard.press('Enter')
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
        el_handle = await ctx.deps.device.page.add_style_tag(content="* {user-select: none !important;}")

        await ctx.deps.device.page.mouse.move(x1, y1)
        await ctx.deps.device.page.mouse.down()
        await ctx.deps.device.page.mouse.move(x2, y2, steps=steps)
        await ctx.deps.device.page.mouse.up()
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
        await ctx.deps.device.page.mouse.wheel(delta_x, delta_y)

    @tool(after_delay=1)
    @limit_recursion(max_depth=50)
    async def swipe(self, ctx: RunContext[AgentDepsType], params: SwipeToolParams) -> ToolResult:
        """
        在设备屏幕中滑动或滚动
        """
        logger.info(f'swipe to {params.to}')
        width, height = ctx.deps.device.device_size.width, ctx.deps.device.device_size.height
        has_scroll_bar = await JSTool.has_scrollbar(ctx.deps.device.page, params.to)
        if ctx.deps.device.is_mobile and not has_scroll_bar:
            await self._swipe_by_mouse(ctx, params, width, height)
        else:
            await self._swipe_by_scroll(ctx, params, width, height)
        if params.expect_keywords:
            await asyncio.sleep(1)  # 避免滑动后截图，元素还未稳定出现
            result = await self.expect_screen_contains(ctx, params.expect_keywords)
            if result.is_success:
                return result
            else:
                return await self.swipe(ctx, params)
        return ToolResult.success()

    @tool(after_delay=1)
    async def goback(self, ctx: RunContext[AgentDepsType], params: ToolParams) -> ToolResult:
        """
        操作返回到上一个页面
        """
        logger.info(f'go to previous page')
        await ctx.deps.device.page.go_back()
        return ToolResult.success()


class AndroidAgentTool(AgentTool):

    @staticmethod
    async def screenshot(ctx: RunContext[AgentDepsType]) -> io.BytesIO:
        image_buffer = io.BytesIO()
        screenshot = ctx.deps.device.adb_device.screenshot()
        screenshot.save(image_buffer, format='webp')
        image_buffer.name = 'screen.webp'
        image_buffer.seek(0)
        return image_buffer

    @tool
    async def get_screen_info(self, ctx: RunContext[AgentDepsType]) -> ToolResult:
        """
        获取当前屏幕信息，screen_elements 包含所有解析到的元素信息，bbox 是相对值，格式为 (x1, y1, x2, y2)
        该工具禁止作为一个单独步骤
        """
        screen_info = await self.get_screen(ctx)
        return ToolResult.success(screen_info.model_dump(include={'screen_elements'}))

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

        ctx.deps.device.adb_device.shell(f'am start -a android.intent.action.VIEW -d "{url_schema}"')
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
        ctx.deps.device.adb_device.click(x, y)

        return ToolResult.success()

    @tool(after_delay=0)
    async def input(self, ctx: RunContext[AgentDepsType], params: InputToolParams):
        """
        在设备指定的元素中输入文本
        """
        x, y = params.get_coordinate(ctx.deps.device.device_size)
        logger.info(f'Input text: ({x}, {y}) -> {params.text}')
        ctx.deps.device.adb_device.click(x, y)
        AdbDeviceProxy(ctx.deps.device.adb_device).input_text(params.text)
        ctx.deps.device.adb_device.keyevent('KEYCODE_ENTER')
        return ToolResult.success()

    @tool
    @limit_recursion(max_depth=50)
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
        logger.info(f'Swipe from ({x1}, {y1}) to ({x2}, {y2})')
        ctx.deps.device.adb_device.swipe(x1, y1, x2, y2, duration=2)
        if params.expect_keywords:
            await asyncio.sleep(1)  # 避免滑动后截图，元素还未稳定出现
            result = await self.expect_screen_contains(ctx, params.expect_keywords)
            if result.is_success:
                return result
            else:
                return await self.swipe(ctx, params)

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
            ctx.deps.device.adb_device.swipe(x1, y1, x2, y2, duration=2)
        return ToolResult.success()

    @tool
    async def start_app(
            self,
            ctx: RunContext[AgentDepsType],
            params: ToolParams,
    ):
        """
        在设备中打开或启动指定的应用(APP)
        """
        packages: list[str] = ctx.deps.device.adb_device.list_packages(filter_list=['-e'])
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
            return ToolResult.failed(output='在该设备中未找到对应的应用')
        logger.info(f'Find App package name：{package_name}')
        ctx.deps.device.adb_device.app_start(package_name)
        await asyncio.sleep(2)
        await self.get_screen(ctx, parse_element=False)
        return ToolResult.success()
