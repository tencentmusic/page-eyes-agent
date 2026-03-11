#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Author : aidenmo
# @Email : aidenmo@tencent.com
# @Time : 2025/5/23 18:30
from collections import OrderedDict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, TypeVar, Literal, Generic, TypeAlias, Union, Any

from pydantic import BaseModel, Field, conlist, ConfigDict, computed_field
from pydantic_ai import RunContext

from .config import Settings, default_settings
from .device import WebDevice, AndroidDevice, HarmonyDevice, IOSDevice

T = TypeVar('T')
ClientT = TypeVar('ClientT')
DeviceT = TypeVar('DeviceT')
ToolT = TypeVar('ToolT')

SimulateDeviceType: TypeAlias = Literal['iPhone 15', 'iPhone 15 Pro', 'iPhone 15 Pro Max', 'iPhone 6'] | str


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
    app_name_map: dict[str, str] = field(default_factory=dict)
    """友好的应用名称到 Bundle ID 的映射"""


class ToolParams(BaseModel):
    # instruction: str = Field(description='用户指令，描述该步骤要做什么', exclude=True)
    instruction: str = Field(description='用户指令，描述该步骤要做什么')
    action: str = Field(description='要执行的动作名称，如 click、input、swipe、open_app 等, 操作调用的工具名称')


class OpenUrlToolParams(ToolParams):
    url: str = Field(description='要打开的url网址')


PositionType: TypeAlias = Literal['left', 'right', 'top', 'bottom']

AgentDepsType: TypeAlias = AgentDeps[
    Union[WebDevice, AndroidDevice, HarmonyDevice, IOSDevice],
    Any,
]


class LLMLocationToolParams(ToolParams):
    element_id: int = Field(description='要操作的元素ID')
    element_content: str = Field(description='要操作的元素内容')

    def get_coordinate(self,
                       ctx: RunContext[AgentDepsType],
                       position: Optional[PositionType] = None,
                       offset: Optional[float] = None) -> tuple[int, int]:
        """计算坐标, 返回 (x, y)"""
        device_size = ctx.deps.device.device_size
        bbox = ctx.deps.context.current_step.screen_elements[self.element_id].get('bbox')

        x1, y1, x2, y2 = bbox
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


class VLMLocationToolParams(ToolParams):
    coordinate: tuple[int, int, int, int] = Field(description='要操作的元素坐标，格式为(x1, y1, x2, y2)')
    element_content: str = Field(description='要操作的元素内容')

    @computed_field
    def bbox(self) -> tuple[float, float, float, float]:
        x1, y1, x2, y2 = self.coordinate
        return x1 / 1000, y1 / 1000, x2 / 1000, y2 / 1000

    def get_coordinate(self,
                       ctx: RunContext[AgentDepsType],
                       position: Optional[PositionType] = None,
                       offset: Optional[float] = None) -> tuple[int, int]:
        device_size = ctx.deps.device.device_size
        x1, y1, x2, y2 = self.coordinate
        width, height = device_size.width, device_size.height

        x, y = ((x1 + x2) / 2) / 1000 * width, ((y1 + y2) / 2) / 1000 * height
        offset = 0.25 if offset is None else offset
        if position == 'left':
            x = x1 + (x2 - x1) * offset
        elif position == 'right':
            x = x2 - (x2 - x1) * offset
        elif position == 'top':
            y = y1 + (y2 - y1) * offset
        elif position == 'bottom':
            y = y2 - (y2 - y1) * offset

        return int(x), int(y)


LocationToolParams = VLMLocationToolParams if default_settings.model_type == 'vlm' else LLMLocationToolParams


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
    """
    示例：
    - 输入"123456" -> text="123456"，send_enter=True
    - 输入"123456"，不发送回车键 -> text="123456"，send_enter=False
    """
    text: str = Field(description='要输入的文本')
    send_enter: bool = Field(default=True, description='是否发送回车键')


class SwipeToolParams(ToolParams):
    """
    示例：
    向上滑动 2 次 -> to='top', repeat_times=2
    """
    to: Literal['left', 'right', 'top', 'bottom'] = Field(description='滑动方向')
    repeat_times: Optional[int] = Field(default=1, description='重复次数或最多重复次数，默认为1次')


class SwipeForKeywordsToolParams(SwipeToolParams):
    """
    示例：
    向上滑动 2 次 -> to='top', repeat_times=2
    向上滑动最多 5 次，直到页面中出现 "确定" 元素 -> to='top', repeat_times=5, expect_keywords=['确定']
    向上滑动，直到出现"胡广生"元素 -> to='top', repeat_times=None, expect_keywords=['胡广生']
    """
    expect_keywords: Optional[list[str]] = Field(default=None, description='期望出现的关键字列表')


class SwipeFromCoordinateToolParams(ToolParams):
    coordinates: conlist(item_type=tuple[int, int], min_length=2) = Field(description='滑动起始坐标列表')


class WaitToolParams(ToolParams):
    """
    示例：
    等待2秒 -> timeout=2
    """
    timeout: int = Field(description='等待时间，单位为秒')


class WaitForKeywordsToolParams(ToolParams):
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
    reason: str = Field(description='失败原因描述')


class ToolResult(BaseModel, Generic[T]):
    is_success: bool

    @classmethod
    def success(cls):
        return cls(is_success=True)

    @classmethod
    def failed(cls):
        return cls(is_success=False)


class ToolResultWithOutput(ToolResult, Generic[T]):
    output: Optional[T] = Field(default=None)

    @classmethod
    def success(cls, output: T = None):
        return cls(is_success=True, output=output)

    @classmethod
    def failed(cls, output: T = None):
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
