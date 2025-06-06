#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Author : aidenmo
# @Email : aidenmo@tencent.com
# @Time : 2025/6/6 14:58
from enum import StrEnum
from typing import Optional

from adbutils import AdbClient, AdbDevice
from playwright.sync_api import sync_playwright
from playwright.async_api import async_playwright, Page as AsyncPage
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


class WebDevice:
    def __init__(self, headless: bool = False):
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(channel='chrome', headless=headless, args=['--start-maximized'])
        self.context = self.browser.new_context(no_viewport=True)
        self.page = self.context.new_page()
        width = self.page.evaluate('() => window.innerWidth')
        height = self.page.evaluate('() => window.innerHeight')
        self.device_size = DeviceSize(width=width, height=height)

        self.device_info = {
            'device_name': 'Web PC',
            'screen_resolution': f'{self.device_size.width}x{self.device_size.height}',
        }

class AsyncWebDevice:
    def __init__(self, browser, context, page: AsyncPage, device_size):
        self.browser = browser
        self.context = context
        self.page = page
        self.device_size = device_size
        self.device_info = {
            'device_name': 'Web PC',
            'screen_resolution': f'{self.device_size.width}x{self.device_size.height}',
        }

    @classmethod
    async def create(cls, headless: bool = False) -> "AsyncWebDevice":
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

        return cls(browser, context, page, device_size)


class AndroidDevice:
    def __init__(self, serial: Optional[str] = None):
        self.client = AdbClient()
        self.adb_device: AdbDevice = self.client.device(serial=serial) if serial else self.client.device_list()[0]
        window_size = self.adb_device.window_size()
        self.device_size = DeviceSize(width=window_size.width, height=window_size.height)

        self.device_info = {
            'device_name': 'Android',
            'screen_resolution': f'{self.device_size.width}x{self.device_size.height}',
        }
