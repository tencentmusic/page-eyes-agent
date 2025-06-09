#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Author : aidenmo
# @Email : aidenmo@tencent.com
# @Time : 2025/5/23 17:47
import asyncio
import io
import json
from abc import ABC
from functools import wraps
from traceback import print_exc
from typing import IO, Optional, TypeVar
from urllib.parse import urlencode, quote

import requests
from loguru import logger
from pydantic import BaseModel, computed_field
from pydantic_ai import ModelRetry, RunContext

from .deps import AgentDeps
from .device import AndroidDevice, WebDevice
from .util.adb_tool import AdbDeviceProxy


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


class StepInfo(BaseModel):
    description: Optional[str] = ''
    action: Optional[str] = ''
    labeled_image_url: str = ''
    error: Optional[str] = ''


class ToolResult(BaseModel):
    is_success: bool
    step_info: Optional[StepInfo]

    @classmethod
    def success(cls, step_info: StepInfo = None):
        return cls(is_success=True, step_info=step_info)

    @classmethod
    def failed(cls, step_info: StepInfo = None):
        return cls(is_success=False, step_info=step_info)


T = TypeVar('T')


def tool(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        for arg in [*args, *kwargs.values()]:
            if isinstance(arg, ActionInfo):
                logger.info(arg)
                break
        try:
            await asyncio.sleep(1)  # 避免页面渲染慢，不稳定
            return await func(*args, **kwargs)
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

    # @abstractmethod
    # def screenshot(self, ctx: RunContext[AgentDeps]) -> io.BytesIO:
    #     raise NotImplementedError
    #
    # @abstractmethod
    # def get_device_screen_elements(self, ctx: RunContext[AgentDeps]) -> io.BytesIO:
    #     raise NotImplementedError
    #
    # @abstractmethod
    # def tear_down(self, ctx: RunContext[AgentDeps]) -> dict:
    #     raise NotImplementedError


class WebAgentTool(AgentTool):
    @staticmethod
    async def screenshot(ctx: RunContext[AgentDeps[WebDevice]]) -> io.BytesIO:
        logger.info(f'获取当前屏幕截图')
        screenshot = await ctx.deps.device.page.screenshot(type='jpeg', quality=80, full_page=False)
        image_buffer = io.BytesIO(screenshot)
        image_buffer.name = 'screen.jpeg'
        return image_buffer

    @tool
    async def get_device_screen_elements(self, ctx: RunContext[AgentDeps[WebDevice]]) -> dict:
        """
        获取当前屏幕的元素信息，返回的数据格式为json（bbox 是相对值，格式为 [x1, y1, x2, y2]）
        """
        data = self._parse_element(await self.screenshot(ctx))
        self._page_record(data, ctx)
        logger.info(f'当前屏幕元素信息：{data.get("labeled_image_url")}')
        return data

    @tool
    async def tear_down(self, ctx: RunContext[AgentDeps[WebDevice]]) -> ToolResult:
        """
        任务完成后的清理步骤，返回步骤信息
        """
        logger.info(f'执行任务完成后的清理工作')
        image_buffer = await self.screenshot(ctx)
        url = self._upload_cos(image_buffer)
        logger.info(f'当前屏幕截图：{url}')
        image_buffer.seek(0)
        self._page_record(self._parse_element(image_buffer), ctx)
        await ctx.deps.device.context.close()
        await ctx.deps.device.browser.close()
        await ctx.deps.device.playwright.stop()
        return ToolResult.success(StepInfo(description='任务完成', action='tear_down', labeled_image_url=url))

    @tool
    async def open_url(self, ctx: RunContext[AgentDeps[WebDevice]], action: ActionInfo) -> ToolResult:
        """
        使用设备打开URL {action.url}
        """
        await ctx.deps.device.page.goto(action.url)
        screenshot = await self.screenshot(ctx)
        url = self._upload_cos(screenshot)
        return ToolResult.success(StepInfo(description='打开URL', action='open_url', labeled_image_url=url))

    @tool
    async def click(self, ctx: RunContext[AgentDeps[WebDevice]], action: ActionInfo) -> ToolResult:
        """
        点击设备屏幕指定的元素
        """
        x, y = action.coordinate
        logger.info(f'click coordinate ({x}, {y})')
        await ctx.deps.device.page.mouse.click(x, y)
        return ToolResult.success()

    @tool
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
    async def get_device_screen_elements(self, ctx: RunContext[AgentDeps[AndroidDevice]]) -> dict:
        """
        获取当前屏幕的元素信息，返回的数据格式为json（bbox 是相对值，格式为 [x1, y1, x2, y2]）
        """
        data = self._parse_element(await self.screenshot(ctx))
        self._page_record(data, ctx)
        logger.info(f'当前屏幕元素信息：{data.get("labeled_image_url")}')
        return data

    @tool
    async def tear_down(self, ctx: RunContext[AgentDeps[AndroidDevice]]) -> ToolResult:
        """
        任务完成后的清理步骤，返回步骤信息
        """
        logger.info(f'执行任务完成后的清理工作')
        image_buffer = await self.screenshot(ctx)
        url = self._upload_cos(image_buffer)
        logger.info(f'当前屏幕截图：{url}')
        image_buffer.seek(0)
        self._page_record(self._parse_element(image_buffer), ctx)
        return ToolResult.success(StepInfo(description='任务完成', action='tear_down', labeled_image_url=url))

    @tool
    async def open_url(self, ctx: RunContext[AgentDeps[AndroidDevice]], action: ActionInfo) -> ToolResult:
        """
        使用设备打开URL {action.url}
        """
        params = {'p': json.dumps({'url': action.url})}
        url_schema = f'qqmusic://qq.com/ui/openUrl?{urlencode(params, quote_via=quote)}'
        ctx.deps.device.adb_device.shell(f'am start -a android.intent.action.VIEW -d "{url_schema}"')
        await asyncio.sleep(2)
        screenshot = await self.screenshot(ctx)
        url = self._upload_cos(screenshot)
        return ToolResult.success(StepInfo(description='打开URL', action='open_url', labeled_image_url=url))

    @tool
    async def tap(self, ctx: RunContext[AgentDeps[AndroidDevice]], action: ActionInfo):
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
