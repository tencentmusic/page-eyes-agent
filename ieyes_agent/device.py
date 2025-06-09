#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Author : aidenmo
# @Email : aidenmo@tencent.com
# @Time : 2025/6/6 14:58
from dataclasses import dataclass
from enum import StrEnum
from typing import Optional

from adbutils import AdbClient, AdbDevice
from playwright.async_api import async_playwright, Playwright, Page, Browser, BrowserContext
from pydantic import BaseModel


class Platform(StrEnum):
    WEB = "WEB"
    QY = "QY"
    KG = "KG"
    KW = "KW"
    APPLET = "APPLET"


class DeviceSize(BaseModel):
    width: int
    height: int


@dataclass
class WebDevice:
    playwright: Playwright
    browser: Browser
    context: BrowserContext
    page: Page
    device_size: DeviceSize

    @classmethod
    async def create(cls, headless: bool = False) -> "WebDevice":
        """异步工厂方法用于创建实例"""
        playwright = await async_playwright().start()
        browser = await playwright.chromium.launch(
            channel='chrome',
            headless=headless,
            args=['--start-maximized']
        )
        context = await browser.new_context(no_viewport=True)
        page = await context.new_page()

        # 更可靠的视口尺寸获取方式
        viewport_size = page.viewport_size
        if viewport_size is None:
            viewport_size = await page.evaluate("""() => ({
                width: document.documentElement.clientWidth,
                height: document.documentElement.clientHeight
            })""")

        device_size = DeviceSize(
            width=viewport_size["width"],
            height=viewport_size["height"]
        )

        return cls(playwright, browser, context, page, device_size)


@dataclass
class AndroidDevice:
    client: AdbClient
    adb_device: AdbDevice
    device_size: DeviceSize

    @classmethod
    async def create(cls, serial: Optional[str] = None):
        client = AdbClient()
        adb_device: AdbDevice = client.device(serial=serial) if serial else client.device_list()[0]
        window_size = adb_device.window_size()
        device_size = DeviceSize(width=window_size.width, height=window_size.height)
        return cls(client, adb_device, device_size)
