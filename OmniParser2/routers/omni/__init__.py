#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Author : aidenmo
# @Email : aidenmo@tencent.com
# @Time : 2025/6/15 17:22
import asyncio
from asyncio import Queue
from contextlib import asynccontextmanager
from io import BytesIO
from typing import Annotated

from PIL import Image, ImageDraw
from fastapi import APIRouter, Depends, FastAPI, BackgroundTasks
from loguru import logger
from paddleocr import PaddleOCR

from config import settings
from core.handler import BoxesHandler
from core.parse import OmniParser, ParsedResult
from schemas.omni import ParsedResponse
from model.icon_captioner import IconCaptioner
from model.icon_detector import IconDetector
from model.overlay_detector import OverlayDetector
from util.context import Context
from util.image_vector_storage import AsyncImageVectorStorage
from util.response import Response
from .deps import RequestParams, idle_queue, get_context, get_queue, get_params

# 全局变量定义
ocr: PaddleOCR | None = None
icon_detector: IconDetector | None = None
icon_captioner: IconCaptioner | None = None
overlay_detector: OverlayDetector | None = None
storage: AsyncImageVectorStorage | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global ocr, icon_detector, icon_captioner, overlay_detector, storage
    # 在应用启动时初始化模型，避免多进程重复初始化
    logger.info('Initializing models...')
    ocr = PaddleOCR(**settings.ocr_config.model_dump())
    icon_detector = IconDetector()
    icon_captioner = IconCaptioner()
    overlay_detector = OverlayDetector()
    logger.info('Models initialized.')
    # 启动时加载向量数据库客户端
    if settings.milvus_config.enable:
        storage = await AsyncImageVectorStorage.create_instance(
            host=settings.milvus_config.host,
            port=settings.milvus_config.port,
        )

    for _ in range(settings.max_concurrency):
        idle_queue.put_nowait(True)
    try:
        yield
    finally:
        await storage.close()


router = APIRouter(lifespan=lifespan)


async def visualize(image: Image.Image, annotated_merge_image: Image.Image, parsed_result: ParsedResult):
    annotated_icon_image = await asyncio.to_thread(
        BoxesHandler.annotate, image=image, elements=parsed_result.icon_elements, visualize=True)
    annotated_ocr_image = await asyncio.to_thread(
        BoxesHandler.annotate, image=image, elements=parsed_result.ocr_elements, visualize=True
    )
    all_images = [annotated_icon_image, annotated_ocr_image, annotated_merge_image]
    total_width = sum([image.width for image in all_images])
    max_height = max([image.height for image in all_images])
    new_image = Image.new('RGB', (total_width, max_height))
    x_offset = 0
    draw = ImageDraw.Draw(new_image)
    for img in all_images:
        new_image.paste(img, (x_offset, 0))
        if x_offset < new_image.width:
            # 画分割线
            draw.line(
                xy=[(x_offset, 0), (x_offset, new_image.height)],
                fill='gray',
                width=1
            )
        x_offset += img.width
    return new_image


async def get_cache_data(params: RequestParams, context: Context):
    if settings.milvus_config.enable and params.img_cache.store:
        with context.timer_recorder.timer('图片缓存查询'):
            cached_data = await storage.query(context.image_buffer, days_filter=params.img_cache.within_days)
        # 如果图片已存在，直接返回缓存的结果
        if cached_data:
            logger.info(f'图片已存在，直接返回缓存的结果...')
            logger.info(f'image_url: {cached_data["image_url"]}')
            logger.info(f'labeled_image_url: {cached_data["labeled_url"]}')
            return cached_data
    return None


async def store_data(
        image: BytesIO,
        params: RequestParams,
        parsed_result: ParsedResult,
        labeled_image_url: str,
        image_url: str
):
    if settings.milvus_config.enable and params.img_cache.store:
        await storage.store(
            image,
            [element.model_dump() for element in parsed_result.elements],
            labeled_image_url,
            key=params.key,
            check_exist=False,
            image_url=image_url)


@router.post("/parse/")
async def parse(
        params: Annotated[RequestParams, Depends(get_params)],
        context: Annotated[Context, Depends(get_context)],
        _: Annotated[Queue, Depends(get_queue)],
        background_tasks: BackgroundTasks
):
    logger.info(f'params: {params.model_dump_json(exclude_defaults=True)}')
    cached_data = await get_cache_data(params, context)
    if cached_data:
        image_url = await context.image_upload_task
        return ParsedResponse(
            parsed_content_list=cached_data["elements"],
            labeled_image_url=cached_data["labeled_url"],
            image_url=image_url,
            timer=context.timer_recorder
        )

    omni = OmniParser(
        image=context.image,
        ocr=ocr,
        ocr_params=params.ocr,
        icon_detector=icon_detector,
        icon_detect_params=params.icon_detect,
        icon_captioner=icon_captioner,
        icon_caption_params=params.icon_caption,
        overlay_detector=overlay_detector,
        overlay_detect_params=params.overlay_detect,
        overlap_iou_threshold=settings.overlap_iou_threshold,
        device=settings.device,
    )
    parsed_result: ParsedResult = await asyncio.to_thread(omni.parse)
    annotated_image = await asyncio.to_thread(BoxesHandler.annotate, image=context.image,
                                              elements=parsed_result.elements, visualize=params.visualize)
    labeled_image_url = await settings.storage_client.async_upload_file(annotated_image, prefix=settings.storage_prefix)
    visualize_image_url = None
    if params.visualize:
        with context.timer_recorder.timer('输出可视化图片'):
            visualize_image = await visualize(context.image, annotated_image, parsed_result)
        visualize_image_url = await settings.storage_client.async_upload_file(visualize_image,
                                                                              prefix=settings.storage_prefix)
    image_url = await context.image_upload_task
    # 后台存储数据，不阻塞接口响应
    background_tasks.add_task(
        store_data,
        BytesIO(context.image_buffer.getvalue()),  # copy image buffer, avoid being closed
        params,
        parsed_result,
        labeled_image_url,
        image_url
    )
    # return Response(data=ParsedResponse(
    #     parsed_content_list=parsed_result.elements,
    #     labeled_image_url=labeled_image_url,
    #     image_url=image_url,
    #     visualize=visualize_image_url,
    #     timer=context.timer_recorder
    # ))
    # TODO: 先兼容老版本格式，后面统一用上面新的数据格式
    return ParsedResponse(
        parsed_content_list=parsed_result.elements,
        labeled_image_url=labeled_image_url,
        image_url=image_url,
        visualize=visualize_image_url,
        timer=context.timer_recorder
    )
