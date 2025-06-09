#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Author : aidenmo
# @Email : aidenmo@tencent.com
# @Time : 2025/5/23 15:31
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional, Union

from loguru import logger
from pydantic import BaseModel
from pydantic_ai import Agent

from .deps import AgentDeps
from .device import AndroidDevice, WebDevice
from .prompt import SYSTEM_PROMPT
from .tools import AndroidAgentTool, WebAgentTool


class ResultsType(BaseModel):
    step: int
    description: str
    action: str
    element_bbox: list[float, float, float, float]
    device_size: str
    labeled_image_url: str
    error: str


class OutputType(BaseModel):
    is_success: bool
    results: list[ResultsType]


@dataclass
class UiAgent:
    model: str
    deps: AgentDeps
    agent: Agent

    @classmethod
    async def create(cls, *args, **kwargs):
        raise NotImplementedError

    async def create_report(self, report_data: str, report_dir: Union[Path, str]):
        logger.info('创建报告...')
        report_dir = Path(report_dir)
        report_dir.mkdir(parents=True, exist_ok=True)

        template = Path(__file__).parent / "report_template.html"
        content = template.read_text().replace('{reportData}', report_data)

        content = content.replace('{pageData}', json.dumps(self.deps.context.page, ensure_ascii=False))
        output_path = report_dir / f'report_{datetime.now(): %Y%m%d%H%M%S}.html'
        output_path.write_text(content)
        logger.info(f"报告：{output_path.resolve().as_uri()}")

    async def run(self, prompt: str, system_prompt: Optional[str] = None, report_dir: str = "./report"):
        # TODO: 给用户添加自定义系统提示词，某些场景需要，如：如果出现位置、权限、用户协议等弹窗，点击同意。如果出现登录页面，关闭它。
        result = await self.agent.run(user_prompt=prompt, deps=self.deps)
        logger.info(result.output)
        await self.create_report(result.output.model_dump_json(), report_dir)


class WebAgent(UiAgent):
    @classmethod
    async def create(cls, model: str, headless: bool = False):
        device = await WebDevice.create(headless=headless)
        deps = AgentDeps(device)
        tool = WebAgentTool()
        screen_resolution = f'{device.device_size.width}x{device.device_size.height}'

        agent = Agent(
            model=model,
            system_prompt=SYSTEM_PROMPT.format(screen_resolution=screen_resolution),
            deps_type=AgentDeps,
            tools=tool.tools,
            output_type=OutputType,
            retries=2
        )
        return cls(model, deps, agent)


class MobileAgent(UiAgent):

    @classmethod
    async def create(cls, model: str, serial: Optional[str] = None):
        device = await AndroidDevice.create(serial=serial)
        deps = AgentDeps(device)
        tool = AndroidAgentTool()
        screen_resolution = f'{device.device_size.width}x{device.device_size.height}'

        agent = Agent(
            model=model,
            system_prompt=SYSTEM_PROMPT.format(screen_resolution=screen_resolution),
            deps_type=AgentDeps,
            tools=tool.tools,
            output_type=OutputType,
            retries=2
        )
        return cls(model, deps, agent)
