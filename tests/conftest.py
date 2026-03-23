#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Author : aidenmo
# @Email : aidenmo@tencent.com
# @Time : 2025/9/30 11:56
import asyncio
import socket
import subprocess
import sys

import pytest
import pytest_asyncio
from loguru import logger

from page_eyes.agent import (
    AndroidAgent,
    ElectronAgent,
    HarmonyAgent,
    IOSAgent,
    PlanningAgent,
    WebAgent,
)
from page_eyes.util.platform import Platform
from pydantic_ai_skills import SkillsToolset

logger.remove()
logger.add(sys.stdout, level="INFO")

debug = True

serial = ""  # Android 设备序列号
connect_key = ""  # Harmony 设备连接key
wda_url = "http://localhost:8100"  # iOS 设备wda url
CDP_URL = "http://127.0.0.1:9222"  # Electron 应用 CDP url
ELECTRON_APP = "Xmind"  # Electron 应用名称（与 .app 目录名一致）


@pytest.fixture(scope="session")
def planning_agent():
    return PlanningAgent()


@pytest_asyncio.fixture(scope="session")
async def web_agent_pc():
    return await WebAgent.create(debug=debug)


@pytest_asyncio.fixture(scope="session")
async def web_agent_mobile():
    return await WebAgent.create(simulate_device="iPhone 15 Pro Max", debug=debug)


@pytest_asyncio.fixture(scope="session")
async def android_agent():
    if not serial:
        logger.info("未指定 Android 设备, 将使用默认第一个设备")
    return await AndroidAgent.create(serial=serial, platform=Platform.QY, debug=debug)


@pytest_asyncio.fixture(scope="session")
async def harmony_agent():
    if not connect_key:
        logger.info("未指定 Harmony 设备, 将使用默认第一个设备")
    return await HarmonyAgent.create(
        connect_key=connect_key, platform=Platform.KG, debug=debug
    )


@pytest_asyncio.fixture(scope="session")
async def ios_agent():
    return await IOSAgent.create(wda_url=wda_url, debug=debug, toolsets=[SkillsToolset()])


def _is_port_open(host: str, port: int) -> bool:
    """检查端口是否可连接"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(1)
        return s.connect_ex((host, port)) == 0


@pytest_asyncio.fixture(scope="session")
async def electron_agent():
    cdp_port = int(CDP_URL.split(":")[-1])

    # 每次都先关闭旧实例，确保干净启动
    logger.info(f"🔄 关闭已运行的 {ELECTRON_APP}（如有）...")
    subprocess.run(
        ["osascript", "-e", f'quit app "{ELECTRON_APP}"'], capture_output=True
    )
    await asyncio.sleep(3)

    # 确保进程完全退出
    subprocess.run(["pkill", "-f", ELECTRON_APP], capture_output=True)
    await asyncio.sleep(2)

    logger.info(f"🚀 正在启动 {ELECTRON_APP}（--remote-debugging-port={cdp_port}）...")
    subprocess.Popen(
        ["open", "-a", ELECTRON_APP, "--args", f"--remote-debugging-port={cdp_port}"]
    )

    for i in range(20):
        await asyncio.sleep(2)
        if _is_port_open("127.0.0.1", cdp_port):
            logger.info(f"✅ {ELECTRON_APP} 启动成功，CDP 端口已就绪")
            break
        logger.info(f"等待 {ELECTRON_APP} 启动... ({i + 1}/20)")
    else:
        raise RuntimeError(
            f"{ELECTRON_APP} 启动超时（40s），CDP 端口 {cdp_port} 未就绪"
        )

    agent = await ElectronAgent.create(cdp_url=CDP_URL, debug=debug)
    yield agent

    logger.info(f"测试结束，{ELECTRON_APP} 保持运行")
