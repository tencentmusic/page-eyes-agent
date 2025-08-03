#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Author : aidenmo
# @Email : aidenmo@tencent.com
# @Time : 2025/5/30 12:34
from pathlib import Path

from adbutils import AdbDevice
from loguru import logger


class AdbDeviceProxy:
    def __init__(self, device: AdbDevice):
        self._device = device
        self.adb_target_dir = "/data/local/tmp"
        self.adb_path = self._push_yadb()

    def _push_yadb(self):
        if not getattr(self._device, 'yadb', None):
            adb_bin_path = Path(__file__).parent / 'bin' / 'yadb'
            logger.info('push yadb to device...')
            self._device.sync.push(src=adb_bin_path, dst=self.adb_target_dir)
            setattr(self._device, 'yadb', f'{self.adb_target_dir}/yadb')
        return getattr(self._device, 'yadb')

    def execute_command(self, *args: str):
        self._device.shell([
            'app_process',
            f'-Djava.class.path={self.adb_path}',
            f'{self.adb_target_dir}',
            'com.ysbing.yadb.Main',
            *args
        ])

    def input_text(self, text: str):
        self.execute_command('-keyboard', text)
