#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Author : aidenmo
# @Email : aidenmo@tencent.com
# @Time : 2025/9/30 11:56
import sys

import pytest
import pytest_asyncio
from loguru import logger

from page_eyes.agent import WebAgent, AndroidAgent, PlanningAgent, IOSAgent
from page_eyes.util.platform import Platform

logger.remove()
logger.add(sys.stdout, level="INFO")

debug = True

serial = ''  # Android 设备序列号


@pytest.fixture(scope="session")
def planning_agent():
    return PlanningAgent()


@pytest_asyncio.fixture(scope="session")
async def web_agent_pc():
    return await WebAgent.create(debug=debug)


@pytest_asyncio.fixture(scope="session")
async def web_agent_mobile():
    return await WebAgent.create(simulate_device='iPhone 15 Pro Max', debug=debug)


@pytest_asyncio.fixture(scope="session")
async def android_agent():
    if not serial:
        logger.info("未指定 Android 设备, 将使用默认第一个设备")
    return await AndroidAgent.create(serial=serial, platform=Platform.KG, debug=debug)


@pytest_asyncio.fixture(scope="session")
async def ios_agent():
    return await IOSAgent.create(wda_url="http://10.91.215.85:8100",debug=debug)
