#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Author : aidenmo
# @Email : aidenmo@tencent.com
# @Time : 2025/9/30 11:56
import sys

import pytest
import pytest_asyncio
from loguru import logger

from page_eyes.agent import WebAgent, AndroidAgent, PlanningAgent, HarmonyAgent
from page_eyes.util.platform import Platform

logger.remove()
logger.add(sys.stdout, level="DEBUG")

debug = False

serial = ''  # Android 设备序列号
connect_key = '127.0.0.1:9002'  # Harmony 设备连接key


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
    return await AndroidAgent.create(serial=serial, platform=Platform.QY, debug=debug)


@pytest_asyncio.fixture(scope="session")
async def harmony_agent():
    if not connect_key:
        logger.info("未指定 Harmony 设备, 将使用默认第一个设备")
    return await HarmonyAgent.create(connect_key=connect_key, platform=Platform.KG, debug=debug)
