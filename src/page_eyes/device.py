#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Author : aidenmo
# @Email : aidenmo@tencent.com
# @Time : 2025/6/6 14:58
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from adbutils import AdbClient, AdbDevice
from playwright.async_api import async_playwright, Playwright, Page, BrowserContext, ViewportSize
import wda

from .deps import DeviceSize
from .util.platform import Platform


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


@dataclass
class IOSDevice:
    """iOS 设备连接类，通过 WebDriverAgent 连接"""
    wda_client: wda.Client
    device_size: DeviceSize
    platform: Platform

    @classmethod
    async def create(cls, wda_url: str = None, platform: Optional[Platform] = Platform.QY):
        if wda_url is None:
            wda_url = os.getenv("IOS_WDA_URL", "http://localhost:8100")

        try:
            wda_client = wda.Client(wda_url)
            window_size = wda_client.window_size()
            device_size = DeviceSize(width=window_size.width, height=window_size.height)
            status = wda_client.status()
            if not status:
                raise Exception(f"Failed to get device status from WebDriverAgent at {wda_url}")
                
            return cls(wda_client, device_size, platform)
            
        except Exception as e:
            raise Exception(f"Failed to connect to WebDriverAgent at {wda_url}: {str(e)}")
