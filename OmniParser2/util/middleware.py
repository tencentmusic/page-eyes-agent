#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Author : aidenmo
# @Email : aidenmo@tencent.com
# @Time : 2025/6/17 17:30
import time
import traceback
import uuid

from fastapi import HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from util.context import trace_id_var
from loguru import logger
from util.response import ErrorResponse


class TimerAndTraceIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint):
        start_time = time.perf_counter_ns()
        trace_id_key = 'X-Trace-ID'
        if request.headers.get(trace_id_key):
            trace_id = request.headers.get(trace_id_key)
        else:
            # 生成 trace_id
            trace_id = str(uuid.uuid4())
        trace_id_var.set(trace_id)
        with logger.contextualize(trace_id=trace_id):
            # 处理请求
            try:
                response = await call_next(request)
            except Exception as exc:
                if isinstance(exc, HTTPException):
                    response = JSONResponse(content=ErrorResponse(code=exc.status_code, msg=exc.detail).model_dump())
                else:
                    format_exc = traceback.format_exc()
                    for line in format_exc.splitlines():
                        logger.error(line)
                    response = JSONResponse(content=ErrorResponse(code=500, msg=f"处理异常:{exc} {format_exc}").model_dump())

            # 在响应头中添加 trace_id
            response.headers[trace_id_key] = trace_id
            response.headers["X-Process-Time"] = str((time.perf_counter_ns() - start_time) / 1_000_000_000)  # s
            logger.info(f'Request elapsed time: {response.headers["X-Process-Time"]}s')

        return response


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(ErrorResponse(code=422, msg="请求参数验证失败", data=exc.errors()).model_dump())
