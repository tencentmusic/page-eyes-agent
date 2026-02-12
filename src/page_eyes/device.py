#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Author : aidenmo
# @Email : aidenmo@tencent.com
# @Time : 2025/6/6 14:58
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Generic

from adbutils import AdbClient, AdbDevice
from playwright.async_api import async_playwright, Playwright, Page, BrowserContext, ViewportSize

from .deps import DeviceSize, DeviceT, ClientT
from .util.hdc_tool import HdcClient, HdcDevice
from .util.platform import Platform


@dataclass
class Device(Generic[ClientT, DeviceT]):
    client: ClientT
    target: DeviceT
    device_size: DeviceSize

    @classmethod
    def create(cls, *args, **kwargs) -> DeviceT:
        raise NotImplementedError


@dataclass
class WebDevice(Device[Playwright, Page]):
    context: BrowserContext
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

        context = await playwright.chromium.launch_persistent_context(
            user_data_dir=Path(tempfile.gettempdir()) / 'playwright',
            channel='chrome',
            headless=headless,
            # devtools=True,
            **context_params
        )

        page = context.pages[0]
        device_size = DeviceSize(**page.viewport_size)

        return cls(playwright, page, device_size, context, simulate_device, is_mobile)

    @classmethod
    async def from_page(cls, page: Page, simulate_device: Optional[str] = None) -> "WebDevice":
        """通过page对象创建实例"""
        playwright = None
        context = page.context

        device_size = DeviceSize(**page.viewport_size)

        return cls(playwright, page, device_size, context, simulate_device)


@dataclass
class AndroidDevice(Device[AdbClient, AdbDevice]):
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
class HarmonyDevice(Device[HdcClient, HdcDevice]):
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
