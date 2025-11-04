#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Author : aidenmo
# @Email : aidenmo@tencent.com
# @Time : 2025/5/23 15:31
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional, Union

from loguru import logger
from pydantic import TypeAdapter
from pydantic_ai import Agent, UserPromptNode, ModelRequestNode, CallToolsNode, RunContext
from pydantic_ai.agent import AgentRunResult
from pydantic_ai.messages import ToolReturnPart, ToolCallPart
from pydantic_ai.usage import Usage

from .config import global_settings
from .deps import AgentDeps, SimulateDeviceType, PlanningOutputType, StepOutputType, PlanningStep, StepActionInfo
from .device import AndroidDevice, WebDevice
from .prompt import SYSTEM_PROMPT, PLANNING_SYSTEM_PROMPT
from .tools import AndroidAgentTool, WebAgentTool, AgentDepsType
from .util.platform import Platform


@dataclass
class PlanningAgent:
    """PlanningAgent class for planning tasks."""
    model: Optional[str] = None
    deps: Optional[AgentDepsType] = None

    async def run(self, prompt: str) -> AgentRunResult[PlanningOutputType]:
        """Run the agent with the given prompt."""
        model = self.model or global_settings.model
        agent = Agent(model=model, system_prompt=PLANNING_SYSTEM_PROMPT, output_type=PlanningOutputType)
        return await agent.run(prompt.strip(), deps=self.deps)


def extra_system_prompt(ctx: RunContext[AgentDepsType]):
    """动态添加额外的系统提示词"""
    context = ctx.deps.context
    step = context.current_step.step
    planning = context.current_step.planning
    return f'当前步骤序号是：{step}，是否需要获取屏幕元素信息：{planning.need_get_screen_info}'


@dataclass
class UiAgent:
    model: str
    deps: AgentDepsType
    agent: Agent

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

    async def run(self, prompt: str, system_prompt: Optional[str] = None, report_dir: str = "./report"):
        # TODO: 给用户添加额外的自定义系统提示词，某些场景需要，如：如果出现位置、权限、用户协议等弹窗，点击同意。如果出现登录页面，关闭它。
        planning_agent = PlanningAgent(model=self.model, deps=self.deps)
        planning_result = await planning_agent.run(prompt)
        planning_steps = planning_result.output.steps

        logger.info(f"🤖Agent planning result: {planning_result.output}")

        self.agent.system_prompt(extra_system_prompt)
        if system_prompt:
            self.agent.system_prompt(lambda: system_prompt)

        for step, planning in enumerate(planning_steps, start=1):
            self.deps.context.current_step.step = step
            self.deps.context.current_step.planning = planning

            async with self.agent.iter(
                    user_prompt=planning.instruction,
                    deps=self.deps,
                    usage=planning_result.usage()) as agent_run:
                async for node in agent_run:
                    if self.deps.settings.log_graph_node:
                        self.format_logger_node(node)
                assert agent_run.result is not None, 'The graph run did not finish properly'
        await self.deps.tool.tear_down(
            RunContext(deps=self.deps, model=self.agent.model, usage=Usage(), prompt=None),
            action=StepActionInfo(action='tear_down', description='任务完成', step=len(planning_steps) + 1)
        )
        logger.debug(f"steps: {self.deps.context.steps}")

        is_success_output = all([step.is_success for step in self.deps.context.steps.values()])

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
            tool_cls: Optional[type[WebAgentTool]] = None,
            debug: Optional[bool] = None,
    ):
        settings = global_settings.copy_and_update(
            model=model,
            simulate_device=simulate_device,
            headless=headless,
            debug=debug)

        logger.info(f'settings: {settings}')

        device = device or await WebDevice.create(settings.headless, settings.simulate_device)
        tool = WebAgentTool() if tool_cls is None else tool_cls()
        deps: AgentDeps[WebDevice, WebAgentTool] = AgentDeps(settings, device, tool)

        agent = Agent[AgentDeps](
            model=settings.model,
            system_prompt=SYSTEM_PROMPT,
            deps_type=AgentDeps,
            tools=tool.tools,
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
            tool_cls: Optional[type[AndroidAgentTool]] = None,
            debug: Optional[bool] = None,
    ):
        settings = global_settings.copy_and_update(model=model, debug=debug)

        logger.info(f'settings: {settings}')

        device = await AndroidDevice.create(serial=serial, platform=platform)

        tool = AndroidAgentTool() if tool_cls is None else tool_cls()
        deps: AgentDeps[AndroidDevice, AndroidAgentTool] = AgentDeps(settings, device, tool)

        agent = Agent[AgentDeps, StepOutputType](
            model=settings.model,
            system_prompt=SYSTEM_PROMPT,
            deps_type=AgentDeps,
            tools=tool.tools,
            output_type=StepOutputType,
            retries=2
        )
        return cls(model, deps, agent)
