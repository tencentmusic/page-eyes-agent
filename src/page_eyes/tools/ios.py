#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Author : aidenmo
# @Email : aidenmo@tencent.com
# @Time : 2025/2/11 16:35
import asyncio
import io
from typing import IO, Optional
from pathlib import Path

from httpx import AsyncClient
from loguru import logger
# noinspection PyProtectedMember
from loguru._logger import context as logger_context
from pydantic import TypeAdapter
from pydantic_ai import RunContext, Agent

from ..deps import (
    AgentDeps, ToolParams, ToolResult, ToolResultWithOutput,
    ClickToolParams, InputToolParams, SwipeToolParams, WaitToolParams,
    AssertContainsParams, AssertNotContainsParams, ScreenInfo, OpenUrlToolParams
)
from ..device import IOSDevice
from ..config import global_settings
from .base import AgentTool, tool

storage_client = global_settings.storage_client


class IOSAgentTool(AgentTool):
    """iOS设备自动化工具类"""

    @staticmethod
    async def screenshot(ctx: RunContext[AgentDeps[IOSDevice, 'IOSAgentTool']]) -> io.BytesIO:
        """截图并返回字节流"""
        image_buffer = io.BytesIO()
        screenshot = ctx.deps.device.wda_client.screenshot()

        # 兼容不同版本的返回值
        if hasattr(screenshot, 'save'):
            # PIL Image 对象
            screenshot.save(image_buffer, format='PNG')
        else:
            # 字节流
            image_buffer.write(screenshot)

        image_buffer.name = 'screen.png'
        image_buffer.seek(0)
        return image_buffer

    @tool
    async def get_screen_info(self, ctx: RunContext[AgentDeps[IOSDevice, 'IOSAgentTool']]) -> ToolResultWithOutput[
        dict]:
        """
        获取当前屏幕信息，screen_elements 包含所有解析到的元素信息，bbox 是相对值，格式为 (x1, y1, x2, y2)
        该工具禁止作为一个单独步骤
        """
        screen_info = await self.get_screen(ctx)
        return ToolResultWithOutput.success(screen_info.model_dump(include={'screen_elements'}))

    async def tear_down(self, ctx: RunContext[AgentDeps[IOSDevice, 'IOSAgentTool']], params: ToolParams) -> ToolResult:
        """清理操作，在失败时调用"""
        logger.warning(f'ios tear down: {params}')
        return ToolResult.success()

    @tool(after_delay=1)
    async def click(self, ctx: RunContext[AgentDeps[IOSDevice, 'IOSAgentTool']], params: ClickToolParams) -> ToolResult:
        """
        点击指定元素

        示例:
        - 点击"确定"按钮 -> position=None, offset=None
        - 点击"确定"按钮左侧 -> position='left', offset=None
        """
        logger.info(f'click element: {params.element_content}')

        device = ctx.deps.device
        session = device.wda_client.session()

        # 计算点击坐标
        x, y = params.get_coordinate(device.device_size, params.position, params.offset)

        # 执行点击
        session.tap(x, y)

        return ToolResult.success()

    @tool(after_delay=1)
    async def input(self, ctx: RunContext[AgentDeps[IOSDevice, 'IOSAgentTool']], params: InputToolParams) -> ToolResult:
        """
        在指定元素中输入文本

        示例:
        - 输入"123456" -> text="123456", send_enter=True
        - 输入"123456"，不发送回车键 -> text="123456", send_enter=False
        """
        logger.info(f'input text: {params.text} to element: {params.element_content}')

        device = ctx.deps.device
        session = device.wda_client.session()

        # 先点击输入框获取焦点
        x, y = params.get_coordinate(device.device_size)
        session.tap(x, y)
        await asyncio.sleep(0.5)

        # 输入文本
        session.send_keys(params.text)

        # 发送回车键
        if params.send_enter:
            session.send_keys('\n')

        return ToolResult.success()

    @tool(after_delay=1)
    async def swipe(self, ctx: RunContext[AgentDeps[IOSDevice, 'IOSAgentTool']], params: SwipeToolParams) -> ToolResult:
        """
        滑动屏幕

        示例:
        - 向上滑动 2 次 -> to='top', repeat_times=2
        - 向上滑动最多 5 次，直到页面中出现 "确定" 元素 -> to='top', repeat_times=5, expect_keywords=['确定']
        """
        logger.info(f'swipe {params.to}, repeat_times: {params.repeat_times}')

        device = ctx.deps.device
        session = device.wda_client.session()
        width, height = device.device_size.width, device.device_size.height

        # 定义滑动起点和终点
        center_x = width // 2
        swipe_configs = {
            'top': (center_x, int(height * 0.7), center_x, int(height * 0.3)),
            'bottom': (center_x, int(height * 0.3), center_x, int(height * 0.7)),
            'left': (int(width * 0.7), height // 2, int(width * 0.3), height // 2),
            'right': (int(width * 0.3), height // 2, int(width * 0.7), height // 2)
        }

        x1, y1, x2, y2 = swipe_configs[params.to]

        repeat_times = params.repeat_times or 999
        for times in range(1, repeat_times + 1):
            session.swipe(x1, y1, x2, y2)
            logger.info(f'swipe {params.to} times: {times}')

            if params.expect_keywords:
                await asyncio.sleep(1)
                result = await self.expect_screen_contains(ctx, params.expect_keywords)
                if result.is_success:
                    return result
                if times == params.repeat_times:
                    return ToolResult.failed()

        return ToolResult.success()

    @tool(after_delay=1)
    async def wait(self, ctx: RunContext[AgentDeps[IOSDevice, 'IOSAgentTool']], params: WaitToolParams) -> ToolResult:
        """
        等待指定时间或直到出现期望的元素

        示例:
        - 等待2秒 -> timeout=2, expect_keywords=None
        - 等待5秒，直到出现"确定"按钮 -> timeout=5, expect_keywords=['确定']
        """
        logger.info(f'wait {params.timeout}s, expect_keywords: {params.expect_keywords}')

        if params.expect_keywords:
            for _ in range(params.timeout):
                await asyncio.sleep(1)
                result = await self.expect_screen_contains(ctx, params.expect_keywords)
                if result.is_success:
                    return result
            return ToolResult.failed()
        else:
            await asyncio.sleep(params.timeout)
            return ToolResult.success()

    @tool
    async def assert_contains(
            self,
            ctx: RunContext[AgentDeps[IOSDevice, 'IOSAgentTool']],
            params: AssertContainsParams
    ) -> ToolResult:
        """
        断言当前屏幕包含指定关键字
        """
        logger.info(f'assert contains: {params.expect_keywords}')
        return await self.expect_screen_contains(ctx, params.expect_keywords)

    @tool
    async def assert_not_contains(
            self,
            ctx: RunContext[AgentDeps[IOSDevice, 'IOSAgentTool']],
            params: AssertNotContainsParams
    ) -> ToolResult:
        """
        断言当前屏幕不包含指定关键字
        """
        logger.info(f'assert not contains: {params.unexpect_keywords}')
        result = await self.expect_screen_contains(ctx, params.unexpect_keywords)

        return ToolResult.success() if not result.is_success else ToolResult.failed()

    @tool(after_delay=1)
    #todo 好像有问题
    async def goback(self, ctx: RunContext[AgentDeps[IOSDevice, 'IOSAgentTool']], params: ToolParams) -> ToolResult:
        """
        返回到上一个页面
        这里优先尝试查找并点击导航栏的返回按钮，如果没有则使用边缘滑动手势
        """
        logger.info('go to previous page')

        device = ctx.deps.device
        session = device.wda_client.session()
        try:
            # 方法1：尝试查找并点击导航栏的返回按钮
            back_button = None

            # 尝试通过不同的方式查找返回按钮
            for selector in [
                {'type': 'XCUIElementTypeButton', 'name': '返回'},
                {'type': 'XCUIElementTypeButton', 'label': 'Back'},
                {'type': 'XCUIElementTypeButton', 'name': 'Back'},
            ]:
                try:
                    back_button = session(**selector)
                    if back_button.exists:
                        back_button.click()
                        logger.info('点击导航栏返回按钮')
                        return ToolResult.success()
                except:
                    continue
            # 方法2：如果没找到返回按钮，使用屏幕左边缘滑动手势
            logger.info('使用左边缘滑动手势返回')
            height = device.device_size.height
            width = device.device_size.width
            session.swipe(10, height // 2, width // 2, height // 2, duration=0.3)

        except Exception as e:
            logger.warning(f'返回操作失败: {e}，尝试备用方案')
            # 备用方案：使用更简单的滑动
            height = device.device_size.height
            session.swipe(10, height // 2, 200, height // 2)

        return ToolResult.success()

    @tool(after_delay=1)
    async def home(self, ctx: RunContext[AgentDeps[IOSDevice, 'IOSAgentTool']], params: ToolParams) -> ToolResult:
        """
        返回主屏幕
        """
        logger.info('go to home')

        session = ctx.deps.device.wda_client.session()
        session.home()

        return ToolResult.success()

    @tool(after_delay=2)
    async def launch_app(
            self,
            ctx: RunContext[AgentDeps[IOSDevice, 'IOSAgentTool']],
            params: ToolParams
    ) -> ToolResult:
        """
        启动指定的应用
        需要在params中传入bundle_id参数
        """
        bundle_id = params.params.get('bundle_id')
        if not bundle_id:
            logger.error('launch_app requires bundle_id parameter')
            return ToolResult.failed()

        logger.info(f'launch app: {bundle_id}')

        session = ctx.deps.device.wda_client.session()
        session.app_launch(bundle_id)

        return ToolResult.success()

    @tool
    async def open_url(self, ctx: RunContext[AgentDeps[IOSDevice, 'IOSAgentTool']],
                       params: OpenUrlToolParams) -> ToolResult:
        """
        使用iOS设备打开URL
        """
        logger.info(f'Open URL: {params.url}')

        # 格式化URL，确保有正确的协议头
        url = params.url.strip()
        if not url.startswith(('http://', 'https://')):
            # 如果没有协议头，添加https://
            if '.' in url and not url.startswith('www.'):
                url = f'https://{url}'
            else:
                url = f'https://www.{url}' if not url.startswith('www.') else f'https://{url}'

        logger.info(f'格式化后的URL: {url}')

        session = ctx.deps.device.wda_client.session()

        # 先启动Safari浏览器
        session.app_launch('com.apple.mobilesafari')
        await asyncio.sleep(1)

        # 使用URL scheme打开网址
        session.open_url(url)

        await asyncio.sleep(2)
        await self.get_screen(ctx, parse_element=False)
        return ToolResult.success()

    @tool
    async def open_app(
            self,
            ctx: RunContext[AgentDeps[IOSDevice, 'IOSAgentTool']],
            params: ToolParams,
    ):
        """
        在设备中打开或启动指定的应用(APP)
        """
        logger.info(f'打开应用指令: {params.instruction}')

        # iOS应用包名映射表
        app_mapping = {
            '设置': 'com.apple.Preferences',
            'safari': 'com.apple.mobilesafari',
            '浏览器': 'com.apple.mobilesafari',
            '日历': 'com.apple.mobilecal',
            '相机': 'com.apple.camera',
            '照片': 'com.apple.mobileslideshow',
            '信息': 'com.apple.MobileSMS',
            '电话': 'com.apple.mobilephone',
            '邮件': 'com.apple.mobilemail',
            '地图': 'com.apple.Maps',
            '时钟': 'com.apple.mobiletimer',
            '计算器': 'com.apple.calculator',
            '备忘录': 'com.apple.mobilenotes',
            '提醒事项': 'com.apple.reminders',
            '通讯录': 'com.apple.MobileAddressBook',
            '音乐': 'com.apple.Music',
            '视频': 'com.apple.videos',
            '播客': 'com.apple.podcasts',
            '图书': 'com.apple.iBooks',
            '健康': 'com.apple.Health',
            '钱包': 'com.apple.Passbook',
            '天气': 'com.apple.weather',
            '股票': 'com.apple.stocks',
            '查找': 'com.apple.mobileme.fmip1',
            '语音备忘录': 'com.apple.VoiceMemos',
            '提示': 'com.apple.tips',
            '文件': 'com.apple.DocumentsApp',
            '快捷指令': 'com.apple.shortcuts',
            '测距仪': 'com.apple.measure',
            '翻译': 'com.apple.translation',
        }
        instruction_lower = params.instruction.lower()
        app_name = None
        for name, bundle_id in app_mapping.items():
            if name.lower() in instruction_lower:
                app_name = name
                bundle_id = app_mapping[name]
                break
        if not app_name:
            return ToolResultWithOutput.failed(output=f'未找到匹配的应用: {params.instruction}')
        logger.info(f'打开应用: {app_name} (Bundle ID: {bundle_id})')
        try:
            session = ctx.deps.device.wda_client.session()
            session.home()
            await asyncio.sleep(1)
            session.app_launch(bundle_id)
            await asyncio.sleep(3)
            await self.get_screen(ctx, parse_element=False)
            return ToolResult.success()

        except Exception as e:
            # 获取设备上所有应用的Bundle ID列表
            apps = ctx.deps.device.wda_client.app_list()
            bundle_ids = [app.get('bundleId', '') for app in apps if app.get('bundleId')]

            # 使用LLM从应用列表中智能匹配
            sub_agent = Agent(
                ctx.model,
                output_type=str,
                system_prompt='你是一个移动端应用助手，负责根据用户输入的指令从提供的应用Bundle ID列表找出用户指令对应的Bundle ID，并仅返回Bundle ID，如果都不匹配则返回空字符串'
            )
            prompt = (f'用户指令：{params.instruction}\n'
                      f'应用Bundle ID列表：{bundle_ids}')
            result = await sub_agent.run(prompt, output_type=str)
            bundle_id = result.output

            if not bundle_id:
                return ToolResultWithOutput.failed(output='在该设备中未找到对应的应用')

            logger.info(f'Find App Bundle ID：{bundle_id}')

            # 启动应用
            session = ctx.deps.device.wda_client.session()
            session.app_launch(bundle_id)
            await asyncio.sleep(2)
            await self.get_screen(ctx, parse_element=False)
            return ToolResult.success()