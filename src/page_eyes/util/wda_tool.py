#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Author : xinttan
# @Email : xinttan@tencent.com
# @Time : 2026/2/12 16:00
import tempfile
from dataclasses import dataclass
from typing import List, NamedTuple, Optional

import wda
from PIL.Image import Image
from loguru import logger


class WdaError(Exception):
    """WebDriverAgent error"""


@dataclass
class WdaDeviceInfo:
    """WDA设备信息"""
    name: str
    udid: str
    version: str
    state: str

@dataclass
class AppInfo:
    """应用信息"""
    bundle_id: str
    display_name: str



class WdaClient(wda.Client):
    """扩展WDA Client，添加更多便捷方法"""

    def long_press(self, x: float, y: float, duration: float = 2.0):
        """长按指定坐标
        """
        self.tap_hold(x, y, duration)
        logger.info(f'Long press at ({x}, {y}) for {duration}s')

    def input_text_with_clear(self, text: str, clear: bool = True):
        """输入文本，支持先清空
        """
        if clear:
            try:
                self.send_keys('')
            except:
                pass

        self.send_keys(text)
        logger.info(f'Input text: {text}')

    def get_app_list(self) -> List[AppInfo]:
        """获取设备上所有应用的Bundle ID和显示名称

        优先使用 pymobiledevice3 获取详细信息，失败则回退到 WDA 方法

        Args:
            wda_client: WDA客户端实例

        Returns:
            应用信息列表
        """
        app_list = []

        try:
            from pymobiledevice3.lockdown import create_using_usbmux
            from pymobiledevice3.services.installation_proxy import InstallationProxyService

            # 通过 USB 连接到设备
            lockdown = create_using_usbmux()
            installation_proxy = InstallationProxyService(lockdown=lockdown)

            # 获取所有应用（用户应用和系统应用）
            apps_info = installation_proxy.get_apps(application_type='Any')

            # 提取 bundle ID 和显示名称
            if apps_info:
                for bundle_id, app_info in apps_info.items():
                    display_name = app_info.get('CFBundleDisplayName') or app_info.get('CFBundleName', '')
                    app_list.append(AppInfo(
                        bundle_id=bundle_id,
                        display_name=display_name
                    ))
            logger.info(f'Found {len(app_list)} apps on device using pymobiledevice3')

        except ImportError:
            logger.warning('pymobiledevice3 not installed, falling back to WDA app_list')
        except Exception as e:
            logger.warning(f'Failed to get app list with pymobiledevice3: {e}, falling back to WDA')

        return app_list

    def tap_and_input(self, x: float, y: float, text: str, send_enter: bool = False, tap_delay: float = 0.5):
        """点击坐标并输入文本(因为WDA的Session=Client，所以都用Client)

        Args:
            x: 点击的x坐标
            y: 点击的y坐标
            text: 要输入的文本
            send_enter: 是否发送回车键
            tap_delay: 点击后等待时间（秒）
        """
        import time

        # 先点击输入框获取焦点
        self.tap(x, y)
        logger.info(f'Tap at ({x}, {y}) to focus input field')

        # 等待输入框获取焦点
        time.sleep(tap_delay)

        # 输入文本
        self.send_keys(text)
        logger.info(f'Input text: {text}')

        # 发送回车键
        if send_enter:
            self.send_keys('\n')
            logger.info('Send enter key')





