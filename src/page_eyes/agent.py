#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Author : aidenmo
# @Email : aidenmo@tencent.com
# @Time : 2025/5/23 15:31
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from random import randint
from typing import Optional, Union

from loguru import logger
from pydantic import TypeAdapter
from pydantic_ai import Agent, UserPromptNode, ModelRequestNode, CallToolsNode, RunContext, UnexpectedModelBehavior
from pydantic_ai.agent import AgentRunResult
from pydantic_ai.messages import ToolReturnPart, ToolCallPart
from pydantic_ai.usage import Usage

from .config import default_settings, Settings, BrowserConfig
from .deps import AgentDeps, SimulateDeviceType, PlanningOutputType, PlanningStep, ToolParams, StepInfo, \
    MarkFailedParams
from .device import WebDevice, AndroidDevice, HarmonyDevice, IOSDevice
from .prompt import SYSTEM_PROMPT, PLANNING_SYSTEM_PROMPT
from .tools import AgentDepsType, WebAgentTool, AndroidAgentTool, HarmonyAgentTool, IOSAgentTool
from .util.platform import Platform


@dataclass
class PlanningAgent:
    """PlanningAgent class for planning tasks."""
    model: Optional[str] = None
    deps: Optional[AgentDepsType] = None

    async def run(self, prompt: str) -> AgentRunResult[PlanningOutputType]:
        """Run the agent with the given prompt."""
        model = self.model or default_settings.model
        agent = Agent(
            model=model,
            system_prompt=PLANNING_SYSTEM_PROMPT,
            output_type=PlanningOutputType,
            model_settings=default_settings.model_settings,
        )
        return await agent.run(prompt.strip(), deps=self.deps)


@dataclass
class UiAgent:
    model: str
    deps: AgentDepsType
    agent: Agent[AgentDepsType]

    @staticmethod
    def merge_settings(override_settings: Settings) -> Settings:
        settings = Settings(
            **{**default_settings.model_dump(), **override_settings.model_dump(exclude_none=True)}
        )
        logger.info(f'settings: {settings}')
        return settings

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
        content = template.read_text(encoding='utf-8').replace('{reportData}', report_data)
        output_path = report_dir / f'report_{datetime.now():%Y%m%d%H%M%S}_{randint(10000, 99999)}.html'
        output_path.write_text(content, encoding='utf-8')
        logger.info(f"报告：{output_path.resolve().as_uri()}")
        return output_path

    def handle_graph_node(self, node):
        """Format the logger node based on the given node type."""
        if isinstance(node, UserPromptNode):
            logger.debug(f"🤖Agent start user task: {repr(node.user_prompt)}")

        elif isinstance(node, ModelRequestNode):
            for part in node.request.parts:
                if isinstance(part, ToolReturnPart):
                    logger.debug(f"🤖Agent tool result: {part.tool_name} -> {part.content}")

        elif isinstance(node, CallToolsNode):
            parts = node.model_response.parts
            tool_parts = [part for part in parts if isinstance(part, ToolCallPart)]
            self.deps.context.current_step.parallel_tool_calls = False
            self.deps.context.current_step.parallel_tool_calls = len(tool_parts) > 1
            for part in tool_parts:
                logger.debug(f"🤖Agent tool call: {part.tool_name}, args: {part.args}")

    async def _sub_agent_run(self, planning, usage) -> AgentRunResult:
        async with self.agent.iter(user_prompt=planning.instruction, deps=self.deps, usage=usage) as agent_run:
            async for node in agent_run:
                self.handle_graph_node(node)
            return agent_run.result

    async def run(self, prompt: str, system_prompt: Optional[str] = None, report_dir: str = "./report"):
        # TODO: 给用户添加额外的自定义系统提示词，某些场景需要，如：如果出现位置、权限、用户协议等弹窗，点击同意。如果出现登录页面，关闭它。
        logger.info(f"🤖Agent start planning...")

        planning_agent = PlanningAgent(model=self.model, deps=self.deps)
        planning_result = await planning_agent.run(prompt)
        planning_steps = planning_result.output.steps

        planning_steps = [*planning_steps, PlanningStep(instruction='结束任务')]
        logger.info(f"🤖Agent planning finished.")
        for index, step in enumerate(planning_steps, 1):
            logger.info(f'◽️step{index}. {step.instruction}')

        if system_prompt:
            self.agent.system_prompt(lambda: system_prompt)

        usage = planning_result.usage()
        ctx = RunContext(deps=self.deps, model=self.agent.model, usage=Usage(), prompt=None)

        logger.info(f"🤖Agent start executing steps...")
        for step, planning in enumerate(planning_steps, start=1):
            self.deps.context.add_step_info(StepInfo(step=step, planning=planning, description=planning.instruction))
            logger.info('')
            logger.info(f'▶️ step={step} {planning.instruction}')

            if planning.instruction != '结束任务':
                try:
                    result = await self._sub_agent_run(planning, usage)
                    usage = result.usage()
                    logger.info(f"💬 {result.output}")
                except UnexpectedModelBehavior as e:
                    await self.deps.tool.mark_failed(ctx, MarkFailedParams(
                        reason=str(e),
                    ))
                    logger.error(f'step={step} {planning.instruction}: {e}')

                logger.info(f'{"✅" if self.deps.context.current_step.is_success else "❌"} '
                            f'step={step} {planning.instruction}')
            else:
                await self.deps.tool.tear_down(ctx, params=ToolParams(action='tear_down', instruction='任务完成'))

            # 步骤执行后如果没有截图则自动补上，比如滑动、等待
            if not self.deps.context.current_step.image_url:
                await self.deps.tool.get_screen(ctx, parse_element=False)

            if not self.deps.context.current_step.is_success:
                break

        logger.debug(f"steps: {self.deps.context.steps}")
        logger.debug(f"usage: {usage}")

        is_success_output = all([step.is_success for step in self.deps.context.steps.values()])

        report_data = {'is_success': is_success_output,
                       'device_size': self.deps.device.device_size,
                       'steps': self.deps.context.steps}
        report_json = TypeAdapter(dict).dump_json(report_data).decode(encoding='utf-8')
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
        settings = cls.merge_settings(Settings(
            model=model,
            browser=BrowserConfig(headless=headless, simulate_device=simulate_device),
            debug=debug
        ))

        device = device or await WebDevice.create(settings.browser.headless, settings.browser.simulate_device)
        tool = WebAgentTool() if tool_cls is None else tool_cls()
        deps: AgentDeps[WebDevice, WebAgentTool] = AgentDeps(settings, device, tool)

        agent = Agent[AgentDeps](
            model=settings.model,
            system_prompt=SYSTEM_PROMPT,
            model_settings=settings.model_settings,
            deps_type=AgentDeps,
            tools=tool.tools,
            retries=3
        )
        return cls(model, deps, agent)


