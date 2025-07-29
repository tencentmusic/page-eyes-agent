#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Author : aidenmo
# @Email : aidenmo@tencent.com
# @Time : 2025/5/23 17:47
import asyncio
import io
from abc import ABC, abstractmethod
from functools import wraps
from traceback import print_exc
from typing import IO, Optional, TypeVar, cast, Literal, Tuple

import requests
from loguru import logger
from pydantic import BaseModel, computed_field, Field, confloat, conlist
from pydantic_ai import ModelRetry, RunContext

from .config import global_settings
from .deps import AgentDeps
from .device import AndroidDevice, WebDevice
from .util.adb_tool import AdbDeviceProxy
from .util.platform import get_client_url_schema


class ActionInfo(BaseModel):
    step: int = Field(ge=1)
    description: str
    action: str
    element_bbox: Optional[conlist(confloat(ge=0.0, le=1.0), min_length=4, max_length=4)] = []
    device_size: list[int] = Field(min_length=2, max_length=2)
    url: Optional[str] = None
    text: Optional[str] = None
    to: Optional[Literal['left', 'right', 'top', 'bottom']] = None

    @computed_field()
    @property
    def coordinate(self) -> Optional[tuple[int, int]]:
        if not self.element_bbox:
            return None
        x1, y1, x2, y2 = self.element_bbox
        width, height = self.device_size
        return int((x1 + x2) / 2 * width), int((y1 + y2) / 2 * height)


class StepRecord(BaseModel):
    step: int
    description: str = ''
    action: str = ''
    element_bbox: Optional[list[float]] = []
    coordinate: Optional[list[float]] = []
    labeled_image_url: str = ''
    error: str = ''
    page: list = []

    def info(self):
        return type(self)(**self.dict(exclude={'page'}))


class ToolOutput(BaseModel):
    labeled_image_url: Optional[str] = ''
    parsed_content_list: Optional[list] = []
    error: Optional[str] = ''


class ToolResult(BaseModel):
    is_success: bool
    output: Optional[ToolOutput]

    @classmethod
    def success(cls, output: ToolOutput = None):
        return cls(is_success=True, output=output)

    @classmethod
    def failed(cls, output: ToolOutput = None):
        return cls(is_success=False, output=output)


T = TypeVar('T')


def record_step(*args, **kwargs):
    ctx: Optional[RunContext[AgentDeps]] = None
    action_info: Optional[ActionInfo] = None
    tool_result: Optional[ToolResult] = None
    for arg in [*args, *kwargs.values()]:
        if isinstance(arg, RunContext):
            ctx = cast(RunContext[AgentDeps], arg)
            continue
        if isinstance(arg, ActionInfo):
            action_info = arg
            continue
        if isinstance(arg, ToolResult):
            tool_result = arg
            continue
    if ctx and action_info and tool_result:
        record = ctx.deps.context.steps.setdefault(action_info.step, StepRecord(step=action_info.step))
        record.description = action_info.description or record.description
        record.action = action_info.action or record.action
        record.element_bbox = action_info.element_bbox or record.element_bbox
        record.labeled_image_url = (tool_result.output and tool_result.output.labeled_image_url
                                    ) or record.labeled_image_url
        record.page = (tool_result.output and tool_result.output.parsed_content_list
                       ) or record.page
        logger.debug(record.info())


