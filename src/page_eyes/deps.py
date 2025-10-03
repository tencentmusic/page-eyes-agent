#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Author : aidenmo
# @Email : aidenmo@tencent.com
# @Time : 2025/5/23 18:30
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Optional, TypeVar, Literal, Generic

from pydantic import BaseModel, Field, confloat, conlist, ConfigDict

from .config import Settings

T = TypeVar('T')


class DeviceSize(BaseModel):
    """当前设备尺寸"""
    width: int
    height: int


class ScreenInfo(BaseModel):
    """当前屏幕信息"""
    image_url: str = ''
    screen_elements: list[dict] = Field(default_factory=list)

    def reset(self):
        self.image_url = ''
        self.screen_elements = []


class StepInfo(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    step: int
    description: str = ''
    action: str = ''
    params: dict = Field(default_factory=dict)
    image_url: str = ''
    screen_elements: list[dict] = Field(default_factory=list)
    is_success: bool = True


@dataclass
class ToolContext:
    """
    工具额外的上下文信息
    steps: 所有步骤信息
    screen_info: 当前屏幕信息
    """
    steps: OrderedDict[int, StepInfo] = field(default_factory=OrderedDict)
    screen_info: ScreenInfo = field(default_factory=ScreenInfo)


@dataclass
class AgentDeps(Generic[T]):
    device: T
    settings: Settings
    context: ToolContext = field(default_factory=ToolContext)


class ActionInfo(BaseModel):
    action: str
    description: str


class StepActionInfo(ActionInfo):
    step: int = Field(ge=1)

    def __repr_args__(self):
        return sorted(super().__repr_args__(), key=lambda item: {'step': 0}.get(item[0], 1))


class OpenUrlActionInfo(StepActionInfo):
    url: Optional[str] = None


class LocationActionInfo(StepActionInfo):
    element_bbox: conlist(confloat(ge=0.0, le=1.0), min_length=4, max_length=4)

    def get_coordinate(self, device_size: DeviceSize) -> tuple[int, int]:
        """计算坐标, 返回 (x, y)"""
        x1, y1, x2, y2 = self.element_bbox
        width, height = device_size.width, device_size.height
        return int((x1 + x2) / 2 * width), int((y1 + y2) / 2 * height)


class ClickActionInfo(LocationActionInfo):
    pass


class InputActionInfo(LocationActionInfo):
    text: str


class SwipeActionInfo(StepActionInfo):
    to: Literal['left', 'right', 'top', 'bottom']


class SwipeFromCoordinateActionInfo(StepActionInfo):
    coordinates: conlist(item_type=tuple[int, int], min_length=2)


class WaitActionInfo(StepActionInfo):
    timeout: int


class AssertContainsActionInfo(StepActionInfo):
    keywords: list[str]


class ToolResult(BaseModel, Generic[T]):
    is_success: bool
    description: Optional[str] = None
    output: Optional[T] = None

    @classmethod
    def success(cls, output: T = None, description: str = None):
        return cls(is_success=True, output=output, description=description)

    @classmethod
    def failed(cls, output: T = None, description: str = None):
        return cls(is_success=False, output=output, description=description)
