#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Author : aidenmo
# @Email : aidenmo@tencent.com
# @Time : 2025/5/23 18:30
from dataclasses import dataclass, field
from typing import TypedDict
from adbutils import AdbDevice


class DeviceInfo(TypedDict):
    device_name: str
    screen_resolution: str


@dataclass
class Context:
    page: dict = field(default_factory=dict)


@dataclass
class AgentDeps:
    device_info: DeviceInfo
    device: AdbDevice
    context: Context = field(default_factory=Context)
