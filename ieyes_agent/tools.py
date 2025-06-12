#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Author : aidenmo
# @Email : aidenmo@tencent.com
# @Time : 2025/5/23 17:47
import asyncio
import io
import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from functools import wraps
from traceback import print_exc
from typing import IO, Optional, TypeVar
from urllib.parse import urlencode, quote
from contextlib import asynccontextmanager

import requests
from loguru import logger
from pydantic import BaseModel, computed_field
from pydantic_ai import ModelRetry, RunContext

from .deps import AgentDeps
from .device import AndroidDevice, WebDevice
from .util.adb_tool import AdbDeviceProxy
from .util.platform import Platform, get_client_url_schema


class ElementInfo(BaseModel):
    element_bbox: list[float, float, float, float]
    device_size: list[int, int]


class ActionInfo(BaseModel):
    step: int
    description: str
    action: str
    element_bbox: Optional[list[float, float, float, float]] = []
    device_size: list[int, int]
    url: Optional[str] = None
    text: Optional[str] = None

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
    element_bbox: list[float] = []
    device_size: list[int, int] = [0, 0]
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
            ctx = arg
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
        record.device_size = action_info.device_size or record.device_size
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
    OMNI_BASE_URL = 'http://21.6.91.201:8000'
    COS_BASE_URL = 'http://uniqc.woa.com/api/tools/file-upload/'

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
            ctx.deps.context.page.update({data.get("labeled_image_url", ''): data.get('parsed_content_list', [])})
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
                ctx = arg
                continue
            if isinstance(arg, ActionInfo):
                bbox = arg.element_bbox
                continue
        if ctx and bbox:
            style = """
            @keyframes fadeBorder {
                      from { border-color: rgba(255,0,0); }
                      to { border-color: transparent; }
                    }
            """
            await ctx.deps.device.page.evaluate("""
            ([bbox, style]) => {
                const [x1, y1, x2, y2] = bbox
                let box = document.querySelector("#option-box")
                let boxStyle = document.querySelector("#box-style")
                if (!boxStyle) {
                    boxStyle = document.createElement("style")
                    boxStyle.id = "box-style"
                    boxStyle.innerHTML = style
                    document.head.appendChild(boxStyle)
                }
                if (!box) {
                    box = document.createElement("div");
                    box.id = "option-box";
                    box.style.position = "absolute";
                    box.style.zIndex = "1000";
                    box.style.border = "2px solid rgba(255,0,0)";
                    box.style.pointerEvents = "none"
                    //box.style.animation = 'fadeBorder 4s forwards';
                    document.body.appendChild(box);
                }
                box.style.top = y1 * 100 + "%"
                box.style.left = x1 * 100 + "%"
                box.style.width = (x2 - x1) * 100 + "%"
                box.style.height = (y2 - y1) * 100 + "%"
                return box
            }
            """, [bbox, style])
        return await func(*args, **kwargs)

    return wrapper


@asynccontextmanager
async def clear_box(ctx: RunContext[AgentDeps[WebDevice]]):
    await ctx.deps.device.page.evaluate("""() => {
        const box = document.querySelector("#option-box")
        if (box) {
            box.style.display = "none"
        }
    }""")
    yield
    await ctx.deps.device.page.evaluate("""() => {
        const box = document.querySelector("#option-box")
        if (box) {
            box.style.display = "unset"
        }
    }""")


class WebAgentTool(AgentTool):

    @staticmethod
    async def screenshot(ctx: RunContext[AgentDeps[WebDevice]]) -> io.BytesIO:
        async with clear_box(ctx):
            screenshot = await ctx.deps.device.page.screenshot(type='jpeg', quality=80, full_page=False)
            image_buffer = io.BytesIO(screenshot)
            image_buffer.name = 'screen.jpeg'
            return image_buffer

    @tool
    async def get_device_screen_elements(self, ctx: RunContext[AgentDeps[WebDevice]], action: ActionInfo) -> ToolResult:
        """
        获取当前屏幕的元素信息，parsed_content_list 包含所有解析到的元素（bbox 是相对值，格式为 [x1, y1, x2, y2]）
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
        点击设备屏幕指定的元素
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
