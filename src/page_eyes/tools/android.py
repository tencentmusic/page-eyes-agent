#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Author : aidenmo
# @Email : aidenmo@tencent.com
# @Time : 2026/2/11 15:52
from typing import TypeAlias

from pydantic_ai import RunContext

from .base import AgentTool
from .mobile import MobileAgentTool
from ..deps import AgentDeps
from ..device import AndroidDevice

AgentDepsType: TypeAlias = AgentDeps[AndroidDevice, AgentTool]


class AndroidAgentTool(MobileAgentTool):

    @staticmethod
    def _start_url(ctx: RunContext[AgentDepsType], url: str):
        return ctx.deps.device.target.shell(f'am start -a android.intent.action.VIEW -d "{url}"')
