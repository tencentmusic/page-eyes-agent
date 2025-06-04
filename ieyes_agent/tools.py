#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Author : aidenmo
# @Email : aidenmo@tencent.com
# @Time : 2025/5/23 17:47
import io
import time
from abc import ABC
from functools import wraps
from traceback import print_exc
from typing import IO, Optional

import requests
from loguru import logger
from pydantic import BaseModel, computed_field
from pydantic_ai import ModelRetry, RunContext

from .deps import AgentDeps
from .util.adb_tool import AdbDeviceProxy


def tool(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            time.sleep(1)  # 避免页面渲染慢，不稳定
            return func(*args, **kwargs)
        except Exception as e:
            print_exc()
            logger.error(f"Error occurred in tool '{func.__name__}': {str(e)}")
            raise ModelRetry(f"Error occurred in tool '{func.__name__}': {str(e)}")

    wrapper.is_tool = True
    return wrapper


class ActionInfo(BaseModel):
    element_bbox: list[float, float, float, float]
    device_size: list[int, int]
    step: int
    description: str
    action: str

    @computed_field()
    @property
    def coordinate(self) -> tuple[int, int]:
        x1, y1, x2, y2 = self.element_bbox
        width, height = self.device_size
        return int((x1 + x2) / 2 * width), int((y1 + y2) / 2 * height)


class Result:
    success = 'success'
    failed = 'failed'


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


class WebAgentTool(AgentTool):
    pass


class AndroidAgentTool(AgentTool):
    @tool
    def get_device_screen_elements(self, ctx: RunContext[AgentDeps]) -> str:
        """
        获取当前屏幕的元素信息，返回的数据格式为json（bbox 是相对值，格式为 [x1, y1, x2, y2]）
        """
        logger.info(f'获取当前屏幕截图')
        image_buffer = io.BytesIO()
        screenshot = ctx.deps.device.screenshot()
        screenshot.save(image_buffer, format='webp')
        image_buffer.name = 'screen.webp'
        image_buffer.seek(0)
        data = self._parse_element(image_buffer)
        self._page_record(data, ctx)
        logger.info(f'当前屏幕元素信息：{data.get("labeled_image_url")}')
        return data

    @tool
    def tear_down(self, ctx: RunContext[AgentDeps]) -> dict:
        """
        任务完成后的清理步骤，返回步骤信息
        """
        logger.info(f'执行任务完成后的清理工作')
        image_buffer = io.BytesIO()
        screenshot = ctx.deps.device.screenshot()
        screenshot.save(image_buffer, format='webp')
        image_buffer.name = 'screen.webp'
        image_buffer.seek(0)
        url = self._upload_cos(image_buffer)
        logger.info(f'当前屏幕截图：{url}')
        image_buffer.seek(0)
        self._page_record(self._parse_element(image_buffer), ctx)
        return {
            'status': Result.success,
            'step_info': {
                'message': '任务完成',
                'description': '任务完成',
                'action': 'tear_down',
                'element_id': -1,
                'element_bbox': [0.0, 0.0, 0.0, 0.0],
                'labeled_image_url': url,
                'error': ''
            }
        }

    @tool
    def tap(self, ctx: RunContext[AgentDeps], action: ActionInfo):
        """
        点击设备屏幕指定的元素
        """
        logger.info(action)
        x, y = action.coordinate
        logger.info(f'Tap coordinate ({x}, {y})')
        ctx.deps.device.click(x, y)

        return Result.success

    @tool
    def input(self, ctx: RunContext[AgentDeps], action: ActionInfo, text: str):
        """
        在设备指定的元素中输入文本
        """
        logger.info(action)
        x, y = action.coordinate
        logger.info(f'Input text: ({x}, {y}) -> {text}')
        ctx.deps.device.click(x, y)
        AdbDeviceProxy(ctx.deps.device).input_text(text)
        ctx.deps.device.keyevent('KEYCODE_ENTER')
        return Result.success