class AndroidAgent(UiAgent):
    """AndroidAgent class for mobile device automation."""

    @classmethod
    async def create(
            cls, model: Optional[str] = None,
            *,
            serial: Optional[str] = None,
            platform: Optional[str | Platform] = None,
            tool_cls: Optional[type[AndroidAgentTool]] = None,
            debug: Optional[bool] = None,
    ):
        settings = cls.merge_settings(Settings(
            model=model,
            debug=debug
        ))

        device = await AndroidDevice.create(serial=serial, platform=platform)

        tool = AndroidAgentTool() if tool_cls is None else tool_cls()
        deps: AgentDeps[AndroidDevice, AndroidAgentTool] = AgentDeps(settings, device, tool)

        agent = Agent[AgentDeps](
            model=settings.model,
            system_prompt=SYSTEM_PROMPT,
            model_settings=settings.model_settings,
            deps_type=AgentDeps,
            tools=tool.tools,
            retries=2
        )
        return cls(model, deps, agent)


class HarmonyAgent(UiAgent):
    """HarmonyAgent class for mobile device automation."""

    @classmethod
    async def create(
            cls, model: Optional[str] = None,
            *,
            connect_key: Optional[str] = None,
            platform: Optional[str | Platform] = None,
            tool_cls: Optional[type[HarmonyAgentTool]] = None,
            debug: Optional[bool] = None,
    ):
        settings = cls.merge_settings(Settings(
            model=model,
            debug=debug
        ))

        device = await HarmonyDevice.create(connect_key=connect_key, platform=platform)

        tool = HarmonyAgentTool() if tool_cls is None else tool_cls()
        deps: AgentDeps[HarmonyDevice, HarmonyAgentTool] = AgentDeps(settings, device, tool)

        agent = Agent[AgentDeps](
            model=settings.model,
            system_prompt=SYSTEM_PROMPT,
            model_settings=settings.model_settings,
            deps_type=AgentDeps,
            tools=tool.tools,
            retries=2
        )
        return cls(model, deps, agent)


class IOSAgent(UiAgent):
    @classmethod
    async def create(
            cls, model: Optional[str] = None,
            *,
            wda_url: str,
            platform: Optional[str | Platform] = None,
            tool_cls: Optional[type[IOSAgentTool]] = None,
            app_name_map: Optional[dict[str, str]] = None,
            debug: Optional[bool] = None,
    ):
        settings = cls.merge_settings(Settings(
            model=model,
            debug=debug
        ))

        device = await IOSDevice.create(wda_url=wda_url, platform=platform)

        tool = IOSAgentTool() if tool_cls is None else tool_cls()
        deps: AgentDeps[IOSDevice, IOSAgentTool] = AgentDeps(
            settings, device, tool,
            app_name_map=app_name_map or {}
        )

        agent = Agent[AgentDeps](
            model=settings.model,
            system_prompt=SYSTEM_PROMPT,
            model_settings=settings.model_settings,
            deps_type=AgentDeps,
            tools=tool.tools,
            retries=2
        )
        return cls(model, deps, agent)
