#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Author : aidenmo
# @Email : aidenmo@tencent.com
# @Time : 2025/5/23 15:31
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from random import randint
from typing import Optional, Union, cast

from loguru import logger
from openai.types import chat
from pydantic import TypeAdapter
from pydantic_ai import (
    Agent,
    CallToolsNode,
    ModelMessage,
    ModelRequestNode,
    RunContext,
    UnexpectedModelBehavior,
    UserPromptNode,
)
from pydantic_ai.agent import AgentRunResult
from pydantic_ai.capabilities import AbstractCapability
from pydantic_ai.messages import ToolReturnPart, ToolCallPart, ModelRequest, UserPromptPart
from pydantic_ai.messages import (
    ModelRequest,
    ToolCallPart,
    ToolReturnPart,
    UserPromptPart,
)
from pydantic_ai.usage import Usage
from pydantic_ai_skills import SkillsToolset, SkillsCapability

from .config import BrowserConfig, Settings, default_settings
from .deps import (
    AgentDeps,
    MarkFailedParams,
    PlanningOutputType,
    PlanningStep,
    SimulateDeviceType,
    StepInfo,
    ToolParams,
)
from .device import AndroidDevice, ElectronDevice, HarmonyDevice, IOSDevice, WebDevice
from .prompt import PLANNING_SYSTEM_PROMPT, SYSTEM_PROMPT
from .tools import (
    AgentDepsType,
    AgentTool,
    AndroidAgentTool,
    ElectronAgentTool,
    HarmonyAgentTool,
    IOSAgentTool,
    WebAgentTool,
)
from .util.platform import Platform

# pydantic ai 新版本，service_tier 为空字符串会报错，这里先打个补丁
_original_validate = chat.ChatCompletion.model_validate


@classmethod
def _patched_validate(cls, obj, *args, **kwargs):
    if isinstance(obj, dict) and obj.get("service_tier") == "":
        obj["service_tier"] = None
    return _original_validate(obj, *args, **kwargs)


chat.ChatCompletion.model_validate = _patched_validate


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


class ImageUserPromptPart(UserPromptPart):
    pass


