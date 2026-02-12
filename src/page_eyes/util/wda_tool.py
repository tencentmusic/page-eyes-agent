#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Author : xinttan
# @Email : xinttan@tencent.com
# @Time : 2026/2/12 16:00
from dataclasses import dataclass
from typing import List, NamedTuple, Optional

import wda
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


class WindowSize(NamedTuple):
    """窗口尺寸"""
    width: int
    height: int


class WdaDeviceProxy:
    """WDA设备代理类，提供高级功能封装

    参考adb_tool.AdbDeviceProxy和hdc_tool的设计
    封装WDA常用操作，提供更友好的API
    """

    def __init__(self, client: wda.Client):
        """初始化代理

        Args:
            client: WDA Client对象
        """
        self._client = client

    @property
    def client(self) -> wda.Client:
        """获取WDA客户端"""
        return self._client

    def get_app_list(self, app_type: str = 'all') -> List[dict]:
        """获取应用列表（改进版本，支持获取所有应用）

        Args:
            app_type: 应用类型
                - 'user': 仅用户安装的应用
                - 'system': 仅系统应用
                - 'all': 所有应用（默认）

        Returns:
            应用列表，每个应用包含bundleId、name等信息
        """
        try:
            if app_type == 'all':
                # 获取所有应用：用户应用 + 系统应用
                user_apps = self._client.app_list('user') or []
                system_apps = self._client.app_list('system') or []
                apps = user_apps + system_apps
                logger.info(f'Found {len(user_apps)} user apps and {len(system_apps)} system apps')
            else:
                # 获取指定类型的应用
                apps = self._client.app_list(app_type) or []
                logger.info(f'Found {len(apps)} {app_type} apps')

            return apps
        except Exception as e:
            logger.warning(f'Failed to get app list: {e}')
            # 如果带参数失败，尝试不带参数（某些WDA版本的默认行为）
            try:
                apps = self._client.app_list() or []
                logger.info(f'Found {len(apps)} apps (fallback method)')
                return apps
            except Exception as e2:
                logger.error(f'Failed to get app list (fallback): {e2}')
                return []

    def get_bundle_ids(self, app_type: str = 'all') -> List[str]:
        """获取应用Bundle ID列表

        Args:
            app_type: 应用类型（user/system/all）

        Returns:
            Bundle ID列表
        """
        apps = self.get_app_list(app_type)
        bundle_ids = [app.get('bundleId', '') for app in apps if app.get('bundleId')]
        return bundle_ids

    def smart_input_text(self, text: str, element_x: float, element_y: float, clear: bool = True):
        """智能输入文本

        Args:
            text: 要输入的文本
            element_x: 输入框x坐标
            element_y: 输入框y坐标
            clear: 是否先清空（默认True）
        """
        session = self._client.session()

        # 点击输入框获取焦点
        session.tap(element_x, element_y)
        logger.info(f'Tap input field at ({element_x}, {element_y})')

        # 输入文本
        if clear:
            # 尝试清空现有内容
            try:
                session.send_keys('')
            except:
                pass

        session.send_keys(text)
        logger.info(f'Input text: {text}')

    def device_info(self) -> WdaDeviceInfo:
        """获取设备信息"""
        try:
            info = self._client.status()
            ios_info = info.get('value', {}).get('ios', {}) if 'value' in info else info.get('ios', {})

            return WdaDeviceInfo(
                name=ios_info.get('name', 'Unknown'),
                udid=ios_info.get('udid', 'Unknown'),
                version=ios_info.get('version', 'Unknown'),
                state=info.get('state', 'Unknown')
            )
        except Exception as e:
            logger.warning(f'Failed to get device info: {e}')
            return WdaDeviceInfo(name='Unknown', udid='Unknown', version='Unknown', state='Unknown')

    def battery_info(self) -> dict:
        """获取电池信息"""
        try:
            info = self._client.status()
            ios_info = info.get('value', {}).get('ios', {}) if 'value' in info else info.get('ios', {})
            battery = ios_info.get('battery', {})

            return {
                'level': battery.get('level', -1),
                'state': battery.get('state', 'Unknown')
            }
        except Exception as e:
            logger.warning(f'Failed to get battery info: {e}')
            return {'level': -1, 'state': 'Unknown'}

    def healthcheck(self) -> bool:
        """WDA服务健康检查

        Returns:
            True表示WDA服务正常，False表示异常
        """
        try:
            status = self._client.status()
            return status is not None
        except Exception as e:
            logger.error(f'WDA healthcheck failed: {e}')
            return False

