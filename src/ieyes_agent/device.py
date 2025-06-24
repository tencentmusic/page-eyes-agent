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

from ieyes_agent.util.platform import Platform


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

    @classmethod
    async def _get_device_size(cls, page: Page) -> DeviceSize:
        """获取设备尺寸, 更可靠的视口尺寸获取方式"""
        viewport_size = await page.evaluate("""() => ({
                        width: document.documentElement.clientWidth,
                        height: document.documentElement.clientHeight
                    })""")

        return DeviceSize(
            width=viewport_size["width"],
            height=viewport_size["height"]
        )

    @classmethod
    async def create(cls, headless: bool = False) -> "WebDevice":
        """异步工厂方法用于创建实例"""
        playwright = await async_playwright().start()
        browser = await playwright.chromium.launch(
            channel='chrome',
            headless=headless,
        )
        context = await browser.new_context(**playwright.devices['iPhone 6'])
        # context = await browser.new_context(viewport=ViewportSize(width=1920, height=1080))
        page = await context.new_page()

        # device_size = await cls._get_device_size(page)
        device_size = DeviceSize(**page.viewport_size)

        return cls(playwright, browser, context, page, device_size)

    @classmethod
    async def from_page(cls, page: Page) -> "WebDevice":
        """通过page对象创建实例"""
        playwright = None
        context = page.context
        browser = context.browser

        device_size = await cls._get_device_size(page)

        return cls(playwright, browser, context, page, device_size)


@dataclass
class AndroidDevice:
    client: AdbClient
    adb_device: AdbDevice
    device_size: DeviceSize
    platform: Platform

    @classmethod
    async def create(cls, serial: Optional[str] = None, platform: Optional[Platform] = Platform.QY):
        client = AdbClient()
        adb_device: AdbDevice = client.device(serial=serial) if serial else client.device_list()[0]
        window_size = adb_device.window_size()
        device_size = DeviceSize(width=window_size.width, height=window_size.height)
        return cls(client, adb_device, device_size, platform)
