#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Author : aidenmo
# @Email : aidenmo@tencent.com
# @Time : 2025/5/23 15:31
import json
from datetime import datetime
from pathlib import Path
from typing import Optional, Union

from pydantic_ai import Agent, ModelRetry, RunContext, Tool
from pydantic import BaseModel

from .deps import AgentDeps
from .prompt import SYSTEM_PROMPT
from loguru import logger
from .tools import AndroidAgentTool, WebAgentTool, AgentTool


class ResultsType(BaseModel):
    step: int
    description: str
    action: str
    element_id: int
    element_bbox: list[float, float, float, float]
    device_size: str
    labeled_image_url: str
    error: str


class OutputType(BaseModel):
    success: bool
    results: list[ResultsType]


class UiAgent:
    def __init__(self, model: str, deps: AgentDeps, tool: AgentTool):
        self.model = model
        self.deps = deps
        self.agent = Agent(
            model=model,
            system_prompt=SYSTEM_PROMPT.format(**deps.device_info),
            deps_type=AgentDeps,
            tools=tool.tools,
            output_type=OutputType,
            retries=2
        )

    def create_report(self, report_data: str, report_dir: Union[Path, str]):
        logger.info('创建报告...')
        report_dir = Path(report_dir)
        report_dir.mkdir(parents=True, exist_ok=True)

        template = Path(__file__).parent / "report_template.html"
        content = template.read_text().replace('{reportData}', report_data)
        if self.deps.context.page:
            content = content.replace('{pageData}', json.dumps(self.deps.context.page, ensure_ascii=False))
        output_path = report_dir / f'report_{datetime.now(): %Y%m%d%H%M%S}.html'
        output_path.write_text(content)
        logger.info(f"报告：{output_path.resolve().as_uri()}")

    def run(self, prompt: str, system_prompt: Optional[str] = None, report_dir: str = "./report"):
        # TODO: 给用户添加自定义系统提示词，某些场景需要，如：如果出现位置、权限、用户协议等弹窗，点击同意。如果出现登录页面，关闭它。
        result = self.agent.run_sync(user_prompt=prompt, deps=self.deps)
        logger.info(result.output)
        self.create_report(result.output.model_dump_json(), report_dir)


class WebAgent(UiAgent):
    def __init__(self, model: str, deps: AgentDeps):
        tool = WebAgentTool()
        super().__init__(model, deps, tool)


class MobileAgent(UiAgent):
    def __init__(self, model: str, deps: AgentDeps):
        tool = AndroidAgentTool()
        super().__init__(model, deps, tool)
