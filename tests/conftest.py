#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Author : aidenmo
# @Email : aidenmo@tencent.com
# @Time : 2025/9/30 11:56
import asyncio
import sys

import pytest
import pytest_asyncio
from loguru import logger

from src.page_eyes.agent import WebAgent, MobileAgent
from src.page_eyes.util.platform import Platform

logger.remove()
logger.add(sys.stdout, level="INFO")

debug = True

serial = ''


@pytest_asyncio.fixture(scope="session")
async def web_agent_pc():
    return await WebAgent.create(debug=debug)


@pytest_asyncio.fixture(scope="session")
async def web_agent_mobile():
    return await WebAgent.create(simulate_device='iPhone 15 Pro Max', debug=debug)


@pytest_asyncio.fixture(scope="session")
async def mobile_agent():
    if not serial:
        pytest.skip("未指定 Android 设备")
    return await MobileAgent.create(serial=serial, platform=Platform.QY, debug=debug)
