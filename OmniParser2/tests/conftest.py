#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Author : aidenmo
# @Email : aidenmo@tencent.com
# @Time : 2025/9/30 11:56
import sys

import pytest
import pytest_asyncio

from util.logger import init_logger

init_logger()


@pytest.fixture(scope="session")
def planning_agent():
    pass


@pytest_asyncio.fixture(scope="session")
async def web_agent_pc():
    pass