@dataclass
class UiAgent:
    model: str
    deps: AgentDepsType
    agent: Agent[AgentDepsType]

    @staticmethod
    def merge_settings(override_settings: Settings) -> Settings:
        settings = Settings(
            **{
                **default_settings.model_dump(),
                **override_settings.model_dump(exclude_none=True),
            }
        )
        logger.info(f"settings: {settings}")
        return settings

    @classmethod
    async def history_processor(
            cls, ctx: RunContext, messages: list[ModelMessage]
    ) -> list[ModelMessage]:
        """上下文处理器"""
        if default_settings.model_type == "vlm" and isinstance(
                messages[-1], ModelRequest
        ):
            # 清理之前的截图
            for message in messages:
                if isinstance(message, ModelRequest):
                    message.parts = [
                        part
                        for part in message.parts
                        if not isinstance(part, ImageUserPromptPart)
                    ]

            # 每一步请求主动携带当前截图
            # screen: ScreenInfo = await ctx.deps.tool.get_screen(ctx=ctx)
            # messages[-1].parts.append(
            #     ImageUserPromptPart(content=[
            #         '当前屏幕截图：',
            #         ImageUrl(url=screen.image_url)
            #     ])
            # )

        return messages

    @classmethod
    async def create(cls, *args, **kwargs):
        """Async factory method to create an instance of this class."""
        raise NotImplementedError

    @classmethod
    def build_agent(cls, settings: Settings, tool: AgentTool, skills_dirs: list[str | Path], **kwargs):
        """Build the agent with the given arguments."""
        skills_dirs = skills_dirs or ['./skills']
        skills_capability = cast(
            AbstractCapability[AgentDeps],
            SkillsCapability(directories=[settings.root / 'skills', *skills_dirs])
        )
        toolset: SkillsToolset = skills_capability.get_toolset()
        if toolset.skills:
            logger.info(f"add skills: {set(toolset.skills.keys())}")

        agent = Agent[AgentDeps](
            model=settings.model,
            system_prompt=SYSTEM_PROMPT,
            model_settings=settings.model_settings,
            deps_type=AgentDeps,
            tools=tool.tools,
            capabilities=[skills_capability],
            # history_processors=[cls.history_processor],
            retries=2,
            **kwargs,
        )
        return agent

    @staticmethod
    async def create_report(report_data: str, report_dir: Union[Path, str]) -> Path:
        """Create a report file based on the given data and directory."""
        logger.info("创建步骤报告...")
        logger.debug(f"report_data: {report_data}")

        report_dir = Path(report_dir)
        report_dir.mkdir(parents=True, exist_ok=True)

        template = Path(__file__).parent / "report_template.html"
        content = template.read_text(encoding="utf-8").replace(
            "{reportData}", report_data
        )
        output_path = (
                report_dir
                / f"report_{datetime.now():%Y%m%d%H%M%S}_{randint(10000, 99999)}.html"
        )
        output_path.write_text(content, encoding="utf-8")
        logger.info(f"报告：{output_path.resolve().as_uri()}")
        return output_path

    def handle_graph_node(self, node):
        """Format the logger node based on the given node type."""
        if isinstance(node, UserPromptNode):
            logger.debug(f"🤖Agent start user task: {repr(node.user_prompt)}")

        elif isinstance(node, ModelRequestNode):
            for part in node.request.parts:
                if isinstance(part, ToolReturnPart):
                    logger.debug(
                        f"🤖Agent tool result: {part.tool_name} -> {part.content}"
                    )

        elif isinstance(node, CallToolsNode):
            if node.model_response.thinking:
                logger.info(f"💬thinking: {node.model_response.thinking}")
            parts = node.model_response.parts
            tool_parts = [part for part in parts if isinstance(part, ToolCallPart)]
            self.deps.context.current_step.parallel_tool_calls = False
            self.deps.context.current_step.parallel_tool_calls = len(tool_parts) > 1
            for part in tool_parts:
                args = part.args.replace("{}", "-")
                logger.info(
                    f"🤖Agent tool call: {part.tool_name}, args: {args}"
                )

    async def _sub_agent_run(self, planning, usage) -> AgentRunResult:
        async with self.agent.iter(
                user_prompt=planning.instruction, deps=self.deps, usage=usage
        ) as agent_run:
            async for node in agent_run:
                self.handle_graph_node(node)
            return agent_run.result

    async def run(
            self,
            prompt: str,
            system_prompt: Optional[str] = None,
            report_dir: str = "./report",
    ):
        # TODO: 给用户添加额外的自定义系统提示词，某些场景需要，如：如果出现位置、权限、用户协议等弹窗，点击同意。如果出现登录页面，关闭它。
        logger.info("🤖Agent start planning...")

        planning_agent = PlanningAgent(model=self.model, deps=self.deps)
        planning_result = await planning_agent.run(prompt)
        planning_steps = planning_result.output.steps

        planning_steps = [*planning_steps, PlanningStep(instruction="结束任务")]
        logger.info("🤖Agent planning finished.")
        for index, step in enumerate(planning_steps, 1):
            logger.info(f"◽️step{index}. {step.instruction}")

        if system_prompt:
            self.agent.system_prompt(lambda: system_prompt)

        usage = planning_result.usage()
        ctx = RunContext(
            deps=self.deps, model=self.agent.model, usage=Usage(), prompt=None
        )

        logger.info("🤖Agent start executing steps...")
        for step, planning in enumerate(planning_steps, start=1):
            self.deps.context.add_step_info(
                StepInfo(step=step, planning=planning, description=planning.instruction)
            )
            logger.info("")
            logger.info(f"▶️ step={step} {planning.instruction}")

            if planning.instruction != "结束任务":
                try:
                    result = await self._sub_agent_run(planning, usage)
                    usage = result.usage()
                    logger.info(f"💬 {str(result.output).strip()}")
                except UnexpectedModelBehavior as e:
                    await self.deps.tool.mark_failed(
                        ctx,
                        MarkFailedParams(
                            reason=str(e),
                        ),
                    )
                    logger.error(f"step={step} {planning.instruction}: {e}")

                logger.info(
                    f'{"✅" if self.deps.context.current_step.is_success else "❌"} '
                    f"step={step} {planning.instruction}"
                )
            else:
                await self.deps.tool.tear_down(
                    ctx, params=ToolParams(action="tear_down", instruction="任务完成")
                )

            # 步骤执行后如果没有截图则自动补上，比如滑动、等待
            if not self.deps.context.current_step.image_url:
                await self.deps.tool.get_screen(ctx, parse_element=False)

            if not self.deps.context.current_step.is_success:
                break

        logger.debug(f"steps: {self.deps.context.steps}")
        logger.debug(f"usage: {usage}")

        is_success_output = all(
            [step.is_success for step in self.deps.context.steps.values()]
        )

        report_data = {
            "is_success": is_success_output,
            "device_size": self.deps.device.device_size,
            "steps": self.deps.context.steps,
        }
        report_json = TypeAdapter(dict).dump_json(report_data).decode(encoding="utf-8")
        report_path = await self.create_report(report_json, report_dir)

        steps_output = [
            step.model_dump(include={"step", "description", "action", "is_success"})
            for step in self.deps.context.steps.values()
        ]

        return {
            "is_success": is_success_output,
            "steps": steps_output,
            "report_path": report_path,
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
            tool: Optional[WebAgentTool] = None,
            skills_dirs: Optional[list[str | Path]] = None,
            debug: Optional[bool] = None,
    ) -> "WebAgent":
        """异步工厂方法用于创建 WebAgent 实例。

        Args:
            model: 可选的 LLM 模型名称
            device: 可选的自定义 WebDevice 实例
            simulate_device: 可选的模拟设备类型
            headless: 可选的无头模式标志，启用后浏览器不显示界面
            tool: 可选的自定义 WebAgentTool 实例
            skills_dirs: 可选的技能目录列表
            debug: 可选的调试标志，启用后输出更多日志

        Returns:
            WebAgent 实例
        """
        settings = cls.merge_settings(
            Settings(
                model=model,
                browser=BrowserConfig(
                    headless=headless, simulate_device=simulate_device
                ),
                debug=debug,
            )
        )

        device = device or await WebDevice.create(
            settings.browser.headless, settings.browser.simulate_device
        )
        tool = tool or WebAgentTool()
        deps: AgentDeps[WebDevice, WebAgentTool] = AgentDeps(settings, device, tool)

        agent = cls.build_agent(settings, tool, skills_dirs)
        return cls(model, deps, agent)


