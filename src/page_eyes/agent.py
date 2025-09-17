#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Author : aidenmo
# @Email : aidenmo@tencent.com
# @Time : 2025/5/23 15:31
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional, Union, Literal, TypeAlias, cast

from loguru import logger
from pydantic import BaseModel, TypeAdapter
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


class OutputType(BaseModel):
    """
    执行指令完成后的需判断整个任务是否成功，并总结各个步骤执行结果，结果格式如下：
    - is_success: 任务否成功
    - summary: 总结各个步骤执行结果
    """
    is_success: bool
    # summary: str  # 加上步骤总结会增加结果输出耗时 3~5s


@dataclass
class UiAgent:
    model: str
    deps: AgentDeps[WebDevice | AndroidDevice]
    agent: Agent[AgentDeps, OutputType]

    @classmethod
    async def create(cls, *args, **kwargs):
        """Async factory method to create an instance of this class."""
        raise NotImplementedError

    @staticmethod
    async def create_report(report_data: str, report_dir: Union[Path, str]) -> Path:
        """Create a report file based on the given data and directory."""
        logger.info('创建步骤报告...')
        logger.debug(f'report_data: {report_data}')

        report_dir = Path(report_dir)
        report_dir.mkdir(parents=True, exist_ok=True)

        template = Path(__file__).parent / "report_template.html"
        content = template.read_text().replace('{reportData}', report_data)

        output_path = report_dir / f'report_{datetime.now():%Y%m%d%H%M%S}.html'
        output_path.write_text(content)
        logger.info(f"报告：{output_path.resolve().as_uri()}")
        return output_path

    @staticmethod
    def format_logger_node(node):
        """Format the logger node based on the given node type."""
        if isinstance(node, UserPromptNode):
            logger.info(f"🤖Agent start user task: {repr(node.user_prompt)}")

        elif isinstance(node, ModelRequestNode):
            for part in node.request.parts:
                if isinstance(part, ToolReturnPart):
                    logger.info(f"🤖Agent tool feedback: {part.tool_name} -> {part.content}")

        elif isinstance(node, CallToolsNode):
            for part in node.model_response.parts:
                if isinstance(part, ToolCallPart):
                    logger.info(f"🤖Agent tool call: {part.tool_name}({part.args.replace('{}', '')})")

        elif isinstance(node, End):
            node = cast(End[FinalResult[OutputType]], node)
            logger.info(f"🤖Agent finished with output: {node.data.output.model_dump()}")

    async def run(self, prompt: str, system_prompt: Optional[str] = None, report_dir: str = "./report"):
        # TODO: 给用户添加额外的自定义系统提示词，某些场景需要，如：如果出现位置、权限、用户协议等弹窗，点击同意。如果出现登录页面，关闭它。
        async with self.agent.iter(user_prompt=prompt.strip(), deps=self.deps, output_type=OutputType) as agent_run:
            async for node in agent_run:
                if self.deps.settings.log_graph_node:
                    self.format_logger_node(node)
            assert agent_run.result is not None, 'The graph run did not finish properly'
            result = agent_run.result

        logger.info(result.output)
        logger.info(f"steps: {self.deps.context.steps}")

        is_success_output = all([step.is_success for step in self.deps.context.steps.values()])
        if is_success_output != result.output.is_success:
            logger.warning(f'model return {result.output.is_success}, but real is {is_success_output}')

        report_data = {'is_success': is_success_output,
                       'device_size': self.deps.device.device_size,
                       'steps': self.deps.context.steps}
        report_json = TypeAdapter(dict).dump_json(report_data).decode()
        report_path = await self.create_report(report_json, report_dir)

        steps_output = [
                step.model_dump(include={'step', 'description', 'action', 'is_success'})
                for step in self.deps.context.steps.values()
        ]

        return {
            'is_success': is_success_output,
            'steps': steps_output,
            'report_path': report_path
        }


SimulateDeviceType: TypeAlias = Literal['iPhone 15', 'iPhone 15 Pro', 'iPhone 15 Pro Max', 'iPhone 6'] | str


class WebAgent(UiAgent):
    """WebAgent class for web automation."""
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

        agent = Agent[AgentDeps, OutputType](
            model=settings.model,
            system_prompt=SYSTEM_PROMPT,
            deps_type=AgentDeps,
            tools=tool.tools,
            output_type=OutputType,
            retries=3
        )
        return cls(model, deps, agent)


class MobileAgent(UiAgent):
    """MobileAgent class for mobile device automation."""

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

        agent = Agent[AgentDeps, OutputType](
            model=settings.model,
            system_prompt=SYSTEM_PROMPT,
            deps_type=AgentDeps,
            tools=tool.tools,
            output_type=OutputType,
            retries=2
        )
        return cls(model, deps, agent)
