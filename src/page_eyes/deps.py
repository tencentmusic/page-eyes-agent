#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Author : aidenmo
# @Email : aidenmo@tencent.com
# @Time : 2025/5/23 18:30
from collections import OrderedDict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, TypeVar, Literal, Generic, TypeAlias

from pydantic import BaseModel, Field, confloat, conlist, ConfigDict

from .config import Settings

T = TypeVar('T')
DeviceT = TypeVar('DeviceT')
ToolT = TypeVar('ToolT')

SimulateDeviceType: TypeAlias = Literal['iPhone 15', 'iPhone 15 Pro', 'iPhone 15 Pro Max', 'iPhone 6'] | str


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
    step: int = 0
    description: str = ''
    action: str = ''
    params: dict = Field(default_factory=dict)
    image_url: str = ''
    planning: Optional['PlanningStep'] = Field(default=None, exclude=True)
    screen_elements: list[dict] = Field(default_factory=list)
    parallel_tool_calls: bool = Field(default=False, exclude=True)
    is_success: bool = True


@dataclass
class AgentContext:
    """
    Agent 额外的上下文信息
    steps: 所有步骤信息
    current_step: 当前步骤信息
    screen_info: 当前屏幕信息
    """
    steps: OrderedDict[int, StepInfo] = field(default_factory=OrderedDict)
    current_step: StepInfo = field(default_factory=StepInfo)

    def set_step_failed(self, reason: str):
        self.steps[self.current_step.step].is_success = False
        self.steps[self.current_step.step].action = 'mark_failed'
        self.steps[self.current_step.step].params = {'reason': reason}

    def add_step_info(self, step_info: StepInfo):
        self.current_step = self.steps.setdefault(step_info.step, step_info)
        return self.current_step

    def update_step_info(self, **kwargs):
        for key, value in kwargs.items():
            if hasattr(self.current_step, key):
                setattr(self.current_step, key, value)
        return self.current_step


@dataclass
class AgentDeps(Generic[DeviceT, ToolT]):
    settings: Settings
    device: DeviceT
    tool: ToolT
    context: AgentContext = field(default_factory=AgentContext)


class ToolParams(BaseModel):
    instruction: str = Field(description='用户指令，描述该步骤要做什么', exclude=True)
    action: str = Field(description='要执行的动作，如 click、input、swipe 等, 是调用的工具名称')


class OpenUrlToolParams(ToolParams):
    url: str = Field(description='要打开的url网址')


PositionType: TypeAlias = Literal['left', 'right', 'top', 'bottom']


class LocationToolParams(ToolParams):
    element_bbox: conlist(confloat(ge=0.0, le=1.0), min_length=4, max_length=4) = Field(description='要操作的元素 bbox')
    element_content: str = Field(description='要操作的元素内容')

    def get_coordinate(self,
                       device_size: DeviceSize,
                       position: Optional[PositionType] = None,
                       offset: Optional[float] = None) -> tuple[int, int]:
        """计算坐标, 返回 (x, y)"""
        x1, y1, x2, y2 = self.element_bbox
        width, height = device_size.width, device_size.height
        x, y = (x1 + x2) / 2, (y1 + y2) / 2
        offset = 0.25 if offset is None else offset
        if position == 'left':
            x = x1 + (x2 - x1) * offset
        elif position == 'right':
            x = x2 - (x2 - x1) * offset
        elif position == 'top':
            y = y1 + (y2 - y1) * offset
        elif position == 'bottom':
            y = y2 - (y2 - y1) * offset

        return int(x * width), int(y * height)


class ClickToolParams(LocationToolParams):
    """示例：
    - 点击"确定"按钮 -> position=None, offset=None
    - 点击"确定"按钮左侧 -> position='left', offset=None
    - 点击"确定"按钮左侧1/2处 -> position='left', offset=0.5
    - 点击"上传"按钮，上传文件:"/Users/Desktop/1.png" -> position=None, offset=None, file_path='/Users/Desktop/1.png'
    """
    position: Optional[PositionType] = Field(default=None, description='点击元素的相对位置')
    offset: Optional[float] = Field(default=None, description='相对位置的偏移量')
    file_path: Optional[Path] = Field(default=None, description='要上传的文件路径')


class InputToolParams(LocationToolParams):
    text: str = Field(description='要输入的文本')
    send_enter: bool = Field(default=True, description='是否发送回车键')


class SwipeToolParams(ToolParams):
    to: Literal['left', 'right', 'top', 'bottom'] = Field(description='滑动方向')
    expect_keywords: Optional[list[str]] = Field(description='期望出现的关键字列表')


class SwipeFromCoordinateToolParams(ToolParams):
    coordinates: conlist(item_type=tuple[int, int], min_length=2) = Field(description='滑动起始坐标列表')


class WaitToolParams(ToolParams):
    """
    示例：
    等待2秒 -> timeout=2，expect_keywords=None
    等待5秒，直到出现"确定"按钮 -> timeout=5，expect_keywords=['确定']
    """
    timeout: int = Field(description='等待时间，单位为秒')
    expect_keywords: Optional[list[str]] = Field(description='期望出现的关键字列表')


class AssertContainsParams(ToolParams):
    expect_keywords: list[str] = Field(description='期望包含的关键字列表')


class AssertNotContainsParams(ToolParams):
    unexpect_keywords: list[str] = Field(description='期望不包含的关键字列表')


class MarkFailedParams(BaseModel):
    reason: str = Field(description='失败原因')


class ToolResult(BaseModel, Generic[T]):
    is_success: bool
    output: Optional[T] = None

    @classmethod
    def success(cls, output: T = None, description: str = None):
        return cls(is_success=True, output=output)

    @classmethod
    def failed(cls, output: T = None, description: str = None):
        return cls(is_success=False, output=output)


class PlanningStep(BaseModel):
    instruction: str = Field(description='步骤指令，用一句话描述该步骤要做什么')


class PlanningOutputType(BaseModel):
    """
    用户指令分解后，规划出的指令序列
    """
    steps: list[PlanningStep] = Field(description='步骤序列')


class StepOutputType(BaseModel):
    """
    用户指令完成后判断是否成功
    """
    is_success: bool = Field(description='所有操作是否成功')
