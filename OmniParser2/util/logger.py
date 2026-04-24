#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Author : aidenmo
# @Email : aidenmo@tencent.com
# @Time : 2025/12/22 15:42
import logging
import sys

from log_reporter import install_loguru
from loguru import logger

from config import settings


def init_logger(level=logging.INFO):
    logger.remove()
    logger.add(sys.stdout,
               level=level,
               enqueue=True,
               format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
                      "<level>{level: <8}</level> | "
                      "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
                      "<green>{extra[trace_id]}</green> - <level>{message}</level>")
    logger.configure(extra={"trace_id": ''})
    # 默认不上报日志
    install_loguru(level="INFO")
