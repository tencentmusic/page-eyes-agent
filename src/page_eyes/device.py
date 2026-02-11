#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Author : aidenmo
# @Email : aidenmo@tencent.com
# @Time : 2025/6/6 14:58
import asyncio
import os
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from adbutils import AdbClient, AdbDevice
from playwright.async_api import async_playwright, Playwright, Page, BrowserContext, ViewportSize
import wda
from dotenv import load_dotenv
from loguru import logger

from .deps import DeviceSize
from .util.hdc import HdcClient, HdcDevice
from .util.platform import Platform

# 加载 .env 文件
load_dotenv()


@dataclass
class WebDevice:
    playwright: Optional[Playwright]
    context: BrowserContext
    page: Page
    device_size: DeviceSize
    simulate_device: Optional[str] = None
    is_mobile: Optional[bool] = None

    @classmethod
    async def create(cls, headless: bool = False, simulate_device: Optional[str] = None) -> "WebDevice":
        """异步工厂方法用于创建实例"""
        playwright = await async_playwright().start()
        context_params = {'viewport': ViewportSize(width=1600, height=900)}
        is_mobile = False
        if simulate_device and simulate_device in playwright.devices:
            is_mobile = True
            context_params.update(playwright.devices[simulate_device])
            del context_params['has_touch']  # fix swipe scene
            del context_params['default_browser_type']  # launch_persistent_context not support default_browser_type

        context = await playwright.firefox.launch_persistent_context(
            user_data_dir=Path(tempfile.gettempdir()) / 'playwright',
            headless=headless,
            # devtools=True,
            **context_params
        )

        page = context.pages[0]
        device_size = DeviceSize(**page.viewport_size)

        return cls(playwright, context, page, device_size, simulate_device, is_mobile)

    @classmethod
    async def from_page(cls, page: Page, simulate_device: Optional[str] = None) -> "WebDevice":
        """通过page对象创建实例"""
        playwright = None
        context = page.context

        device_size = DeviceSize(**page.viewport_size)

        return cls(playwright, context, page, device_size, simulate_device)


@dataclass
class AndroidDevice:
    client: AdbClient
    adb_device: AdbDevice
    device_size: DeviceSize
    platform: Platform

    @classmethod
    async def create(cls, serial: Optional[str] = None, platform: Optional[Platform] = Platform.QY):
        """异步工厂方法用于创建实例"""
        client = AdbClient()
        current_devices = client.device_list()
        if serial:
            if serial not in [item.serial for item in current_devices]:
                output = client.connect(serial, timeout=10)
                if 'connected' not in output:
                    raise Exception(f"adb connect failed: {output}")
            adb_device: AdbDevice = client.device(serial=serial)
        elif current_devices:
            adb_device: AdbDevice = current_devices[0]
        else:
            raise Exception("No adb device found")

        window_size = adb_device.window_size()
        device_size = DeviceSize(width=window_size.width, height=window_size.height)
        return cls(client, adb_device, device_size, platform)


async def start_wda_if_needed(udid: str = None, wda_project_path: str = None, timeout: int = 30) -> bool:
    """
    尝试启动WebDriverAgent

    Args:
        udid: iOS设备的UDID，如果不提供则从环境变量IOS_UDID读取
        wda_project_path: WebDriverAgent项目路径，如果不提供则从环境变量IOS_WDA_PROJECT_PATH读取
        timeout: 启动超时时间（秒）

    Returns:
        bool: 是否成功启动或已经在运行
    """
    if udid is None:
        udid = os.getenv("IOS_UDID")

    if wda_project_path is None:
        wda_project_path = os.getenv("IOS_WDA_PROJECT_PATH")

    # 如果没有配置UDID或项目路径，跳过自动启动
    if not udid or not wda_project_path:
        logger.warning("未配置IOS_UDID或IOS_WDA_PROJECT_PATH，跳过自动启动WebDriverAgent")
        return False

    try:
        logger.info(f"尝试启动WebDriverAgent... UDID: {udid}")

        cmd = [
            "xcodebuild",
            "-project", f"{wda_project_path}/WebDriverAgent.xcodeproj",
            "-scheme", "WebDriverAgentRunner",
            "-destination", f"id={udid}",
            "test"
        ]

        logger.debug(f"执行命令: {' '.join(cmd)}")

        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=wda_project_path
        )

        logger.info(f"等待WebDriverAgent启动... (超时: {timeout}秒)")

        await asyncio.sleep(3)
        if process.poll() is not None:
            stdout, stderr = process.communicate()
            logger.error(f"WebDriverAgent启动失败")
            logger.error(f"stdout: {stdout.decode('utf-8', errors='ignore')}")
            logger.error(f"stderr: {stderr.decode('utf-8', errors='ignore')}")
            return False

        logger.info("✅ WebDriverAgent进程已启动")
        return True

    except FileNotFoundError:
        logger.error("未找到xcodebuild命令，请确保已安装Xcode")
        return False
    except Exception as e:
        logger.error(f"启动WebDriverAgent失败: {e}")
        return False


