#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Author : aidenmo
# @Email : aidenmo@tencent.com
# @Time : 2025/7/7 18:10

import asyncio
import io
from asyncio import Queue
from io import BytesIO
from typing import Annotated, AsyncGenerator

from PIL import Image
from fastapi import Depends, UploadFile, File, HTTPException, Form
from fastapi.exceptions import RequestValidationError
from loguru import logger
from pydantic import BaseModel, HttpUrl, Field, ValidationError

from config import settings
from schemas.omni import ImgCacheParams, OCRParams, IconDetectParams, IconCaptionParams, OverlayDetectParams
from util import format_bytes
from util.context import Context, context_var
from util.cos import download_file

idle_queue = Queue()


class RequestParams(BaseModel):
    key: str = Field('', description="访问密钥")
    img_cache: ImgCacheParams = Field(default_factory=ImgCacheParams, description="图片缓存参数")
    ocr: OCRParams = Field(default_factory=OCRParams, description="OCR 参数")
    icon_detect: IconDetectParams = Field(default_factory=IconDetectParams, description="图标检测参数")
    icon_caption: IconCaptionParams = Field(default_factory=IconCaptionParams, description="图标识别参数")
    overlay_detect: OverlayDetectParams = Field(default_factory=OverlayDetectParams, description="弹窗/加载中检测参数")
    overlap_iou_threshold: float = Field(default=settings.overlap_iou_threshold, description="图标重叠IoU阈值")
    visualize: bool = Field(default=False, description="是否可视化识别结果")


async def get_params(
        params: RequestParams | str | None = Form(default_factory=RequestParams, description='其他参数')
) -> RequestParams:
    logger.info(f'start parse...')
    if isinstance(params, str):
        try:
            return RequestParams.model_validate_json(params)
        except ValidationError as e:
            raise RequestValidationError(errors=e.errors())

    return params


async def get_image_source(
        file: UploadFile = File(default=None, description="图片文件"),
        image_url: HttpUrl = Form(None, description="图片的URL地址"),
) -> AsyncGenerator[tuple[Image.Image, asyncio.Task, BytesIO], None]:
    if not any([file, image_url]):
        raise HTTPException(status_code=400, detail="file or image_url is required")

    image_buffer = BytesIO()
    try:
        if file:
            image_buffer = BytesIO(await file.read())
            image_buffer.name = file.filename
        else:
            image_buffer = io.BytesIO(await download_file(image_url.__str__()))
            image_buffer.name = image_url.path.rsplit('/', 1)[-1]
        # 保持所有图片 3 channels
        image = Image.open(image_buffer).convert('RGB')
        logger.info(f'image: {image_buffer.name} size: {image.size} {format_bytes(len(image_buffer.getvalue()))}')
        # 异步上传原始图片
        image_upload_task = asyncio.create_task(
            settings.storage_client.async_upload_file(
                BytesIO(image_buffer.getvalue()), prefix=settings.storage_prefix)
        )
        yield image, image_upload_task, image_buffer
    finally:
        image_buffer.close()


async def get_context(
        image_source: Annotated[tuple[Image.Image, asyncio.Task, BytesIO], Depends(get_image_source)]
) -> AsyncGenerator[Context, None]:
    """请求上下文"""
    image, image_upload_task, image_buffer = image_source
    context = Context(image=image, image_upload_task=image_upload_task, image_buffer=image_buffer)
    context_var.set(context)
    yield context


async def get_queue() -> AsyncGenerator[Queue, None]:
    """限流"""
    try:
        if idle_queue.qsize() == 0:
            logger.warning(f'idle queue is empty, wait for idle queue...')
        await idle_queue.get()
        logger.info(f'require idle queue success， idle queue size: {idle_queue.qsize()}')
        yield idle_queue
    finally:
        idle_queue.put_nowait(True)
