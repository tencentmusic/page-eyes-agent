#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Author : aidenmo
# @Email : aidenmo@tencent.com
# @Time : 2025/5/23 15:31
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional, Union, Literal, TypeAlias, cast

from loguru import logger
from pydantic import BaseModel
from pydantic_ai import Agent, UserPromptNode, ModelRequestNode, CallToolsNode
from pydantic_ai.messages import ToolReturnPart, ToolCallPart
from pydantic_ai.result import FinalResult
from pydantic_graph.nodes import End

from .config import global_settings
from .deps import AgentDeps
from .device import AndroidDevice, WebDevice
from .prompt import SYSTEM_PROMPT
from .tools import AndroidAgentTool, WebAgentTool
from .util.platform import Platform


class ResultsType(BaseModel):
    step: int
    description: str
    action: str
    element_bbox: list[float]
    labeled_image_url: str
    error: str


class OutputType(BaseModel):
    is_success: bool
    # results: list[ResultsType]


@dataclass
class UiAgent:
    model: str
    deps: AgentDeps
    agent: Agent[AgentDeps, OutputType]

    @classmethod
    async def create(cls, *args, **kwargs):
        raise NotImplementedError

    @staticmethod
    async def create_report(report_data: str, report_dir: Union[Path, str]) -> Path:
        logger.info('创建步骤报告...')
        logger.debug(f'report_data: {report_data}')

        report_dir = Path(report_dir)
        report_dir.mkdir(parents=True, exist_ok=True)

        template = Path(__file__).parent / "report_template.html"
        content = template.read_text().replace('{reportData}', report_data)

        output_path = report_dir / f'report_{datetime.now(): %Y%m%d%H%M%S}.html'
        output_path.write_text(content)
        logger.info(f"报告：{output_path.resolve().as_uri()}")
        return output_path

    @staticmethod
    def format_logger_node(node):
        if isinstance(node, UserPromptNode):
            logger.info(f"🤖Agent start user task: {repr(node.user_prompt)}")

        elif isinstance(node, ModelRequestNode):
            for part in node.request.parts:
                if isinstance(part, ToolReturnPart):
                    logger.info(f"🤖Agent tool feedback: {part.tool_name} -> {part.content}")

        elif isinstance(node, CallToolsNode):
            for part in node.model_response.parts:
                if isinstance(part, ToolCallPart):
                    logger.info(f"🤖Agent tool call: {part.tool_name}({part.args})")

        elif isinstance(node, End):
            node = cast(End[FinalResult[OutputType]], node)
            logger.info(f"🤖Agent finished with output: {node.data.output.model_dump()}")

    async def run(self, prompt: str, system_prompt: Optional[str] = None, report_dir: str = "./report"):
        # TODO: 给用户添加额外的自定义系统提示词，某些场景需要，如：如果出现位置、权限、用户协议等弹窗，点击同意。如果出现登录页面，关闭它。
        async with self.agent.iter(user_prompt=prompt, deps=self.deps, output_type=OutputType) as agent_run:
            async for node in agent_run:
                if self.deps.settings.log_graph_node:
                    self.format_logger_node(node)
            assert agent_run.result is not None, 'The graph run did not finish properly'
            result = agent_run.result

        logger.info(result.output)
        # report_data = result.output.dict()
        logger.info(f"steps: {self.deps.context.steps}")
        report_data = {'is_success': result.output.is_success,
                       'results': [step.dict() for step in self.deps.context.steps.values()]}
        # if self.deps.context.page:
        #     for item in report_data['results']:
        #         item['page'] = self.deps.context.page.get(item.get('labeled_image_url')) or []
        return await self.create_report(json.dumps(report_data, ensure_ascii=False), report_dir)


SimulateDeviceType: TypeAlias = Literal['iPhone 15', 'iPhone 15 Pro', 'iPhone 15 Pro Max', 'iPhone 6'] | str


class WebAgent(UiAgent):
    @classmethod
    async def create(
            cls,
            model: Optional[str] = None,
            *,
            device: Optional[WebDevice] = None,
            simulate_device: Optional[SimulateDeviceType] = None,
            headless: Optional[bool] = None,
            debug: Optional[bool] = None,
    ):

        settings = global_settings.copy_and_update(
            model=model,
            simulate_device=simulate_device,
            headless=headless,
            debug=debug)

        logger.info(f'settings: {settings}')

        device = device or await WebDevice.create(settings.headless, settings.simulate_device)
        deps = AgentDeps(device, settings)
        tool = WebAgentTool()
        screen_resolution = f'{device.device_size.width}x{device.device_size.height}'

        agent = Agent[AgentDeps, OutputType](
            model=global_settings.model,
            system_prompt=SYSTEM_PROMPT.format(screen_resolution=screen_resolution),
            deps_type=AgentDeps,
            tools=tool.tools,
            output_type=OutputType,
            retries=2
        )
        return cls(model, deps, agent)


class MobileAgent(UiAgent):

    @classmethod
    async def create(
            cls, model: Optional[str] = None,
            *,
            serial: Optional[str] = None,
            platform: Optional[str | Platform] = None,
            debug: Optional[bool] = None,
    ):
        settings = global_settings.copy_and_update(model=model, debug=debug)

        logger.info(f'settings: {settings}')

        device = await AndroidDevice.create(serial=serial, platform=platform)
        deps = AgentDeps(device, settings)
        tool = AndroidAgentTool()
        screen_resolution = f'{device.device_size.width}x{device.device_size.height}'

        agent = Agent[AgentDeps, OutputType](
            model=model,
            system_prompt=SYSTEM_PROMPT.format(screen_resolution=screen_resolution),
            deps_type=AgentDeps,
            tools=tool.tools,
            output_type=OutputType,
            retries=2
        )
        return cls(model, deps, agent)