@dataclass
class IOSDevice:
    """iOS 设备连接类，通过 WebDriverAgent 连接"""
    wda_client: wda.Client
    device_size: DeviceSize
    platform: Platform

    @classmethod
    async def create(cls, wda_url: str, platform: Optional[Platform] = Platform.QY, auto_start_wda: bool = True):
        """
        创建iOS设备连接
        Args:
            wda_url: WebDriverAgent URL（必填）
            platform: 平台类型
            auto_start_wda: 是否自动启动WDA（默认True）
        Returns:
            IOSDevice实例
        """
        try:
            logger.info(f"尝试连接WebDriverAgent: {wda_url}")
            wda_client = wda.Client(wda_url)
            window_size = wda_client.window_size()
            device_size = DeviceSize(width=window_size.width, height=window_size.height)
            status = wda_client.status()
            if not status:
                raise Exception(f"Failed to get device status from WebDriverAgent at {wda_url}")

            logger.info("✅ 成功连接到WebDriverAgent")
            return cls(wda_client, device_size, platform)

        except Exception as first_error:
            logger.warning(f"首次连接失败: {first_error}")
            # 如果连接失败且允许自动启动，尝试启动WDA
            if auto_start_wda:
                logger.info("尝试自动启动WebDriverAgent...")
                # 启动WDA【只在MACOS环境下且安装了Xcode的条件下才有效，推荐自己启动】
                started = await start_wda_if_needed()
                if started:
                    logger.info("等待WebDriverAgent完全启动...")
                    max_retries = 10
                    retry_delay = 3
                    for i in range(max_retries):
                        try:
                            await asyncio.sleep(retry_delay)
                            logger.info(f"第 {i+1}/{max_retries} 次尝试连接...")
                            wda_client = wda.Client(wda_url)
                            window_size = wda_client.window_size()
                            device_size = DeviceSize(width=window_size.width, height=window_size.height)
                            status = wda_client.status()
                            if status:
                                logger.info("✅ 成功连接到WebDriverAgent")
                                return cls(wda_client, device_size, platform)
                        except Exception as retry_error:
                            if i == max_retries - 1:
                                raise Exception(f"启动WDA后仍无法连接: {retry_error}")
                            logger.debug(f"连接失败，继续重试... {retry_error}")

            raise Exception(f"Failed to connect to WebDriverAgent at {wda_url}: {first_error}")


async def start_wda_if_needed(udid: str = None, wda_project_path: str = None, timeout: int = 30) -> bool:
    """
    尝试启动WebDriverAgent

    Args:
        udid: iOS设备的UDID，如果不提供则从环境变量IOS_UDID读取
        wda_project_path: WebDriverAgent项目路径，如果不提供则从环境变量IOS_WDA_PROJECT_PATH读取
        timeout: 启动超时时间（秒）

    Returns:
        bool: 是否成功启动或已经在运行
    """
    if udid is None:
        udid = os.getenv("IOS_UDID")

    if wda_project_path is None:
        wda_project_path = os.getenv("IOS_WDA_PROJECT_PATH")

    # 如果没有配置UDID或项目路径，跳过自动启动
    if not udid or not wda_project_path:
        logger.warning("未配置IOS_UDID或IOS_WDA_PROJECT_PATH，跳过自动启动WebDriverAgent")
        return False

    try:
        logger.info(f"尝试启动WebDriverAgent... UDID: {udid}")

        cmd = [
            "xcodebuild",
            "-project", f"{wda_project_path}/WebDriverAgent.xcodeproj",
            "-scheme", "WebDriverAgentRunner",
            "-destination", f"id={udid}",
            "test"
        ]

        logger.debug(f"执行命令: {' '.join(cmd)}")

        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=wda_project_path
        )

        logger.info(f"等待WebDriverAgent启动... (超时: {timeout}秒)")

        await asyncio.sleep(3)
        if process.poll() is not None:
            stdout, stderr = process.communicate()
            logger.error(f"WebDriverAgent启动失败")
            logger.error(f"stdout: {stdout.decode('utf-8', errors='ignore')}")
            logger.error(f"stderr: {stderr.decode('utf-8', errors='ignore')}")
            return False

        logger.info("✅ WebDriverAgent进程已启动")
        return True

    except FileNotFoundError:
        logger.error("未找到xcodebuild命令，请确保已安装Xcode")
        return False
    except Exception as e:
        logger.error(f"启动WebDriverAgent失败: {e}")
        return False