def tool(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        for arg in [*args, *kwargs.values()]:
            if isinstance(arg, ActionInfo):
                logger.info(arg)
                break
        try:
            await asyncio.sleep(1)  # 避免页面渲染慢，不稳定
            result = await func(*args, **kwargs)
            record_step(result, *args, **kwargs)  # 记录步骤信息
            logger.debug(result)
            return result
        except Exception as e:
            print_exc()
            logger.error(f"Error occurred in tool '{func.__name__}': {str(e)}")
            raise ModelRetry(f"Error occurred in tool '{func.__name__}': {str(e)}")

    wrapper.is_tool = True
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

    def _upload_cos(self, file: IO[bytes]) -> str:
        response = requests.post(self.COS_BASE_URL, files={'file': file})
        return response.json().get('url')

    def _parse_element(self, file: Optional[IO[bytes]] = None, image_url: Optional[str] = None):
        url = f'{self.OMNI_BASE_URL}/omni/parse/'
        if not file and not image_url:
            raise ValueError('请提供file或image_url')
        response = requests.post(url, files={'file': file}, data={'image_url': image_url})
        response.raise_for_status()
        return response.json()

    @staticmethod
    def _page_record(data: dict, ctx: RunContext[AgentDeps]):
        """通过上下文记录页面截图和元素解析信息"""
        if data:
            parsed_content_list: list[dict] = data.get('parsed_content_list', [])
            if parsed_content_list and isinstance(ctx.deps.device, (AndroidDevice, WebDevice)):
                width, height = ctx.deps.device.device_size.width, ctx.deps.device.device_size.height
                for item in parsed_content_list:
                    x1, y1, x2, y2 = item['bbox']
                    item['bbox_coordinate'] = [int(width * x1), int(height * y1), int(width * x2), int(height * y2)]

            ctx.deps.context.page.update({data.get("labeled_image_url", ''): parsed_content_list})

        return ctx.deps.context.page

    @staticmethod
    @abstractmethod
    async def screenshot(ctx: RunContext[AgentDeps]) -> io.BytesIO:
        raise NotImplementedError

    @abstractmethod
    async def get_device_screen_elements(self, ctx: RunContext[AgentDeps]) -> ToolResult:
        raise NotImplementedError

    @abstractmethod
    async def tear_down(self, ctx: RunContext[AgentDeps]) -> ToolResult:
        raise NotImplementedError


def drawer_box(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        ctx: Optional[RunContext[AgentDeps[WebDevice]]] = None
        bbox: Optional[list[float]] = None
        for arg in [*args, *kwargs.values()]:
            if isinstance(arg, RunContext):
                ctx = cast(RunContext[AgentDeps[WebDevice]], arg)
                continue
            if isinstance(arg, ActionInfo):
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


class WebAgentTool(AgentTool):

    @staticmethod
    async def screenshot(ctx: RunContext[AgentDeps[WebDevice]]) -> io.BytesIO:
        screenshot = await ctx.deps.device.page.screenshot(full_page=False, style='#option-el-box {display: none;}')
        image_buffer = io.BytesIO(screenshot)
        image_buffer.name = 'screen.png'
        return image_buffer

    @tool
    async def get_device_screen_elements(self, ctx: RunContext[AgentDeps[WebDevice]], action: ActionInfo) -> ToolResult:
        """
        获取当前屏幕的元素信息，parsed_content_list 包含所有解析到的元素，bbox 是相对值，格式为 (x1, y1, x2, y2)
        该工具禁止作为一个单独步骤，step 序号应与下一步的操作保持一致
        """
        data = self._parse_element(await self.screenshot(ctx))
        labeled_image_url = data.get('labeled_image_url') or ''
        parsed_content_list = data.get('parsed_content_list') or []
        self._page_record(data, ctx)
        return ToolResult.success(ToolOutput(
            labeled_image_url=labeled_image_url,
            parsed_content_list=parsed_content_list
        ))

    @tool
    async def tear_down(self, ctx: RunContext[AgentDeps[WebDevice]], action: ActionInfo) -> ToolResult:
        """
        任务完成后的清理步骤，返回步骤信息
        """
        image_buffer = await self.screenshot(ctx)
        url = self._upload_cos(image_buffer)
        image_buffer.seek(0)
        self._page_record(self._parse_element(image_buffer), ctx)

        if ctx.deps.device.playwright is not None:
            await ctx.deps.device.context.close()
            await ctx.deps.device.browser.close()
            await ctx.deps.device.playwright.stop()
        return ToolResult.success(ToolOutput(labeled_image_url=url))

    @tool
    async def open_url(self, ctx: RunContext[AgentDeps[WebDevice]], action: ActionInfo) -> ToolResult:
        """
        使用设备打开URL {action.url}
        """
        await ctx.deps.device.page.goto(action.url)
        screenshot = await self.screenshot(ctx)
        url = self._upload_cos(screenshot)
        return ToolResult.success(ToolOutput(labeled_image_url=url))

    @tool
    @drawer_box
    async def click(self, ctx: RunContext[AgentDeps[WebDevice]], action: ActionInfo) -> ToolResult:
        """
        点击设备屏幕指定的元素, action.element_bbox 不能为空
        """
        x, y = action.coordinate
        logger.info(f'click coordinate ({x}, {y})')
        await ctx.deps.device.page.mouse.click(x, y)
        return ToolResult.success()

    @tool
    @drawer_box
    async def input(self, ctx: RunContext[AgentDeps[WebDevice]], action: ActionInfo) -> ToolResult:
        """
        在设备指定的元素中输入文本 {action.text}
        """
        x, y = action.coordinate
        logger.info(f'Input text: ({x}, {y}) -> {action.text}')
        await ctx.deps.device.page.mouse.click(x, y)
        await ctx.deps.device.page.keyboard.type(action.text)
        await ctx.deps.device.page.keyboard.press('Enter')
        return ToolResult.success()

    @staticmethod
    async def _scroll(
            ctx: RunContext[AgentDeps[WebDevice]],
            action: ActionInfo,
    ):
        logger.info(f'scroll {action.to}')
        width, height = action.device_size
        if action.to == 'bottom':
            delta_x, delta_y = 0, 0.5 * height
        elif action.to == 'right':
            delta_x, delta_y = 0.5 * width, 0
        elif action.to == 'top':
            delta_x, delta_y = 0, -0.5 * height
        elif action.to == 'left':
            delta_x, delta_y = -0.5 * width, 0
        else:
            raise ValueError(f'Invalid Parameter: to={action.to}')

        logger.info(f'Scroll delta_x={delta_x}, delta_y={delta_y}')
        await ctx.deps.device.page.mouse.wheel(delta_x, delta_y)

    @tool
    async def scroll(
            self,
            ctx: RunContext[AgentDeps[WebDevice]],
            action: ActionInfo,
    ):
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
    async def swipe(
            self,
            ctx: RunContext[AgentDeps[WebDevice]],
            action: ActionInfo,
    ):
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
        return await self._scroll(ctx, action)


class AndroidAgentTool(AgentTool):

    @staticmethod
    async def screenshot(ctx: RunContext[AgentDeps[AndroidDevice]]) -> io.BytesIO:
        logger.info(f'获取当前屏幕截图')
        image_buffer = io.BytesIO()
        screenshot = ctx.deps.device.adb_device.screenshot()
        screenshot.save(image_buffer, format='webp')
        image_buffer.name = 'screen.webp'
        image_buffer.seek(0)
        return image_buffer

    @tool
    async def get_device_screen_elements(self, ctx: RunContext[AgentDeps[AndroidDevice]],
                                         action: ActionInfo) -> ToolResult:
        """
        获取当前屏幕的元素信息，parsed_content_list 包含所有解析到的元素（bbox 是相对值，格式为 [x1, y1, x2, y2]）
        该工具禁止作为一个单独步骤，step 序号应与下一步的操作保持一致
        """
        data = self._parse_element(await self.screenshot(ctx))
        labeled_image_url = data.get('labeled_image_url') or ''
        parsed_content_list = data.get('parsed_content_list') or []
        self._page_record(data, ctx)
        logger.info(f'step={action.step} 当前屏幕元素信息：{labeled_image_url}')
        return ToolResult.success(ToolOutput(
            labeled_image_url=labeled_image_url,
            parsed_content_list=parsed_content_list
        ))

    @tool
    async def tear_down(self, ctx: RunContext[AgentDeps[AndroidDevice]], action: ActionInfo) -> ToolResult:
        """
        任务完成后的清理步骤，返回步骤信息
        """
        logger.info(f'执行任务完成后的清理工作')
        image_buffer = await self.screenshot(ctx)
        url = self._upload_cos(image_buffer)
        logger.info(f'当前屏幕截图：{url}')
        image_buffer.seek(0)
        self._page_record(self._parse_element(image_buffer), ctx)
        return ToolResult.success(ToolOutput(labeled_image_url=url))

    @tool
    async def open_url(self, ctx: RunContext[AgentDeps[AndroidDevice]], action: ActionInfo) -> ToolResult:
        """
        使用设备打开URL {action.url}
        """
        platform = ctx.deps.device.platform
        url_schema = get_client_url_schema(action.url, platform)
        logger.info(f'open schema: {url_schema}')

        ctx.deps.device.adb_device.shell(f'am start -a android.intent.action.VIEW -d "{url_schema}"')
        await asyncio.sleep(2)
        screenshot = await self.screenshot(ctx)
        url = self._upload_cos(screenshot)
        return ToolResult.success(ToolOutput(labeled_image_url=url))

    @tool
    async def tap(self, ctx: RunContext[AgentDeps[AndroidDevice]], action: ActionInfo) -> ToolResult:
        """
        点击设备屏幕指定的元素
        """
        x, y = action.coordinate
        logger.info(f'Tap coordinate ({x}, {y})')
        ctx.deps.device.adb_device.click(x, y)

        return ToolResult.success()

    @tool
    async def input(self, ctx: RunContext[AgentDeps[AndroidDevice]], action: ActionInfo):
        """
        在设备指定的元素中输入文本
        """
        x, y = action.coordinate
        logger.info(f'Input text: ({x}, {y}) -> {action.text}')
        ctx.deps.device.adb_device.click(x, y)
        AdbDeviceProxy(ctx.deps.device.adb_device).input_text(action.text)
        ctx.deps.device.adb_device.keyevent('KEYCODE_ENTER')
        return ToolResult.success()

    @tool
    async def swipe(
            self,
            ctx: RunContext[AgentDeps[AndroidDevice]],
            action: ActionInfo,
    ):
        """
        在设备屏幕中滑动，参数 to 表示滑动方向
        action.to='left' 向左滑动
        action.to='right' 向右滑动
        action.to='top' 向上滑动
        action.to='bottom' 向下滑动
        """
        logger.info(f'swipe to {action.to}')
        width, height = action.device_size
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

        logger.info(f'Swipe from ({x1}, {y1}) to ({x2}, {y2})')
        ctx.deps.device.adb_device.swipe(x1, y1, x2, y2, duration=2)
        return ToolResult.success()

    @tool
    async def swipe_from_coordinate(
            self,
            ctx: RunContext[AgentDeps[AndroidDevice]],
            action: ActionInfo,
            start_coordinate: Tuple[int, int],
            end_coordinate: Tuple[int, int]
    ):
        """
        在设备屏幕中根据指定的起始坐标和结束坐标滑动
        start_coordinate 为起始坐标，格式为 (x1, y1)
        end_coordinate 为结束坐标，格式为 (x2, y2)
        """
        x1, y1 = start_coordinate
        x2, y2 = end_coordinate
        logger.info(f'Swipe from ({x1}, {y1}) to ({x2}, {y2})')
        ctx.deps.device.adb_device.swipe(x1, y1, x2, y2, duration=2)
        return ToolResult.success()

