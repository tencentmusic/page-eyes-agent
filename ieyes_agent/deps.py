#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Author : aidenmo
# @Email : aidenmo@tencent.com
# @Time : 2025/5/23 18:30
from dataclasses import dataclass, field
from typing import Generic, TypeVar
from typing import TypedDict
from playwright.async_api import JSHandle


class DeviceInfo(TypedDict):
    device_name: str
    screen_resolution: str


@dataclass
class Context:
    page: dict = field(default_factory=dict)
    box_handle: JSHandle = None


T = TypeVar('T')


@dataclass
class AgentDeps(Generic[T]):
    device: T
    context: Context = field(default_factory=Context)
