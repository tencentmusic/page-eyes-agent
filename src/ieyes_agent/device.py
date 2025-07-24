#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Author : aidenmo
# @Email : aidenmo@tencent.com
# @Time : 2025/6/6 14:58
from dataclasses import dataclass
from typing import Optional

from adbutils import AdbClient, AdbDevice
from playwright.async_api import async_playwright, Playwright, Page, Browser, BrowserContext, ViewportSize
from pydantic import BaseModel

from .util.platform import Platform


class DeviceSize(BaseModel):
    width: int
    height: int


@dataclass
class WebDevice:
    playwright: Optional[Playwright]
    browser: Browser
    context: BrowserContext
    page: Page
    device_size: DeviceSize
    simulate_device: Optional[str] = None

    @classmethod
    async def create(cls, headless: bool = False, simulate_device: Optional[str] = None) -> "WebDevice":
        """异步工厂方法用于创建实例"""
        playwright = await async_playwright().start()
        browser = await playwright.chromium.launch(
            channel='chrome',
            headless=headless,
        )
        context_params = {'viewport': ViewportSize(width=1920, height=1080)}
        if simulate_device and simulate_device in playwright.devices:
            context_params.update(playwright.devices[simulate_device])

        context = await browser.new_context(**context_params)
        page = await context.new_page()
        device_size = DeviceSize(**page.viewport_size)

        return cls(playwright, browser, context, page, device_size, simulate_device)

    @classmethod
    async def from_page(cls, page: Page, simulate_device: Optional[str] = None) -> "WebDevice":
        """通过page对象创建实例"""
        playwright = None
        context = page.context
        browser = context.browser

        device_size = DeviceSize(**page.viewport_size)

        return cls(playwright, browser, context, page, device_size, simulate_device)


@dataclass
class AndroidDevice:
    client: AdbClient
    adb_device: AdbDevice
    device_size: DeviceSize
    platform: Platform

    @classmethod
    async def create(cls, serial: Optional[str] = None, platform: Optional[Platform] = Platform.QY):
        client = AdbClient()
        current_devices = client.device_list()
        if serial:
            if serial not in current_devices:
                output = client.connect(serial, timeout=10)
                if 'connected' not in output:
                    raise Exception(f"adb connect failed: {output}")
            adb_device: AdbDevice = client.device(serial=serial)
        elif current_devices:
            adb_device: AdbDevice = client.device_list()[0]
        else:
            raise Exception("No adb device found")

        window_size = adb_device.window_size()
        device_size = DeviceSize(width=window_size.width, height=window_size.height)
        return cls(client, adb_device, device_size, platform)
