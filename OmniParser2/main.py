#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Author : aidenmo
# @Email : aidenmo@tencent.com
# @Time : 2025/6/15 17:24
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from log_reporter import flush
from loguru import logger
from starlette.middleware.cors import CORSMiddleware

from config import settings
from routers import omni, health
from util.logger import init_logger
from util.middleware import TimerAndTraceIDMiddleware, validation_exception_handler


@asynccontextmanager
async def lifespan(app_: FastAPI):
    init_logger(settings.log_level)

    logger.info(f'app startup: {app_}')
    logger.info(f'settings: {settings}')
    try:
        yield
    finally:
        flush()
        logger.info('app shutdown')


app = FastAPI(
    openapi_url=settings.openapi_url,
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(TimerAndTraceIDMiddleware)
app.exception_handler(RequestValidationError)(validation_exception_handler)

app.include_router(omni.router, prefix="/omni", tags=["page-shot"])
app.include_router(health.router, prefix="/health", tags=["health"])

if __name__ == '__main__':
    import uvicorn

    uvicorn.run('main:app', host='0.0.0.0', port=8000, reload=settings.auto_reload)