class AndroidAgent(UiAgent):
    """AndroidAgent class for mobile device automation."""

    @classmethod
    async def create(
            cls,
            model: Optional[str] = None,
            *,
            serial: Optional[str] = None,
            platform: Optional[str | Platform] = None,
            tool: Optional[AndroidAgentTool] = None,
            skills_dirs: Optional[list[str | Path]] = None,
            debug: Optional[bool] = None,
    ) -> "AndroidAgent":
        """异步工厂方法用于创建 AndroidAgent 实例。

        Args:
            model: 可选的 LLM 模型名称
            serial: 可选的 Android 设备序列号
            platform: 可选的平台类型
            tool: 可选的自定义 AndroidAgentTool 实例
            skills_dirs: 可选的技能目录列表
            debug: 可选的调试标志，启用后输出更多日志

        Returns:
            AndroidAgent 实例
        """
        settings = cls.merge_settings(Settings(model=model, debug=debug))

        device = await AndroidDevice.create(serial=serial, platform=platform)

        tool = tool or AndroidAgentTool()
        deps: AgentDeps[AndroidDevice, AndroidAgentTool] = AgentDeps(settings, device, tool)

        agent = cls.build_agent(settings, tool, skills_dirs)
        return cls(model, deps, agent)


class HarmonyAgent(UiAgent):
    """HarmonyAgent class for mobile device automation."""

    @classmethod
    async def create(
            cls,
            model: Optional[str] = None,
            *,
            connect_key: Optional[str] = None,
            platform: Optional[str | Platform] = None,
            tool: Optional[HarmonyAgentTool] = None,
            skills_dirs: Optional[list[str | Path]] = None,
            debug: Optional[bool] = None,
    ) -> "HarmonyAgent":
        """异步工厂方法用于创建 HarmonyAgent 实例。

        Args:
            model: 可选的 LLM 模型名称
            connect_key: 可选的鸿蒙设备连接密钥
            platform: 可选的平台类型
            tool: 可选的自定义 HarmonyAgentTool 实例
            skills_dirs: 可选的技能目录列表
            debug: 可选的调试标志，启用后输出更多日志

        Returns:
            HarmonyAgent 实例
        """
        settings = cls.merge_settings(Settings(model=model, debug=debug))

        device = await HarmonyDevice.create(connect_key=connect_key, platform=platform)

        tool = tool or HarmonyAgentTool()
        deps: AgentDeps[HarmonyDevice, HarmonyAgentTool] = AgentDeps(settings, device, tool)

        agent = cls.build_agent(settings, tool, skills_dirs)
        return cls(model, deps, agent)


