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

    def double_tap(self, x: float, y: float):
        """双击指定坐标
        """
        self.double_tap(x, y)
        logger.info(f'Double tap at ({x}, {y})')

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

    def swipe_with_direction(self, direction: str, distance: float = 0.5):
        """按方向滑动
        """
        size = self.window_size()
        width, height = size.width, size.height
        center_x, center_y = width / 2, height / 2

        swipe_map = {
            'up': (center_x, height * (0.5 + distance / 2), center_x, height * (0.5 - distance / 2)),
            'down': (center_x, height * (0.5 - distance / 2), center_x, height * (0.5 + distance / 2)),
            'left': (width * (0.5 + distance / 2), center_y, width * (0.5 - distance / 2), center_y),
            'right': (width * (0.5 - distance / 2), center_y, width * (0.5 + distance / 2), center_y),
        }

        if direction not in swipe_map:
            raise ValueError(f"Invalid direction: {direction}. Must be one of: up/down/left/right")

        x1, y1, x2, y2 = swipe_map[direction]
        self.swipe(x1, y1, x2, y2)
        logger.info(f'Swipe {direction} with distance {distance}')

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



