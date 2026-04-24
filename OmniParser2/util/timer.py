#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Author : aidenmo
# @Email : aidenmo@tencent.com
# @Time : 2026/1/4 14:11

import time
from contextlib import contextmanager

from loguru import logger
from pydantic import BaseModel, Field


class TimerInfo(BaseModel):
    message: str
    elapsed: float


class TimerRecorder(BaseModel):
    timer_stack: list[tuple[float, str]] | None = Field(default_factory=list)
    records: list[TimerInfo] | None = Field(default_factory=list)

    @contextmanager
    def timer(self, message: str):
        st = time.perf_counter()
        yield
        elapsed = time.perf_counter() - st
        logger.info(f'{message}耗时: {elapsed}s')
        self.records.append(TimerInfo(message=message, elapsed=elapsed))

    def timer_start(self, message: str):
        self.timer_stack.append((time.perf_counter(), message))

    def timer_stop(self):
        if len(self.timer_stack) % 2 == 0:
            raise Exception('计时器需要先调用 timer_start')
        st, message = self.timer_stack.pop()
        elapsed = time.perf_counter() - st
        logger.info(f'{message}耗时: {elapsed}s')
        self.records.append(TimerInfo(message=message, elapsed=elapsed))