class IOSAgent(UiAgent):
    """IOSAgent class for mobile device automation."""
    @classmethod
    async def create(
            cls,
            model: Optional[str] = None,
            *,
            wda_url: str,
            platform: Optional[str | Platform] = None,
            tool: Optional[IOSAgentTool] = None,
            app_name_map: Optional[dict[str, str]] = None,
            skills_dirs: Optional[list[str | Path]] = None,
            debug: Optional[bool] = None
    ) -> "IOSAgent":
        """异步工厂方法用于创建 IOSAgent 实例。

        Args:
            model: 可选的 LLM 模型名称
            wda_url: WebDriverAgent 的连接地址
            platform: 可选的平台类型
            tool: 可选的自定义 IOSAgentTool 实例
            app_name_map: 可选的应用名称映射字典
            skills_dirs: 可选的技能目录列表
            debug: 可选的调试标志，启用后输出更多日志

        Returns:
            IOSAgent 实例
        """
        settings = cls.merge_settings(Settings(model=model, debug=debug))

        device = await IOSDevice.create(wda_url=wda_url, platform=platform)

        tool = tool or IOSAgentTool()
        deps: AgentDeps[IOSDevice, IOSAgentTool] = AgentDeps(settings, device, tool, app_name_map=app_name_map or {})

        agent = cls.build_agent(settings, tool, skills_dirs)
        return cls(model, deps, agent)


class ElectronAgent(UiAgent):
    """ElectronAgent class for Electron desktop app automation."""

    @classmethod
    async def create(
            cls,
            model: Optional[str] = None,
            *,
            cdp_url: str = "http://127.0.0.1:9222",
            tool: Optional[ElectronAgentTool] = None,
            skills_dirs: Optional[list[str | Path]] = None,
            debug: Optional[bool] = None,
    ) -> "ElectronAgent":
        """异步工厂方法用于创建 ElectronAgent 实例。

        Args:
            model: 可选的 LLM 模型名称
            cdp_url: Electron 应用的 CDP 远程调试地址
            tool: 可选的自定义 ElectronAgentTool 实例
            skills_dirs: 可选的技能目录列表
            debug: 可选的调试标志，启用后输出更多日志

        Returns:
            ElectronAgent 实例
        """
        settings = cls.merge_settings(Settings(model=model, debug=debug))

        device = await ElectronDevice.create(cdp_url=cdp_url)

        tool = tool or ElectronAgentTool()
        deps: AgentDeps[ElectronDevice, ElectronAgentTool] = AgentDeps(settings, device, tool)

        agent = cls.build_agent(settings, tool, skills_dirs)

        return cls(model, deps, agent)
