#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Author : aidenmo
# @Email : aidenmo@tencent.com
# @Time : 2025/8/3 11:06
from pathlib import Path

from esprima import parseScript
from playwright.async_api import Page, ElementHandle


def parse_script():
    parse_result = {}
    script = (Path(__file__).parent / 'script.js').read_text()
    parsed = parseScript(script, {"range": True})
    for item in parsed.body[0].declarations[0].init.properties:
        parse_result[item.key.name] = script[item.value.range[0]: item.value.range[1]]

    return parse_result


class JSTool:
    _script: dict = parse_script()

    @classmethod
    async def add_highlight_element(cls, page: Page, element_bbox: list) -> ElementHandle:
        return (await page.evaluate_handle(cls._script['add_highlight_element'], [element_bbox])).as_element()

    @classmethod
    async def remove_highlight_element(cls, page: Page):
        return await page.evaluate(cls._script['remove_highlight_element'])

    @classmethod
    async def has_scrollbar(cls, page: Page, to: str) -> bool:
        if to in ['top', 'bottom']:
            return await page.evaluate(cls._script['has_vertical_scrollbar'])
        else:
            return await page.evaluate(cls._script['has_horizontal_scrollbar'])

    @staticmethod
    async def remove_element(el_handle: ElementHandle):
        await el_handle.evaluate("el => el.remove()")

