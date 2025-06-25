#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Author : aidenmo
# @Email : aidenmo@tencent.com
# @Time : 2025/5/23 18:30
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Generic, TypeVar
from typing import TypedDict

from playwright.async_api import JSHandle

from .config import Settings


class DeviceInfo(TypedDict):
    device_name: str
    screen_resolution: str


@dataclass
class Context:
    page: dict = field(default_factory=dict)
    steps: dict = field(default_factory=OrderedDict)
    box_handle: JSHandle = None


T = TypeVar('T')


@dataclass
class AgentDeps(Generic[T]):
    device: T
    settings: Settings
    context: Context = field(default_factory=Context)
