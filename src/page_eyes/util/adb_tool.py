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
        self.y_adb_path = Path("/data/local/tmp/yadb")
        self._push_yadb()

    def _push_yadb(self):
        if not getattr(self._device, 'yadb', None):
            if not self._device.sync.exists(str(self.y_adb_path)):
                adb_bin_path = Path(__file__).parent / 'bin' / 'yadb'
                logger.info('push yadb to device...')
                self._device.sync.push(src=adb_bin_path, dst=self.y_adb_path)
            setattr(self._device, 'yadb', self.y_adb_path)

    def execute_command(self, *args: str):
        self._device.shell([
            'app_process',
            f'-Djava.class.path={self.y_adb_path}',
            f'{self.y_adb_path.parent}',
            'com.ysbing.yadb.Main',
            *args
        ])

    def input_text(self, text: str):
        self.execute_command('-keyboard', text)
