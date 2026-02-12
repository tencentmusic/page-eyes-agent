#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Author : aidenmo
# @Email : aidenmo@tencent.com
# @Time : 2026/2/11 15:52
import asyncio
# noinspection PyProtectedMember
import io
from typing import TypeAlias

from loguru import logger
# noinspection PyProtectedMember
from pydantic_ai import RunContext, Agent

from .base import AgentTool, tool
from ..deps import ToolParams, ToolResult, ClickToolParams, \
    InputToolParams, SwipeToolParams, SwipeFromCoordinateToolParams, OpenUrlToolParams, ToolResultWithOutput, AgentDeps
from ..device import HarmonyDevice
from ..util.adb_tool import AdbDeviceProxy
from ..util.platform import get_client_url_schema
from .android import AndroidAgentTool

AgentDepsType: TypeAlias = AgentDeps[HarmonyDevice, AgentTool]


class HarmonyAgentTool(AndroidAgentTool):

    @staticmethod
    def _start_url(ctx: RunContext[AgentDepsType], url: str):
        return ctx.deps.device.target.shell(['aa', 'start', '-A', 'ohos.want.action.viewData', '-U', url])

    @tool(after_delay=0)
    async def input(self, ctx: RunContext[AgentDepsType], params: InputToolParams):
        """
        在设备指定的元素中输入文本
        """
        x, y = params.get_coordinate(ctx.deps.device.device_size)
        logger.info(f'Input text: ({x}, {y}) -> {params.text}')
        ctx.deps.device.target.uitest.input_text(params.text, x=x, y=y)
        if params.send_enter:
            enter_event = ctx.deps.device.target.uitest.keyevent.ENTER
            ctx.deps.device.target.uitest.inject_keyevent(enter_event)
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
        bundles, _ = ctx.deps.device.target.bm.dump_all_installed_bundles()
        sub_agent = Agent(
            ctx.model,
            output_type=str,
            system_prompt='你是一个移动端应用助手，负责根据用户输入的指令从提供的应用包名列表找出用户指令对应的包名，并仅返回包名，如果都不匹配则返回空字符串'
        )
        prompt = (f'用户指令：{params.instruction}\n'
                  f'应用包名列表：{bundles}')
        result = await sub_agent.run(prompt, output_type=str)
        bundle_name = result.output
        if not bundle_name:
            return ToolResultWithOutput.failed(output='在该设备中未找到对应的应用')
        logger.info(f'Find App bundle name：{bundle_name}')
        main_ability = ctx.deps.device.target.get_main_ability(bundle_name)
        out, _ = ctx.deps.device.target.aa.start(bundle_name, ability=main_ability)
        if 'successfully' not in out:
            return ToolResultWithOutput.failed(output=f'启动应用失败，原因：{out}')
        await asyncio.sleep(2)
        await self.get_screen(ctx, parse_element=False)
        return ToolResult.success()