@dataclass
class IOSDevice:
    """iOS 设备连接类，通过 WebDriverAgent 连接"""
    wda_client: wda.Client
    device_size: DeviceSize
    platform: Platform

    @classmethod
    async def create(cls, wda_url: str, platform: Optional[Platform] = Platform.QY, auto_start_wda: bool = True):
        """
        创建iOS设备连接
        Args:
            wda_url: WebDriverAgent URL（必填）
            platform: 平台类型
            auto_start_wda: 是否自动启动WDA（默认True）
        Returns:
            IOSDevice实例
        """
        try:
            logger.info(f"尝试连接WebDriverAgent: {wda_url}")

            wda_client = wda.Client(wda_url)

            window_size = wda_client.window_size()
            device_size = DeviceSize(width=window_size.width, height=window_size.height)

            status = wda_client.status()
            if not status:
                raise Exception(f"Failed to get device status from WebDriverAgent at {wda_url}")

            logger.info("✅ 成功连接到WebDriverAgent")

            return cls(wda_client, device_size, platform)

        except Exception as first_error:
            logger.warning(f"首次连接失败: {first_error}")
            # 如果连接失败且允许自动启动，尝试启动WDA
            if auto_start_wda:
                logger.info("尝试自动启动WebDriverAgent...")
                # 启动WDA【只在MACOS环境下且安装了Xcode的条件下才有效，推荐自己启动】
                started = await start_wda_if_needed()
                if started:
                    logger.info("等待WebDriverAgent完全启动...")
                    max_retries = 10
                    retry_delay = 3
                    for i in range(max_retries):
                        try:
                            await asyncio.sleep(retry_delay)
                            logger.info(f"第 {i+1}/{max_retries} 次尝试连接...")
                            wda_client = wda.Client(wda_url)
                            window_size = wda_client.window_size()
                            device_size = DeviceSize(width=window_size.width, height=window_size.height)
                            status = wda_client.status()
                            if status:
                                logger.info("✅ 成功连接到WebDriverAgent")
                                return cls(wda_client, device_size, platform)
                        except Exception as retry_error:
                            if i == max_retries - 1:
                                raise Exception(f"启动WDA后仍无法连接: {retry_error}")
                            logger.debug(f"连接失败，继续重试... {retry_error}")

            raise Exception(f"Failed to connect to WebDriverAgent at {wda_url}: {first_error}")

        except Exception as e:
            raise Exception(f"Failed to connect to WebDriverAgent at {wda_url}: {str(e)}")


@dataclass
class HarmonyDevice:
    client: HdcClient
    hdc_device: HdcDevice
    device_size: DeviceSize
    platform: Platform

    @classmethod
    async def create(cls, connect_key: Optional[str] = None, platform: Optional[Platform] = Platform.QY):
        """异步工厂方法用于创建实例"""
        client = HdcClient()
        current_devices = client.device_list()
        if connect_key:
            if connect_key not in [item.connect_key for item in current_devices]:
                output = client.connect(connect_key)
                if 'Connect failed' in output:
                    raise Exception(f"hdc connect failed: {output}")
            hdc_device: HdcDevice = client.device(connect_key=connect_key)
        elif current_devices:
            hdc_device: HdcDevice = current_devices[0]
        else:
            raise Exception("No adb device found")

        window_size = hdc_device.window_size()
        device_size = DeviceSize(width=window_size.width, height=window_size.height)
        return cls(client, hdc_device, device_size, platform)
