#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Author : aidenmo
# @Email : aidenmo@tencent.com
# @Time : 2026/2/11 15:24
import asyncio
import io
import time
import traceback
from abc import ABC, abstractmethod
from functools import wraps
from pathlib import Path
from typing import IO, Optional, cast, TypeAlias, Union

from httpx import AsyncClient
from loguru import logger
# noinspection PyProtectedMember
from loguru._logger import context as logger_context
from pydantic import TypeAdapter
from pydantic_ai import ModelRetry, RunContext, ToolReturn, ImageUrl, Tool

from ..config import default_settings
from ..deps import AgentDeps, ToolParams, ToolResult, StepInfo, LocationToolParams, ClickToolParams, \
    InputToolParams, SwipeToolParams, OpenUrlToolParams, ScreenInfo, AgentContext, \
    WaitForKeywordsToolParams, AssertContainsParams, MarkFailedParams, AssertNotContainsParams, ToolResultWithOutput, \
    WaitToolParams, LLMLocationToolParams, SwipeForKeywordsToolParams
from ..device import AndroidDevice, WebDevice, HarmonyDevice, IOSDevice
from ..util.js_tool import JSTool
from ..util.storage import Base64Strategy

storage_client = default_settings.storage_client

AgentDepsType: TypeAlias = AgentDeps[
    Union[WebDevice, AndroidDevice, HarmonyDevice, IOSDevice],
    'AgentTool',
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

        if self.ctx.deps.settings.debug and isinstance(self.step_params, LLMLocationToolParams):
            if isinstance(self.ctx.deps.device, WebDevice):
                bbox = self.ctx.deps.context.current_step.screen_elements[self.step_params.element_id].get('bbox')
                await JSTool.add_highlight_element(self.ctx.deps.device.target, bbox)

    async def post_handle(self, tool_result: ToolResult):
        """工具的后置处理"""
        if not all([self.ctx, self.step_params]):
            return
        self.current_step.is_success = tool_result.is_success


def tool(f=None, *, after_delay=0, before_delay=0, llm=True, vlm=True):
    """
    工具函数装饰器，用于标记函数为工具函数，并自动记录步骤信息
    :param f: 被装饰的函数
    :param before_delay: 操作前的等待时间，单位为秒，默认为0
    :param after_delay: 操作后的等待时间，单位为秒，默认为0
    :param llm: 是否支持LLM调用，默认为True
    :param vlm: 是否支持VLM调用，默认为True
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
                logger.error(f"Error occurred in tool '{func.__name__}': {str(e)}")
                format_exc = traceback.format_exc()
                for line in format_exc.splitlines():
                    logger.error(line)

                raise ModelRetry(f"Error occurred, try call '{func.__name__}' again")

        wrapper.is_tool = True
        wrapper.llm = llm
        wrapper.vlm = vlm
        return wrapper

    if f is not None:
        return decorator(f)
    return decorator


class AgentTool(ABC):
    """VLM 模型使用的工具可以以 _vl 结尾, 如 click_vl -> click"""
    OMNI_BASE_URL = default_settings.omni_parser.base_url
    OMNI_KEY = default_settings.omni_parser.key

    @property
    def tools(self) -> list:
        result = []
        for item in dir(self):
            if item.startswith('_') or item in ['tools', 'tear_down']:
                continue
            value = getattr(self, item)
            if callable(value) and hasattr(value, 'is_tool'):
                if default_settings.model_type == 'llm' and not getattr(value, 'llm'):
                    continue
                if default_settings.model_type == 'vlm' and not getattr(value, 'vlm'):
                    continue
                # 移除 _vl 后缀，让工具名称保持一致
                result.append(Tool(value, name=value.__name__.removesuffix('_vl')))

        return result

    @staticmethod
    async def _upload_cos(file: IO[bytes], prefix='page-eyes-agent/', suffix='.png') -> str:
        return await storage_client.async_upload_file(file, prefix=prefix, suffix=suffix)

    async def _parse_element(self, file: Optional[IO[bytes]] = None, image_url: Optional[str] = None):
        url = f'{self.OMNI_BASE_URL}/omni/parse/'
        if not file and not image_url:
            raise ValueError('请提供file或image_url')
        trace_id = logger_context.get().get('trace_id')
        headers = {'X-Trace-Id': trace_id} if trace_id else None
        async with AsyncClient(timeout=300, headers=headers) as client:
            response = await client.post(url, files={'file': file}, data={'key': self.OMNI_KEY})
            response.raise_for_status()
            return response.json()

    async def get_screen(self, ctx: RunContext[AgentDepsType], parse_element: bool = True) -> ScreenInfo:
        image_buffer = await self.screenshot(ctx)
        if parse_element:
            parsed_data = await self._parse_element(image_buffer)
            image_url = parsed_data.get('labeled_image_url') or ''
            parsed_content_list = parsed_data.get('parsed_content_list') or []
            logger.info(f'👁‍🗨 Get screen element：{image_url}')
            if not parsed_content_list:
                raise Exception(f'Screen parsed error! {parsed_data}')
        else:
            image_url = await self._upload_cos(image_buffer, suffix=Path(image_buffer.name).suffix)
            parsed_content_list = []
            logger.info(f'👁‍🗨 Get screen url：{image_url[:200] + (image_url[200:] and "...")}')

        # 将当前屏幕信息记录到上下文
        ctx.deps.context.current_step.image_url = image_url
        ctx.deps.context.current_step.screen_elements = parsed_content_list
        # 仅保留必要的字段给LLM
        parsed_elements = TypeAdapter(list[dict]).dump_python(
            parsed_content_list,
            exclude={'__all__': {'type', 'interactivity', 'source'}}
        )
        return ScreenInfo(image_url=image_url, screen_elements=parsed_elements)

    async def get_screen_vl(self, ctx: RunContext[AgentDepsType]) -> ScreenInfo:
        """获取当前屏幕信息，仅用于VLm模型"""
        image_buffer = await self.screenshot(ctx)
        image_url = Base64Strategy().upload_file(image_buffer, suffix='.png')
        parsed_content_list = []
        logger.info(f'👁‍🗨 Get screen url：{image_url[:200] + (image_url[200:] and "...")}')

        # 将当前屏幕信息记录到上下文
        ctx.deps.context.current_step.image_url = image_url
        ctx.deps.context.current_step.screen_elements = parsed_content_list

        return ScreenInfo(image_url=image_url, screen_elements=parsed_content_list)

    @tool(vlm=False)
    async def get_screen_info(self, ctx: RunContext[AgentDepsType]) -> ToolResultWithOutput[dict]:
        """
        获取当前屏幕信息，每个元素都有唯一的 ID，单个元素包含以下字段：
        id: 元素ID
        content: 元素描述信息
        left_elem_ids: 该元素左侧的元素列表
        right_elem_ids: 该元素右侧的元素列表
        top_elem_ids: 该元素上方的元素列表
        bottom_elem_ids: 该元素下方的元素列表

        注意：该工具禁止作为一个单独步骤执行
        """
        screen_info = await self.get_screen(ctx)
        # 仅保留必要的字段给 LLM
        parsed_elements = TypeAdapter(list[dict]).dump_python(
            screen_info.screen_elements,
            include={'__all__': {'id', 'content', 'left_elem_ids', 'top_elem_ids', 'right_elem_ids', 'bottom_elem_ids'}}
        )
        return ToolResultWithOutput.success(parsed_elements)

    @tool(llm=False)
    async def get_screen_info_vl(self, ctx: RunContext[AgentDepsType]) -> ToolReturn:
        """
        获取当前屏幕截图
        """
        screen_info = await self.get_screen_vl(ctx)
        return ToolReturn(
            return_value='当前屏幕截图：',
            content=[ImageUrl(url=screen_info.image_url)]
        )

    @tool(vlm=False)
    async def wait(self, ctx: RunContext[AgentDepsType], params: WaitForKeywordsToolParams) -> ToolResult:
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

    @tool(llm=False)
    async def wait_vl(self, ctx: RunContext[AgentDepsType], params: WaitToolParams) -> ToolResult:
        """
        在任务中等待或停留指定的超时时间（timeout），单位：秒
        """
        await asyncio.sleep(params.timeout)
        return ToolResult.success()

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

    @tool(before_delay=2, vlm=False)
    async def assert_screen_contains(
            self,
            ctx: RunContext[AgentDepsType],
            params: AssertContainsParams
    ) -> ToolResult:
        """
        检查屏幕中是否出现或包含指定的多个关键字内容，如果是则 is_success=True, 否则 is_success=False
        """
        return await self.expect_screen_contains(ctx, params.expect_keywords)

    @tool(before_delay=2, vlm=False)
    async def assert_screen_not_contains(
            self,
            ctx: RunContext[AgentDepsType],
            params: AssertNotContainsParams
    ) -> ToolResult:
        """
        检查屏幕中是否不出现或不包含指定的多个关键字内容，如果是则 is_success=True, 否则 is_success=False
        """
        return await self.expect_screen_not_contains(ctx, params.unexpect_keywords)

    @tool(vlm=False)
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

    @tool(llm=False, vlm=False)
    async def set_task_failed(
            self,
            ctx: RunContext[AgentDepsType],
            params: MarkFailedParams
    ) -> ToolResult:
        """
        仅任务失败或断言失败时调用，否则不允许调用
        """
        logger.info(f'Mark task failed, reason: {params.reason}')
        ctx.deps.context.set_step_failed(params.reason)
        return ToolResult.success()

    @tool(vlm=False)
    async def swipe(self, ctx: RunContext[AgentDepsType], params: SwipeForKeywordsToolParams) -> ToolResult:
        """
        在设备屏幕中滑动或滚动
        """
        return await self._swipe_for_keywords(ctx, params)

    @tool(llm=False)
    async def swipe_vl(self, ctx: RunContext[AgentDepsType], params: SwipeToolParams) -> ToolResult:
        """
        在设备屏幕中滑动或滚动
        """
        return await self._swipe_for_keywords(ctx, SwipeForKeywordsToolParams(**params.model_dump()))

    @staticmethod
    @abstractmethod
    async def screenshot(ctx: RunContext[AgentDepsType]) -> io.BytesIO:
        raise NotImplementedError

    @abstractmethod
    async def open_url(self, ctx: RunContext[AgentDepsType], params: OpenUrlToolParams) -> ToolResult:
        raise NotImplementedError

    @abstractmethod
    async def click(self, ctx: RunContext[AgentDepsType], params: ClickToolParams) -> ToolResult:
        raise NotImplementedError

    @abstractmethod
    async def input(self, ctx: RunContext[AgentDepsType], params: InputToolParams) -> ToolResult:
        raise NotImplementedError

    @abstractmethod
    async def _swipe_for_keywords(self, ctx: RunContext[AgentDepsType], params: SwipeForKeywordsToolParams) -> ToolResult:
        raise NotImplementedError

    @abstractmethod
    async def tear_down(self, ctx: RunContext[AgentDepsType], params: ToolParams) -> ToolResult:
        raise NotImplementedError

    # TODO: 所有端实现返回上一页
    # @abstractmethod
    # async def go_back(self, ctx: RunContext[AgentDepsType], params: ToolParams) -> ToolResult:
    #     raise NotImplementedError
